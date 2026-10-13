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
    weather_signal: dict[str, int | str] | None = None,
    historical_climate: dict[str, Any] | None = None,
    seasonal_index: int | None = None,
) -> dict[str, Any]:
    """Estimate crowd score with optional historical climate and seasonal demand integration.

    When historical_climate and seasonal_index are None (default), behavior is
    byte-identical to the original implementation to preserve existing tests.
    """
    notes: list[str] = []

    # --- Popularity ---
    popularity = destination.get("popularity_score")
    if popularity is None:
        popularity = 50
        notes.append("Curated popularity input is unavailable; neutral 50 was used.")

    # --- Date demand (seasonality refinement when best_months is empty) ---
    date_demand, date_notes = estimate_date_demand(target_date, destination.get("best_months") or [])
    notes.extend(date_notes)
    if date_demand is None:
        if seasonal_index is not None:
            date_demand = seasonal_index
            notes.append(
                f"Curated peak-month information unavailable; "
                f"statewide seasonal index for {target_date.strftime('%B')} ({seasonal_index}) used."
            )
        else:
            date_demand = 50
            # No extra note here — estimate_date_demand already added one

    # --- Event pressure ---
    if event_pressure is None:
        event_pressure = 50
        notes.append("Event information was not reviewed for this date; neutral 50 was used.")

    # --- Weather visit tendency ---
    historical_weather_block: dict[str, Any] | None = None

    if weather_signal is not None:
        # Fresh forecast takes precedence
        weather_visit_tendency = int(weather_signal["value"])
        notes.append(str(weather_signal["note"]))
        if historical_climate is not None:
            notes.append(
                f"5-year historical climate context for {target_date.strftime('%B')}: "
                f"{historical_climate['note']}"
            )
            historical_weather_block = {
                "month": target_date.month,
                "avg_precipitation_mm": historical_climate.get("avg_precipitation_mm"),
                "avg_temp_max_c": historical_climate.get("avg_temp_max_c"),
                "avg_temp_min_c": historical_climate.get("avg_temp_min_c"),
                "wet_day_probability": historical_climate.get("wet_day_probability"),
                "landslide_risk_probability": historical_climate.get("landslide_risk_probability"),
                "friction": historical_climate.get("friction"),
                "visit_tendency": historical_climate.get("visit_tendency"),
                "source": historical_climate.get("source"),
            }
    elif historical_climate is not None:
        # No live forecast: use historical climate as the weather signal
        weather_visit_tendency = int(historical_climate["visit_tendency"])
        notes.append(
            f"No fresh weather forecast available. Using 5-year historical climate for "
            f"{target_date.strftime('%B')}: {historical_climate['note']}"
        )
        historical_weather_block = {
            "month": target_date.month,
            "avg_precipitation_mm": historical_climate.get("avg_precipitation_mm"),
            "avg_temp_max_c": historical_climate.get("avg_temp_max_c"),
            "avg_temp_min_c": historical_climate.get("avg_temp_min_c"),
            "wet_day_probability": historical_climate.get("wet_day_probability"),
            "landslide_risk_probability": historical_climate.get("landslide_risk_probability"),
            "friction": historical_climate.get("friction"),
            "source": historical_climate.get("source"),
        }
    else:
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

    result = {
        "score": score,
        "level": crowd_level(score),
        "estimated": True,
        **components,
        "notes": notes,
        "data_mode": DATA_MODE,
        "reviewed_at": destination.get("reviewed_at"),
    }
    if historical_weather_block is not None:
        result["historical_weather"] = historical_weather_block
    return result