from datetime import date

import pytest

from app.services.crowd_score import crowd_level, estimate_crowd
from app.services.date_demand import estimate_date_demand


def _destination(
    *,
    popularity: int | None = 10,
    best_months: list[int] | None = None,
) -> dict:
    return {
        "popularity_score": popularity,
        "best_months": best_months or [],
        "reviewed_at": date(2026, 9, 15),
    }


def test_exact_crowd_formula_and_estimate_provenance() -> None:
    estimate = estimate_crowd(
        _destination(popularity=20, best_months=[10]),
        date(2026, 10, 17),
        event_pressure=40,
    )

    assert estimate["score"] == round(0.35 * 20 + 0.30 * 80 + 0.20 * 40 + 0.15 * 50)
    assert estimate["data_mode"] == "curated_rule_estimate"
    assert estimate["reviewed_at"] == date(2026, 9, 15)
    assert estimate["estimated"] is True
    assert estimate["notes"] == ["Weather visit-tendency data is unavailable; neutral 50 was used."]


def test_missing_inputs_use_neutral_fifties_and_explain_each() -> None:
    estimate = estimate_crowd(_destination(popularity=None), date(2026, 10, 17), None)

    assert estimate["score"] == 50
    assert estimate["popularity"] == 50
    assert estimate["date_demand"] == 50
    assert estimate["event_pressure"] == 50
    assert estimate["weather_visit_tendency"] == 50
    assert len(estimate["notes"]) == 4


@pytest.mark.parametrize(
    ("score", "level"),
    [(0, "Quiet"), (34, "Quiet"), (35, "Moderate"), (59, "Moderate"),
     (60, "Busy"), (79, "Busy"), (80, "Very busy"), (100, "Very busy")],
)
def test_crowd_level_boundaries(score: int, level: str) -> None:
    assert crowd_level(score) == level


def test_date_demand_is_documented_and_missing_season_is_neutral() -> None:
    weekend = date(2026, 10, 17)

    assert estimate_date_demand(weekend, [10]) == (80, [])
    score, notes = estimate_date_demand(weekend, [])
    assert score is None
    assert "neutral 50" in notes[0]
