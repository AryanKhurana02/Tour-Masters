from datetime import date
from typing import Any

from app.services.date_demand import estimate_date_demand


WEIGHTS = {
    "popularity": 0.35,
    "date_demand": 0.30,
    "event_pressure": 0.20,
    "weather_visit_tendency": 0.15,
}
DATA_MODE = "curated_rule_estimate"


def crowd_level(score: int) -> str:
    if score <= 34:
        return "Quiet"
    if score <= 59:
        return "Moderate"
    if score <= 79:
        return "Busy"
    return "Very busy"


def estimate_crowd(
    destination: dict[str, Any],
    target_date: date,
    event_pressure: int | None,
) -> dict[str, Any]:
    notes: list[str] = []
    popularity = destination["popularity_score"]
    if popularity is None:
        popularity = 50
        notes.append("Curated popularity input is unavailable; neutral 50 was used.")

    date_demand, date_notes = estimate_date_demand(target_date, destination["best_months"])
    notes.extend(date_notes)
    if date_demand is None:
        date_demand = 50

    if event_pressure is None:
        event_pressure = 50
        notes.append("Event information was not reviewed for this date; neutral 50 was used.")

    weather_visit_tendency = 50
    notes.append("Weather visit-tendency data is unavailable; neutral 50 was used.")

    components = {
        "popularity": popularity,
        "date_demand": date_demand,
        "event_pressure": event_pressure,
        "weather_visit_tendency": weather_visit_tendency,
    }
    score = round(sum(WEIGHTS[key] * value for key, value in components.items()))
    score = max(0, min(100, score))
    return {
        "score": score,
        "level": crowd_level(score),
        "estimated": True,
        **components,
        "notes": notes,
        "data_mode": DATA_MODE,
        "reviewed_at": destination["reviewed_at"],
    }
