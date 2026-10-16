from datetime import date

import pytest

from app.services.crowd_score import (
    calculate_mountain_hci,
    crowd_level,
    estimate_crowd,
)
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
    assert estimate["notes"] == []


def test_missing_inputs_use_neutral_fifties() -> None:
    estimate = estimate_crowd(_destination(popularity=None), date(2026, 10, 17), None)

    assert estimate["score"] == 50
    assert estimate["popularity"] == 50
    assert estimate["date_demand"] == 50
    assert estimate["event_pressure"] == 50
    assert estimate["weather_visit_tendency"] == 50
    assert estimate["notes"] == []


@pytest.mark.parametrize(
    ("score", "level"),
    [(0, "Quiet"), (34, "Quiet"), (35, "Moderate"), (59, "Moderate"),
     (60, "Busy"), (79, "Busy"), (80, "Very busy"), (100, "Very busy")],
)
def test_crowd_level_boundaries(score: int, level: str) -> None:
    assert crowd_level(score) == level


def test_date_demand_missing_season_is_neutral() -> None:
    weekend = date(2026, 10, 17)

    assert estimate_date_demand(weekend, [10]) == (80, [])
    score, notes = estimate_date_demand(weekend, [])
    assert score is None
    assert notes == []


def test_mountain_hci_ideal_and_worst_weather() -> None:
    # Ideal hill weather: 20C, clear, dry, calm -> 4*10 + 2*10 + 3*10 + 10 = 100.
    assert calculate_mountain_hci(20.0, 10.0, 0.0, 5.0) == 100
    # Freezing, overcast, torrential, gale -> 4*2 + 2*2 + 3*0 + 0 = 12.
    assert calculate_mountain_hci(-5.0, 90.0, 30.0, 50.0) == 12


def _climate(**overrides) -> dict:
    base = {
        "hci_score": 30,
        "visit_tendency": 80,
        "avg_precipitation_mm": 320.0,
        "avg_temp_max_c": 22.0,
        "avg_temp_min_c": 14.0,
        "wet_day_probability": 0.70,
        "landslide_risk_probability": 0.20,
        "friction": 60,
        "source": "Open-Meteo 5-year archive (2021-2026)",
        "note": "Monsoon climatology.",
    }
    base.update(overrides)
    return base


def test_historical_hci_drives_weather_and_emits_safety_alert() -> None:
    estimate = estimate_crowd(
        _destination(popularity=50, best_months=[7]),
        date(2026, 7, 15),
        event_pressure=50,
        historical_climate=_climate(),
        seasonal_index=50,
    )

    # HCI score (30) is used as the weather variable, not the legacy tendency (80).
    assert estimate["weather_visit_tendency"] == 30
    assert estimate["historical_weather"]["hci_score"] == 30
    assert estimate["safety_alert"]["severity"] == "high"
    assert estimate["safety_alert"]["landslide_risk_probability"] == 0.2
    assert "landslide-risk rainfall" in estimate["safety_alert"]["message"]


def test_benign_climate_has_no_safety_alert() -> None:
    estimate = estimate_crowd(
        _destination(popularity=50, best_months=[11]),
        date(2026, 11, 12),
        event_pressure=50,
        historical_climate=_climate(
            hci_score=80,
            wet_day_probability=0.05,
            landslide_risk_probability=0.0,
        ),
        seasonal_index=60,
    )

    assert estimate["weather_visit_tendency"] == 80
    assert "safety_alert" not in estimate