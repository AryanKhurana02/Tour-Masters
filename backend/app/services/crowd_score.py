from datetime import date
from typing import Any

from app.services.date_demand import estimate_date_demand
from app.services.safety import build_safety_alert

WEIGHTS = {
    "popularity": 0.35,
    "date_demand": 0.30,
    "event_pressure": 0.20,
    "weather_visit_tendency": 0.15,
}
DATA_MODE = "curated_rule_estimate"

# Holiday Climate Index weights (adapted for hill-station tourism).
# HCI = 4T + 2A + 3Rd + W, where each sub-score is 0-10 (max 100).
HCI_WEIGHTS = {"T": 4, "A": 2, "Rd": 3, "W": 1}


def crowd_level(score: int) -> str:
    if score <= 34:
        return "Quiet"
    if score <= 59:
        return "Moderate"
    if score <= 79:
        return "Busy"
    return "Very busy"


def _thermal_comfort(temp_c: float) -> int:
    """Thermal comfort sub-score (0-10). Peak comfort is 15-25C in the hills."""
    if 15 <= temp_c <= 25:
        return 10
    if 10 <= temp_c < 15 or 25 < temp_c <= 30:
        return 7
    if 5 <= temp_c < 10:
        return 4
    return 2


def _cloud_score(cloud_cover_pct: float) -> int:
    """Sky clarity sub-score (0-10); overcast skies hide the Himalayan views."""
    if cloud_cover_pct <= 20:
        return 10
    if cloud_cover_pct <= 50:
        return 7
    if cloud_cover_pct <= 80:
        return 4
    return 2


def _rain_score(rain_mm: float) -> int:
    """Rain sub-score (0-10); heavy rain signals landslide and transit risk."""
    if rain_mm <= 0:
        return 10
    if rain_mm <= 5:
        return 6
    if rain_mm <= 15:
        return 3
    return 0


def _wind_score(wind_kmh: float) -> int:
    """Wind sub-score (0-10)."""
    if wind_kmh <= 10:
        return 10
    if wind_kmh <= 25:
        return 7
    if wind_kmh <= 40:
        return 4
    return 0


def hci_components(
    temp_c: float,
    cloud_cover_pct: float,
    rain_mm: float,
    wind_kmh: float,
) -> dict[str, int]:
    """Return the four HCI sub-scores (each 0-10) for transparency."""
    return {
        "T": _thermal_comfort(temp_c),
        "A": _cloud_score(cloud_cover_pct),
        "Rd": _rain_score(rain_mm),
        "W": _wind_score(wind_kmh),
    }


def calculate_mountain_hci(
    temp_c: float,
    cloud_cover_pct: float,
    rain_mm: float,
    wind_kmh: float,
) -> int:
    """Adapted Holiday Climate Index (HCI) for mountain topography, 0-100.

    HCI = 4T + 2A + 3Rd + W. A high score means comfortable, clear, dry and
    calm weather that draws visitors; a low score means weather friction.
    """
    parts = hci_components(temp_c, cloud_cover_pct, rain_mm, wind_kmh)
    score = sum(HCI_WEIGHTS[key] * value for key, value in parts.items())
    return max(0, min(100, score))


def _historical_weather_block(
    target_date: date, historical_climate: dict[str, Any]
) -> dict[str, Any]:
    """Project a climatology row onto the HistoricalWeatherSignal shape."""
    return {
        "month": target_date.month,
        "avg_precipitation_mm": historical_climate.get("avg_precipitation_mm"),
        "avg_temp_max_c": historical_climate.get("avg_temp_max_c"),
        "avg_temp_min_c": historical_climate.get("avg_temp_min_c"),
        "wet_day_probability": historical_climate.get("wet_day_probability"),
        "landslide_risk_probability": historical_climate.get("landslide_risk_probability"),
        "friction": historical_climate.get("friction"),
        "visit_tendency": historical_climate.get("visit_tendency"),
        "hci_score": historical_climate.get("hci_score"),
        "source": historical_climate.get("source"),
    }


def _climate_weather_value(historical_climate: dict[str, Any]) -> int:
    """Prefer the HCI score; fall back to the legacy friction-based tendency."""
    hci_score = historical_climate.get("hci_score")
    if hci_score is not None:
        return int(hci_score)
    return int(historical_climate["visit_tendency"])


def estimate_crowd(
    destination: dict[str, Any],
    target_date: date,
    event_pressure: int | None,
    weather_signal: dict[str, int | str] | None = None,
    historical_climate: dict[str, Any] | None = None,
    seasonal_index: int | None = None,
) -> dict[str, Any]:
    """Estimate crowd score, using the Holiday Climate Index as the weather variable.

    Weather priority: fresh Open-Meteo forecast -> 5-year historical HCI ->
    neutral 50. When historical_climate and seasonal_index are None (default),
    behaviour is identical to the original implementation to keep tests stable.
    """
    notes: list[str] = []

    # --- Popularity ---
    popularity = destination.get("popularity_score")
    if popularity is None:
        popularity = 50

    # --- Date demand (seasonality refinement when best_months is empty) ---
    date_demand, date_notes = estimate_date_demand(target_date, destination.get("best_months") or [])
    notes.extend(date_notes)
    if date_demand is None:
        date_demand = seasonal_index if seasonal_index is not None else 50

    # --- Event pressure ---
    if event_pressure is None:
        event_pressure = 50

    # --- Weather visit tendency (HCI when available) ---
    historical_weather_block: dict[str, Any] | None = None

    if weather_signal is not None:
        # Fresh forecast takes precedence. The repository supplies the HCI score
        # as the value when it is available, otherwise the legacy tendency.
        weather_visit_tendency = int(weather_signal["value"])
        notes.append(str(weather_signal["note"]))
        if historical_climate is not None:
            notes.append(
                f"5-year historical climate context for {target_date.strftime('%B')}: "
                f"{historical_climate['note']}"
            )
            historical_weather_block = _historical_weather_block(target_date, historical_climate)
    elif historical_climate is not None:
        # No live forecast: the 5-year historical HCI drives the weather signal.
        weather_visit_tendency = _climate_weather_value(historical_climate)
        notes.append(
            f"5-year historical HCI for {target_date.strftime('%B')}: "
            f"{historical_climate['note']}"
        )
        historical_weather_block = _historical_weather_block(target_date, historical_climate)
    else:
        weather_visit_tendency = 50

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

    alert = build_safety_alert(
        destination_name=str(destination.get("name") or "this destination"),
        target_date=target_date,
        historical_climate=historical_climate,
    )
    if alert is not None:
        result["safety_alert"] = alert

    return result
