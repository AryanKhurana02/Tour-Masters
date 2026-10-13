from datetime import date

from app.schemas.recommendation import RecommendationRequest
from app.services.recommendation import recommend

from app.db.database import connect_database


def test_ranking_uses_exact_weights_and_missing_travel_is_neutral(catalogue_path) -> None:
    request = RecommendationRequest(
        region="Uttarakhand",
        start_destination_id=1,
        start_date=date(2026, 10, 17),
        days=1,
        interests=["hiking"],
        budget_per_night_max=1200,
    )

    with connect_database(catalogue_path) as connection:
        items, warnings = recommend(connection, request)

    alternative = items[0]
    assert alternative["destination"]["id"] == 2
    assert alternative["fits"] == {
        "interest": 100,
        "quietness": 65,
        "travel": 50,
        "stay": 100,
    }
    assert alternative["rank_score"] == 82.75
    assert alternative["crowd"]["score"] == 35
    assert warnings == []


def test_crowd_preference_excludes_busy_candidates(catalogue_path) -> None:
    request = RecommendationRequest(
        region="Uttarakhand",
        start_destination_id=1,
        start_date=date(2026, 10, 17),
        days=1,
        avoid_crowds=True,
    )
    with connect_database(catalogue_path) as connection:
        items, _ = recommend(connection, request)

    assert [item["destination"]["id"] for item in items] == [2]


def test_broadened_candidate_pool_is_disclosed(catalogue_path) -> None:
    request = RecommendationRequest(
        region="Uttarakhand",
        start_destination_id=4,
        start_date=date(2026, 10, 17),
        days=1,
        allow_broadened_search=True,
    )
    with connect_database(catalogue_path) as connection:
        items, warnings = recommend(connection, request)

    assert items
    assert items[0]["destination"]["id"] != 4
    assert any("No reviewed look-alike links" in warning for warning in warnings)


def test_unknown_stay_price_is_neutral_not_zero(catalogue_path) -> None:
    request = RecommendationRequest(
        region="Uttarakhand",
        start_destination_id=1,
        start_date=date(2026, 10, 17),
        days=1,
        budget_per_night_max=1000,
    )
    with connect_database(catalogue_path) as connection:
        items, _ = recommend(connection, request)

    assert items[0]["fits"]["stay"] == 60
    assert items[0]["homestays"][0]["nightly_min"] == 1000
    assert items[0]["homestays"][0]["nightly_max"] == 1200


def test_unknown_stay_price_is_neutral_fit(catalogue_path) -> None:
    request = RecommendationRequest(
        region="Uttarakhand",
        start_destination_id=1,
        start_date=date(2026, 10, 17),
        days=1,
        budget_per_night_max=1000,
    )
    with connect_database(catalogue_path) as connection:
        connection.execute(
            "UPDATE homestays SET nightly_min = NULL, nightly_max = NULL, currency = NULL"
        )
        items, _ = recommend(connection, request)

    assert items[0]["fits"]["stay"] == 50
    assert "unknown" in " ".join(items[0]["reasons"]).casefold()


def test_demo_stay_fixture_is_not_presented_as_reviewed(catalogue_path) -> None:
    request = RecommendationRequest(
        region="Uttarakhand",
        start_destination_id=1,
        start_date=date(2026, 10, 17),
        days=1,
    )
    with connect_database(catalogue_path) as connection:
        connection.execute("UPDATE homestays SET source_label = 'DEMO FIXTURE - NOT VERIFIED'")
        items, _ = recommend(connection, request)

    assert items[0]["fits"]["stay"] == 50
    reasons = " ".join(items[0]["reasons"]).casefold()
    assert "demo homestay fixtures" in reasons
    assert "at least one reviewed homestay" not in reasons


def test_disabled_alternative_is_not_recommended(catalogue_path) -> None:
    request = RecommendationRequest(
        region="Uttarakhand",
        start_destination_id=1,
        start_date=date(2026, 10, 17),
        days=1,
    )
    with connect_database(catalogue_path) as connection:
        connection.execute("UPDATE alternative_links SET enabled = 0")
        items, _ = recommend(connection, request)

    assert items == []


def test_known_event_is_still_unknown_without_reviewed_calendar_window(catalogue_path) -> None:
    request = RecommendationRequest(
        region="Uttarakhand",
        start_destination_id=1,
        start_date=date(2026, 10, 17),
        days=1,
        avoid_crowds=False,
    )
    with connect_database(catalogue_path) as connection:
        connection.execute("DELETE FROM event_calendar_reviews")
        items, _ = recommend(connection, request)

    busy_alternative = next(item for item in items if item["destination"]["id"] == 3)
    assert busy_alternative["crowd"]["event_pressure"] == 50
    assert any("Event information" in note for note in busy_alternative["crowd"]["notes"])
