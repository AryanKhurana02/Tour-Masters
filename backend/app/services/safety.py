"""Derive travel-safety alerts from real historical weather signals.

This module is deliberately conservative: alerts are only produced from
measured 5-year climatology fields (wet-day probability and landslide-risk
rainfall probability), never from invented hazards. When the signals are
unavailable or benign, no alert is returned.
"""

from __future__ import annotations

from datetime import date
from typing import Any

MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

# Fraction of historical days that trigger each severity band.
LANDSLIDE_HIGH = 0.15
LANDSLIDE_MEDIUM = 0.05
WET_HIGH = 0.65
WET_MEDIUM = 0.40


def _elevated(value: float | None, medium: float, high: float) -> str | None:
    if value is None:
        return None
    if value >= high:
        return "high"
    if value >= medium:
        return "medium"
    return None


def build_safety_alert(
    *,
    destination_name: str,
    target_date: date,
    historical_climate: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Return a SafetyAlert payload, or None when conditions are not elevated."""
    if not historical_climate:
        return None

    landslide_raw = historical_climate.get("landslide_risk_probability")
    wet_raw = historical_climate.get("wet_day_probability")
    if landslide_raw is None and wet_raw is None:
        return None

    landslide = float(landslide_raw) if landslide_raw is not None else None
    wet = float(wet_raw) if wet_raw is not None else None

    landslide_band = _elevated(landslide, LANDSLIDE_MEDIUM, LANDSLIDE_HIGH)
    wet_band = _elevated(wet, WET_MEDIUM, WET_HIGH)
    bands = [band for band in (landslide_band, wet_band) if band is not None]
    if not bands:
        return None
    severity = "high" if "high" in bands else "medium"

    month_name = MONTH_NAMES[target_date.month - 1]
    details: list[str] = []
    if wet is not None and wet >= WET_MEDIUM:
        details.append(f"{round(wet * 100)}% of {month_name} days historically saw rain")
    if landslide is not None and landslide >= LANDSLIDE_MEDIUM:
        details.append(
            f"{round(landslide * 100)}% recorded landslide-risk rainfall (40 mm+)"
        )
    if not details:
        details.append("historical weather friction is elevated")

    message = (
        f"{severity.capitalize()} weather risk in {destination_name} for {month_name}: "
        + "; ".join(details)
        + ". Check road conditions before travelling."
    )

    return {
        "severity": severity,
        "landslide_risk_probability": round(landslide, 3) if landslide is not None else None,
        "wet_day_probability": round(wet, 3) if wet is not None else None,
        "message": message,
    }
