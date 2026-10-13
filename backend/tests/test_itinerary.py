from datetime import date

import pytest

from app.db.database import connect_database
from app.schemas.itinerary import ItineraryRequest
from app.services.itinerary import build_itinerary
from app.services.itinerary_validation import ItineraryValidationError


def test_template_itinerary_has_exact_dates_days_and_estimates(catalogue_path) -> None:
    request = ItineraryRequest(
        start_date=date(2026, 10, 17),
        days=3,
        destination_ids=[2],
    )

    with connect_database(catalogue_path) as connection:
        result = build_itinerary(
            connection, request, request_id="test-id", llm_enabled=False
        )

    assert result["generation_mode"] == "rule_fallback"
    assert [item["day_number"] for item in result["days"]] == [1, 2, 3]
    assert [item["date"] for item in result["days"]] == [
        date(2026, 10, 17), date(2026, 10, 18), date(2026, 10, 19)
    ]
    assert {item["destination_id"] for item in result["days"]} == {2}
    assert all(len(item["blocks"]) == 3 for item in result["days"])
    assert all(item["crowd"]["estimated"] for item in result["days"])
    assert any("final selected destination is repeated" in warning for warning in result["warnings"])


def test_unknown_destination_is_rejected(catalogue_path) -> None:
    request = ItineraryRequest(start_date=date(2026, 10, 17), days=1, destination_ids=[999])

    with connect_database(catalogue_path) as connection:
        with pytest.raises(ItineraryValidationError, match="unknown or disabled"):
            build_itinerary(connection, request, request_id="test-id", llm_enabled=False)


def test_mismatched_stay_and_destination_is_rejected(catalogue_path) -> None:
    request = ItineraryRequest(
        start_date=date(2026, 10, 17),
        days=1,
        destination_ids=[3],
        homestay_ids=[1],
    )

    with connect_database(catalogue_path) as connection:
        with pytest.raises(ItineraryValidationError, match="does not belong"):
            build_itinerary(connection, request, request_id="test-id", llm_enabled=False)


def test_selected_stay_budget_requires_a_complete_in_range_price(catalogue_path) -> None:
    request = ItineraryRequest(
        start_date=date(2026, 10, 17),
        days=1,
        destination_ids=[2],
        homestay_ids=[1],
        budget_per_night_max=1100,
    )

    with connect_database(catalogue_path) as connection:
        with pytest.raises(ItineraryValidationError, match="exceeds"):
            build_itinerary(connection, request, request_id="test-id", llm_enabled=False)
