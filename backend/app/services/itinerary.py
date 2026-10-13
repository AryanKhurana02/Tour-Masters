from __future__ import annotations

import logging
import sqlite3
from datetime import timedelta
from typing import Any

from app.integrations.llm_client import (
    LLMProviderError,
    TextOnlyGenerator,
    create_text_prompt,
    parse_text_only_response,
)
from app.repositories.destination_repository import get_event_pressure
from app.repositories.weather_repository import get_weather_visit_tendency
from app.schemas.itinerary import ItineraryRequest
from app.services.crowd_score import estimate_crowd
from app.services.itinerary_validation import validate_itinerary_selection
from app.services.seasonality import get_seasonal_demand_for_month
from app.services.weather_history import get_historical_weather_friction


logger = logging.getLogger("pahadpath.itinerary")
_PERIODS = ("morning", "afternoon", "evening")


def build_itinerary(
    connection: sqlite3.Connection,
    request: ItineraryRequest,
    *,
    request_id: str,
    llm_enabled: bool,
    text_generator: TextOnlyGenerator | None = None,
) -> dict[str, Any]:
    destinations, homestays, warnings = validate_itinerary_selection(connection, request)
    use_llm = request.use_llm and llm_enabled and text_generator is not None
    if request.use_llm and not llm_enabled:
        warnings.append("Text generation is disabled in backend configuration; using the template plan.")
    elif request.use_llm and text_generator is None:
        warnings.append("No text-generation provider is configured; using the template plan.")

    day_text: list[str] | None = None
    if use_llm and text_generator is not None:
        try:
            raw_response = text_generator.generate(create_text_prompt(request.days))
            day_text = parse_text_only_response(raw_response, request.days)
        except (LLMProviderError, TimeoutError, ValueError) as error:
            logger.warning(
                "Optional text generation failed request_id=%s category=%s",
                request_id,
                type(error).__name__,
            )
            warnings.append("Optional text generation failed validation or was unavailable; using the template plan.")

    days: list[dict[str, Any]] = []
    for index in range(request.days):
        destination_index = min(index, len(destinations) - 1)
        destination = destinations[destination_index]
        homestay = homestays[destination_index]
        target_date = request.start_date + timedelta(days=index)
        event_pressure = get_event_pressure(
            connection,
            region=destination["region"],
            destination_id=destination["id"],
            target_date=target_date,
        )
        weather_signal = get_weather_visit_tendency(
            connection,
            destination_id=destination["id"],
            target_date=target_date,
        )

        # Optional enrichments per day
        historical_climate = get_historical_weather_friction(
            destination["name"], target_date.month
        )
        seasonal_index = get_seasonal_demand_for_month(target_date.month)

        crowd = estimate_crowd(
            destination,
            target_date,
            event_pressure,
            weather_signal,
            historical_climate,
            seasonal_index,
        )
        template_texts = [
            f"Keep this {period} flexible and explore at your own pace."
            for period in _PERIODS
        ]
        if day_text is not None:
            template_texts[0] = day_text[index]
        blocks = [
            {"period": period, "text": text}
            for period, text in zip(_PERIODS, template_texts, strict=True)
        ]
        days.append({
            "day_number": index + 1,
            "date": target_date,
            "destination_id": destination["id"],
            "destination_name": destination["name"],
            "homestay_id": homestay["id"] if homestay else None,
            "homestay_name": homestay["name"] if homestay else None,
            "crowd": crowd,
            "blocks": blocks,
            "warnings": [],
        })

    return {
        "request_id": request_id,
        "generation_mode": "llm_text_assisted" if day_text is not None else "rule_fallback",
        "days": days,
        "warnings": warnings,
    }
