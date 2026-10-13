from __future__ import annotations

import sqlite3
from typing import Any

from app.repositories.destination_repository import (
    get_destination_for_itinerary,
    get_homestay_for_itinerary,
)
from app.schemas.itinerary import ItineraryRequest


class ItineraryValidationError(ValueError):
    pass


def validate_itinerary_selection(
    connection: sqlite3.Connection,
    request: ItineraryRequest,
) -> tuple[list[dict[str, Any]], list[dict[str, Any] | None], list[str]]:
    destinations: list[dict[str, Any]] = []
    for destination_id in request.destination_ids:
        destination = get_destination_for_itinerary(connection, destination_id)
        if destination is None:
            raise ItineraryValidationError(f"Selected destination ID {destination_id} is unknown or disabled.")
        destinations.append(destination)

    selected_homestay_ids = request.homestay_ids or [None] * len(destinations)
    homestays: list[dict[str, Any] | None] = []
    warnings: list[str] = []
    for destination, homestay_id in zip(destinations, selected_homestay_ids, strict=True):
        if homestay_id is None:
            homestays.append(None)
            continue
        homestay = get_homestay_for_itinerary(connection, homestay_id)
        if homestay is None:
            raise ItineraryValidationError(f"Selected homestay ID {homestay_id} is unknown or disabled.")
        if homestay["destination_id"] != destination["id"]:
            raise ItineraryValidationError(
                f"Homestay ID {homestay_id} does not belong to destination ID {destination['id']}."
            )
        if request.budget_per_night_max is not None:
            if homestay["nightly_min"] is None or homestay["nightly_max"] is None:
                raise ItineraryValidationError(
                    f"Homestay ID {homestay_id} has no complete reviewed price range; budget cannot be verified."
                )
            if homestay["nightly_max"] > request.budget_per_night_max:
                raise ItineraryValidationError(
                    f"Homestay ID {homestay_id} exceeds the requested per-night budget."
                )
        homestays.append(homestay)

    if len(destinations) < request.days:
        warnings.append(
            "Fewer unique destinations were selected than requested days; the final selected destination is repeated."
        )
    if request.budget_per_night_max is not None and not any(homestays):
        warnings.append("No homestay was selected; the requested budget could not be applied to a stay.")
    return destinations, homestays, warnings
