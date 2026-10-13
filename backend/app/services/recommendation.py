from __future__ import annotations

import sqlite3
from typing import Any

from app.repositories.destination_repository import (
    get_event_pressure,
    get_recommendation_candidates,
    list_homestays,
)
from app.schemas.recommendation import RecommendationRequest
from app.services.crowd_score import estimate_crowd


def _stay_fit(
    stays: list[dict[str, Any]],
    budget: int | None,
) -> tuple[float, list[str]]:
    if not stays:
        return 50, ["No reviewed homestay data is available; stay fit is neutral."]
    if all("DEMO FIXTURE" in stay["source_label"].upper() for stay in stays):
        return 50, [
            "Demo homestay fixtures are for interface testing only; price, availability, and stay fit are unverified."
        ]
    if budget is None:
        return 100, ["At least one reviewed homestay is listed; no budget filter was requested."]

    known_prices = [stay for stay in stays if stay["nightly_min"] is not None]
    if not known_prices:
        return 50, ["Homestay prices are unknown; stay fit is neutral and budget fit is unverified."]
    fits = [
        stay for stay in known_prices
        if stay["nightly_min"] <= budget
        and stay["nightly_max"] is not None
        and stay["nightly_max"] <= budget
    ]
    if fits:
        return 100, ["At least one reviewed homestay price range is within the requested budget."]
    overlaps = [
        stay for stay in known_prices
        if stay["nightly_min"] <= budget
        and stay["nightly_max"] is not None
        and stay["nightly_max"] > budget
    ]
    if overlaps:
        return 60, ["A reviewed homestay price range overlaps the budget; availability is not verified."]
    if any(stay["nightly_max"] is None for stay in known_prices):
        return 50, ["Some reviewed homestay prices have no verified maximum; budget fit is unverified."]
    return 0, ["Reviewed homestay prices exceed the requested budget."]


def _interest_fit(
    requested_interests: list[str],
    destination_tags: list[str],
    link_tags: list[str],
) -> tuple[float, str]:
    if not requested_interests:
        return 50, "No interests were provided; interest fit is neutral."
    available_tags = {tag.casefold() for tag in destination_tags + link_tags}
    matched = set(requested_interests) & available_tags
    score = round(100 * len(matched) / len(set(requested_interests)))
    if matched:
        return score, f"Matches curated interests: {', '.join(sorted(matched))}."
    return score, "No requested interests matched this destination's curated tags."


def recommend(
    connection: sqlite3.Connection,
    request: RecommendationRequest,
) -> tuple[list[dict[str, Any]], list[str]]:
    candidates = get_recommendation_candidates(
        connection,
        region=request.region,
        source_destination_id=request.start_destination_id,
    )
    warnings: list[str] = []
    if request.start_destination_id is not None and not candidates and request.allow_broadened_search:
        candidates = get_recommendation_candidates(
            connection,
            region=request.region,
            source_destination_id=None,
        )
        candidates = [item for item in candidates if item["id"] != request.start_destination_id]
        warnings.append(
            "No reviewed look-alike links were found; showing other reviewed destinations in the requested region."
        )

    ranked: list[dict[str, Any]] = []
    crowd_filtered: list[dict[str, Any]] = []
    for destination in candidates:
        event_pressure = get_event_pressure(
            connection,
            region=destination["region"],
            destination_id=destination["id"],
            target_date=request.start_date,
        )
        crowd = estimate_crowd(destination, request.start_date, event_pressure)
        stays = list_homestays(connection, destination["id"])
        interest, interest_reason = _interest_fit(
            request.interests, destination["tags"], destination["link_tags"]
        )
        quietness = 100 - crowd["score"]
        travel = destination["travel_fit"]
        if travel is None:
            travel = 50
            travel_reason = "Curated travel feasibility is unavailable; travel fit is neutral."
        else:
            travel_reason = "Travel fit is a curated feasibility score, not a travel time."
        stay, stay_reasons = _stay_fit(stays, request.budget_per_night_max)

        rank = (
            0.45 * interest
            + 0.35 * quietness
            + 0.10 * travel
            + 0.10 * stay
        )
        item = {
            "destination": {
                key: destination[key]
                for key in (
                    "id", "name", "district", "region", "description", "tags",
                    "best_months", "popularity_score", "source_label", "source_url",
                    "reviewer", "reviewed_at",
                )
            },
            "homestays": stays,
            "crowd": crowd,
            "rank_score": round(rank, 2),
            "fits": {
                "interest": interest,
                "quietness": quietness,
                "travel": travel,
                "stay": stay,
            },
            "reasons": [
                interest_reason,
                f"Estimated crowd level is {crowd['level']} ({crowd['score']}/100).",
                travel_reason,
                *stay_reasons,
            ],
        }
        if request.avoid_crowds and crowd["score"] >= 60:
            crowd_filtered.append(item)
        else:
            ranked.append(item)

    if not ranked and crowd_filtered and request.allow_broadened_search:
        ranked = crowd_filtered
        warnings.append(
            "No reviewed candidate met the quieter-than-busy preference; the crowd filter was relaxed."
        )
    elif crowd_filtered and not ranked:
        warnings.append(
            "No reviewed candidate met the quieter-than-busy preference; no busier places were returned."
        )
    return sorted(ranked, key=lambda item: (-item["rank_score"], item["destination"]["id"])), warnings
