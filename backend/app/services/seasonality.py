"""Load Uttarakhand seasonality data (monthly arrival trends, activities, weather).

CSV schema (from uttarakhand_seasonality.csv):
  Month, Domestic_Arrival_Trend, Foreign_Arrival_Trend, Seasonal_Activity_Focus, Weather_Condition

Exports:
  get_seasonal_index(month: int) -> dict | None
  get_all_months() -> list[dict]
"""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any

# Repo-root-relative path
REPO_ROOT = Path(__file__).resolve().parents[3]
CSV_PATH = REPO_ROOT / "backend" / "app" / "data" / "uttarakhand_seasonality.csv"

# Qualitative label → numeric index (0-100)
LABEL_TO_INDEX = {
    "low (highest)": 100,
    "peak (highest)": 100,
    "peak": 95,
    "high": 75,
    "moderate": 55,
    "low": 30,
}

# Domestic weight is higher because footfall data shows ~99.4% domestic visitors
DOMESTIC_WEIGHT = 0.85
FOREIGN_WEIGHT = 0.15

_SEASONAL_CACHE: list[dict[str, Any]] | None = None


def _parse_trend(label: str) -> int | None:
    """Parse 'Low (Index: 57)' → 57; 'Peak' → 95; 'Moderate' → 55; etc."""
    if not label:
        return None
    label = label.strip()
    lower = label.casefold()

    # Extract parenthetical index if present: "Low (Index: 57)" → 57
    m = re.search(r"\(index:\s*(\d+)\)", lower)
    if m:
        return int(m.group(1))

    # Fallback to qualitative mapping
    for key, val in LABEL_TO_INDEX.items():
        if key in lower:
            return val
    return 50  # neutral fallback


def _load_seasonality() -> list[dict[str, Any]]:
    global _SEASONAL_CACHE
    if _SEASONAL_CACHE is not None:
        return _SEASONAL_CACHE

    if not CSV_PATH.exists():
        _SEASONAL_CACHE = []
        return _SEASONAL_CACHE

    rows: list[dict[str, Any]] = []
    with CSV_PATH.open("r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            month_name = row["Month"].strip()
            domestic_idx = _parse_trend(row["Domestic_Arrival_Trend"])
            foreign_idx = _parse_trend(row["Foreign_Arrival_Trend"])
            combined = (
                round(DOMESTIC_WEIGHT * domestic_idx + FOREIGN_WEIGHT * foreign_idx)
                if domestic_idx is not None and foreign_idx is not None
                else domestic_idx or foreign_idx or 50
            )
            rows.append(
                {
                    "month_name": month_name,
                    "month": _month_name_to_number(month_name),
                    "domestic_index": domestic_idx,
                    "foreign_index": foreign_idx,
                    "combined_index": combined,
                    "activity_focus": row["Seasonal_Activity_Focus"].strip(),
                    "weather_condition": row["Weather_Condition"].strip(),
                }
            )

    rows.sort(key=lambda r: r["month"])
    _SEASONAL_CACHE = rows
    return _SEASONAL_CACHE


def _month_name_to_number(name: str) -> int:
    months = {
        "january": 1,
        "february": 2,
        "march": 3,
        "april": 4,
        "may": 5,
        "june": 6,
        "july": 7,
        "august": 8,
        "september": 9,
        "october": 10,
        "november": 11,
        "december": 12,
    }
    return months.get(name.casefold(), 0)


def get_seasonal_index(month: int) -> dict[str, Any] | None:
    """Return seasonality info for a month (1-12), or None if unknown."""
    if not 1 <= month <= 12:
        return None
    for row in _load_seasonality():
        if row["month"] == month:
            return row
    return None


def get_all_months() -> list[dict[str, Any]]:
    """Return all 12 months of seasonality data."""
    return _load_seasonality()


def get_seasonal_demand_for_month(month: int) -> int | None:
    """Return combined seasonal demand index (0-100) for a month, or None."""
    info = get_seasonal_index(month)
    return info["combined_index"] if info else None