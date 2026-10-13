from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import pandas as pd

logger = logging.getLogger("footfall_calibration")

# Load footfall data once at module level
_FOOTFALL_DATA: Optional[pd.DataFrame] = None
_FOOTFALL_LOADED: bool = False
_FOOTFALL_PATH = "C:/Users/ACER/OneDrive/Downloads/uttarakhand_tourist_footfall.xlsx"


def _load_footfall_data() -> pd.DataFrame:
    """Load the Uttarakhand tourist footfall dataset."""
    global _FOOTFALL_DATA, _FOOTFALL_LOADED
    if not _FOOTFALL_LOADED:
        try:
            _FOOTFALL_DATA = pd.read_excel(_FOOTFALL_PATH)
            _FOOTFALL_LOADED = True
            logger.info("Loaded footfall data: %d rows", len(_FOOTFALL_DATA))
        except FileNotFoundError:
            logger.warning(
                "Footfall data file not found at %s", _FOOTFALL_PATH
            )
            _FOOTFALL_DATA = pd.DataFrame(
                columns=[
                    "Destination",
                    "Domestic_Visitors",
                    "Foreign_Visitors",
                    "Total_Footfall",
                    "Category",
                ]
            )
    return _FOOTFALL_DATA


def get_destination_footfall(destination_name: str) -> Dict[str, int]:
    """Get footfall statistics for a specific destination.

    Returns dict with domestic, foreign, and total visitors.
    Normalizes destination names for matching.
    """
    df = _load_footfall_data()
    if df.empty:
        return {"domestic": 0, "foreign": 0, "total": 0}

    # Normalize destination name for matching
    dest_lower = destination_name.strip().lower()

    # Exact match first
    match = df[
        df["Destination / Hub"].str.strip().str.lower() == dest_lower
    ]
    if not match.empty:
        row = match.iloc[0]
        return {
            "domestic": int(row["Domestic Visitors"]),
            "foreign": int(row["Foreign Visitors"]),
            "total": int(row["Total Footfall"]),
        }

    # Partial match - check if destination name is contained in our data
    match = df[
        df["Destination / Hub"]
        .str.strip()
        .str.lower()
        .str.contains(dest_lower, regex=False)
    ]
    if not match.empty:
        row = match.iloc[0]
        return {
            "domestic": int(row["Domestic Visitors"]),
            "foreign": int(row["Foreign Visitors"]),
            "total": int(row["Total Footfall"]),
        }

    # No match - return state overall stats proportionally
    total_row = df[df["Destination / Hub"].str.strip().str.lower() == "total state footfall"]
    if not total_row.empty:
        row = total_row.iloc[0]
        total_domestic = int(row["Domestic Visitors"])
        total_foreign = int(row["Foreign Visitors"])
        total_overall = int(row["Total Footfall"])
        # Return a small fraction based on typical destination share
        proportion = 0.01  # ~1% of state total as default
        return {
            "domestic": int(total_domestic * proportion),
            "foreign": int(total_foreign * proportion),
            "total": int(total_overall * proportion),
        }

    return {"domestic": 0, "foreign": 0, "total": 0}


def get_statewide_footfall() -> Dict[str, int]:
    """Get total statewide tourist footfall statistics."""
    df = _load_footfall_data()
    if df.empty:
        return {"domestic": 0, "foreign": 0, "total": 0}

    total_row = df[df["Destination / Hub"].str.strip().str.lower() == "total state footfall"]
    if not total_row.empty:
        row = total_row.iloc[0]
        return {
            "domestic": int(row["Domestic Visitors"]),
            "foreign": int(row["Foreign Visitors"]),
            "total": int(row["Total Footfall"]),
        }

    # Fallback: sum all rows
    total_domestic = int(df["Domestic Visitors"].sum())
    total_foreign = int(df["Foreign Visitors"].sum())
    total_overall = int(df["Total Footfall"].sum())
    return {"domestic": total_domestic, "foreign": total_foreign, "total": total_overall}


def get_destination_categories() -> Dict[str, str]:
    """Get the category/focus for each destination in the dataset."""
    df = _load_footfall_data()
    if df.empty:
        return {}
    categories: Dict[str, str] = {}
    for _, row in df.iterrows():
        dest = str(row["Destination / Hub"])
        cat = str(row["Category / Focus"])
        categories[dest] = cat
    return categories


def get_top_destinations(n: int = 10) -> List[Dict[str, any]]:
    """Get the top N destinations by total footfall."""
    df = _load_footfall_data()
    if df.empty:
        return []

    # Sort by total footfall descending
    df_sorted = df.sort_values("Total Footfall", ascending=False)
    results: List[Dict[str, any]] = []
    for _, row in df_sorted.head(n).iterrows():
        results.append(
            {
                "destination": str(row["Destination / Hub"]),
                "domestic": int(row["Domestic Visitors"]),
                "foreign": int(row["Foreign Visitors"]),
                "total": int(row["Total Footfall"]),
                "category": str(row["Category / Focus"]),
            }
        )
    return results


def get_footfall_by_category(category: str) -> Dict[str, int]:
    """Get total footfall for a specific category/focus area."""
    df = _load_footfall_data()
    if df.empty:
        return {"domestic": 0, "foreign": 0, "total": 0}

    match = df[df["Category / Focus"].str.strip().str.lower() == category.lower()]
    if not match.empty:
        row = match.iloc[0]
        return {
            "domestic": int(row["Domestic Visitors"]),
            "foreign": int(row["Foreign Visitors"]),
            "total": int(row["Total Footfall"]),
        }

    return {"domestic": 0, "foreign": 0, "total": 0}