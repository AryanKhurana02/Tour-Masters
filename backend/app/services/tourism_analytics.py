from __future__ import annotations

import asyncio
import logging
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger("tourism_analytics")

# Paths to datasets
_FOOTFALL_PATH = "C:/Users/ACER/OneDrive/Downloads/uttarakhand_tourist_footfall.xlsx"
_REVIEWS_PATH = r"C:\Users\ACER\AppData\Local\Temp\Uttarakhand_HomeStay_Reviews.csv"

# Cached data
_footfall_df: Optional[pd.DataFrame] = None
_reviews_df: Optional[pd.DataFrame] = None
_loaded: bool = False


def _load_datasets() -> None:
    """Load both datasets lazily."""
    global _footfall_df, _reviews_df, _loaded
    if _loaded:
        return

    # Load footfall data
    try:
        _footfall_df = pd.read_excel(_FOOTFALL_PATH)
        logger.info("Loaded footfall dataset: %d rows", len(_footfall_df))
    except FileNotFoundError:
        logger.warning("Footfall dataset not found at %s", _FOOTFALL_PATH)
        _footfall_df = pd.DataFrame()

    # Load reviews dataset
    try:
        _reviews_df = pd.read_csv(_REVIEWS_PATH)
        logger.info("Loaded reviews dataset: %d rows", len(_reviews_df))
    except FileNotFoundError:
        logger.warning("Reviews dataset not found at %s", _REVIEWS_PATH)
        _reviews_df = pd.DataFrame()

    _loaded = True


def _ensure_loaded() -> None:
    """Ensure datasets are loaded before use."""
    global _loaded
    if not _loaded:
        _load_datasets()


def get_footfall_data() -> Optional[pd.DataFrame]:
    """Get the full footfall dataset."""
    _ensure_loaded()
    return _footfall_df


def get_reviews_data() -> Optional[pd.DataFrame]:
    """Get the full reviews dataset."""
    _ensure_loaded()
    return _reviews_df


def get_destination_footfall(destination_name: str) -> Dict[str, int]:
    """Get footfall statistics for a specific destination (from footfall dataset)."""
    _ensure_loaded()
    if _footfall_df is None or _footfall_df.empty:
        return {"domestic": 0, "foreign": 0, "total": 0}

    dest_lower = destination_name.strip().lower()
    match = _footfall_df[
        _footfall_df["Destination / Hub"].str.strip().str.lower() == dest_lower
    ]
    if not match.empty:
        row = match.iloc[0]
        return {
            "domestic": int(row["Domestic Visitors"]),
            "foreign": int(row["Foreign Visitors"]),
            "total": int(row["Total Footfall"]),
        }

    # Partial match
    match = _footfall_df[
        _footfall_df["Destination / Hub"]
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

    return {"domestic": 0, "foreign": 0, "total": 0}


def get_statewide_footfall() -> Dict[str, int]:
    """Get total statewide tourist footfall."""
    _ensure_loaded()
    if _footfall_df is None or _footfall_df.empty:
        return {"domestic": 0, "foreign": 0, "total": 0}

    total_row = _footfall_df[
        _footfall_df["Destination / Hub"].str.strip().str.lower() == "total state footfall"
    ]
    if not total_row.empty:
        row = total_row.iloc[0]
        return {
            "domestic": int(row["Domestic Visitors"]),
            "foreign": int(row["Foreign Visitors"]),
            "total": int(row["Total Footfall"]),
        }
    return {"domestic": 0, "foreign": 0, "total": 0}


def get_destination_categories() -> Dict[str, str]:
    """Get category/focus for destinations from footfall dataset."""
    _ensure_loaded()
    if _footfall_df is None or _footfall_df.empty:
        return {}
    categories: Dict[str, str] = {}
    for _, row in _footfall_df.iterrows():
        dest = str(row["Destination / Hub"])
        cat = str(row["Category / Focus"])
        categories[dest] = cat
    return categories


def get_top_destinations(n: int = 10) -> List[Dict[str, any]]:
    """Get top N destinations by total footfall."""
    _ensure_loaded()
    if _footfall_df is None or _footfall_df.empty:
        return []

    df_sorted = _footfall_df.sort_values("Total Footfall", ascending=False)
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
    """Get footfall by category/focus area."""
    _ensure_loaded()
    if _footfall_df is None or _footfall_df.empty:
        return {"domestic": 0, "foreign": 0, "total": 0}

    match = _footfall_df[_footfall_df["Category / Focus"].str.strip().str.lower() == category.lower()]
    if not match.empty:
        row = match.iloc[0]
        return {
            "domestic": int(row["Domestic Visitors"]),
            "foreign": int(row["Foreign Visitors"]),
            "total": int(row["Total Footfall"]),
        }
    return {"domestic": 0, "foreign": 0, "total": 0}


# ---- Reviews Analytics ----

def get_average_rating() -> Optional[float]:
    """Get average rating from homestay reviews."""
    _ensure_loaded()
    if _reviews_df is None or _reviews_df.empty:
        return None
    try:
        return float(_reviews_df["rating"].mean())
    except (ValueError, TypeError):
        return None


def get_sentiment_distribution() -> Dict[str, int]:
    """Get count of reviews by sentiment."""
    _ensure_loaded()
    if _reviews_df is None or _reviews_df.empty:
        return {"Positive": 0, "Neutral": 0, "Negative": 0}
    if "sentiment" not in _reviews_df.columns:
        return {"Positive": 0, "Neutral": 0, "Negative": 0}
    counts = _reviews_df["sentiment"].value_counts()
    result: Dict[str, int] = {"Positive": 0, "Neutral": 0, "Negative": 0}
    for key in counts.index:
        if key in result:
            result[key] = int(counts[key])
    return result


def get_top_review_topics(n: int = 10) -> List[Dict[str, any]]:
    """Get most common review topics."""
    _ensure_loaded()
    if _reviews_df is None or _reviews_df.empty:
        return []
    if "review_topic" not in _reviews_df.columns:
        return []
    topic_counts = _reviews_df["review_topic"].value_counts().head(n)
    results: List[Dict[str, any]] = []
    for topic, count in topic_counts.items():
        results.append({"topic": topic, "count": int(count), "percentage": round(count * 100 / len(_reviews_df), 1)})
    return results


def get_rating_by_guest_type() -> Dict[str, Dict[str, any]]:
    """Get average rating broken down by guest type."""
    _ensure_loaded()
    if _reviews_df is None or _reviews_df.empty or "guest_type" not in _reviews_df.columns:
        return {}
    result: Dict[str, Dict[str, any]] = {}
    for guest, group in _reviews_df.groupby("guest_type"):
        avg_rating = float(group["rating"].mean())
        review_count = len(group)
        result[guest] = {"average_rating": round(avg_rating, 2), "review_count": review_count}
    return result


def get_reviews_by_date_range(start_date: str, end_date: str) -> pd.DataFrame:
    """Get reviews within a date range."""
    _ensure_loaded()
    if _reviews_df is None or _reviews_df.empty:
        return pd.DataFrame()
    if "review_date" not in _reviews_df.columns:
        return pd.DataFrame()
    try:
        mask = (
            (_reviews_df["review_date"] >= start_date)
            & (_reviews_df["review_date"] <= end_date)
        )
        return _reviews_df[mask].copy()
    except Exception:
        return pd.DataFrame()


def get_most_mentioned_homestays(n: int = 10) -> List[Dict[str, any]]:
    """Get most frequently reviewed homestays."""
    _ensure_loaded()
    if _reviews_df is None or _reviews_df.empty or "homestay_name" not in _reviews_df.columns:
        return []
    homestay_counts = _reviews_df["homestay_name"].value_counts().head(n)
    results: List[Dict[str, any]] = []
    for name, count in homestay_counts.items():
        results.append({"homestay": name, "review_count": int(count)})
    return results


def get_sentiment_by_topic(topic: str) -> Dict[str, any]:
    """Get sentiment breakdown for a specific review topic."""
    _ensure_loaded()
    if _reviews_df is None or _reviews_df.empty:
        return {"topic": topic, "positive": 0, "neutral": 0, "negative": 0, "total": 0}
    if "review_topic" not in _reviews_df.columns or "sentiment" not in _reviews_df.columns:
        return {"topic": topic, "positive": 0, "neutral": 0, "negative": 0, "total": 0}
    topic_df = _reviews_df[_reviews_df["review_topic"] == topic]
    if topic_df.empty:
        return {"topic": topic, "positive": 0, "neutral": 0, "negative": 0, "total": 0}
    counts = topic_df["sentiment"].value_counts()
    result: Dict[str, any] = {
        "topic": topic,
        "total": len(topic_df),
        "positive": int(counts.get("Positive", 0)),
        "neutral": int(counts.get("Neutral", 0)),
        "negative": int(counts.get("Negative", 0)),
    }
    # Calculate percentages
    if result["total"] > 0:
        result["positive_pct"] = round(result["positive"] / result["total"] * 100, 1)
        result["neutral_pct"] = round(result["neutral"] / result["total"] * 100, 1)
        result["negative_pct"] = round(result["negative"] / result["total"] * 100, 1)
    else:
        result["positive_pct"] = 0
        result["neutral_pct"] = 0
        result["negative_pct"] = 0
    return result


# ---- Combined Analytics ----

def get_combined_insights(destination_name: str) -> Dict[str, any]:
    """Get combined insights from both footfall and reviews datasets.

    Returns a comprehensive analytics package for a destination,
    useful for crowd score calibration and marketing decisions.
    """
    _ensure_loaded()

    footfall = get_destination_footfall(destination_name)
    categories = get_destination_categories()
    category = categories.get(destination_name, "Unknown")

    # Reviews stats
    avg_rating = get_average_rating()
    sentiment_dist = get_sentiment_distribution()
    top_topics = get_top_review_topics(5)

    # Homestay metrics
    most_mentioned = get_most_mentioned_homestays(5)
    rating_by_guest = get_rating_by_guest_type()

    return {
        "destination": destination_name,
        "footfall": footfall,
        "category": category,
        "average_rating": avg_rating,
        "sentiment_distribution": sentiment_dist,
        "top_review_topics": top_topics,
        "most_mentioned_homestays": most_mentioned,
        "rating_by_guest_type": rating_by_guest,
        "total_reviews": len(_reviews_df) if _reviews_df is not None else 0,
    }


# Convenience wrappers
def get_footfall_data_path() -> str:
    """Return the path to the footfall dataset."""
    return _FOOTFALL_PATH


def get_reviews_data_path() -> str:
    """Return the path to the reviews dataset."""
    return _REVIEWS_PATH


# Global instances
_footfall_service = None
_reviews_service = None


def get_footfall_service():
    """Get the footfall calibration service instance."""
    global _footfall_service
    if _footfall_service is None:
        from app.services.footfall_calibration import FootfallCalibrationService
        _footfall_service = FootfallCalibrationService()
    return _footfall_service


def get_reviews_service():
    """Get the reviews analytics service instance."""
    global _reviews_service
    if _reviews_service is None:
        _reviews_service = TourismAnalytics()
    return _reviews_service