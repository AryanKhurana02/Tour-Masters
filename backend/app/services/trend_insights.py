from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd

from app.services.footfall_calibration import (
    get_destination_footfall,
    get_statewide_footfall,
    get_destination_categories,
    get_top_destinations,
    get_footfall_by_category,
)

logger = logging.getLogger("pytrends_trends")

# Global instance for the backend
trend_insights = None  # Initialized on demand


class TrendInsights:
    """Fetches Google Trends data to enhance crowd score estimates.

    Uses Google Trends search volume data as a proxy for customer interest
    and potential crowd levels at destinations. Data is cached and refreshed
    periodically; falls back to rule-based estimates when unavailable.
    Also integrates real footfall data from the Uttarakhand tourism dataset
    to provide grounded, data-backed crowd predictions.
    """

    def __init__(
        self,
        hl: str = "en-US",
        tz: int = 360,
        geo: str = "US",
        timeout: int = 30,
    ) -> None:
        self.hl = hl
        self.tz = tz
        self.geo = geo
        self.timeout = timeout
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl = timedelta(hours=24)

    @staticmethod
    def _ensure_service() -> "TrendInsights":
        """Lazy initialization of the global service instance."""
        global trend_insights
        if trend_insights is None:
            trend_insights = TrendInsights()
        return trend_insights

    @staticmethod
    def _get_footfall_service():
        """Access the footfall calibration service."""
        from app.services.footfall_calibration import (
            get_destination_footfall,
            get_statewide_footfall,
        )
        return get_destination_footfall, get_statewide_footfall

    async def fetch_interest_over_time(
        self, keywords: List[str], timeframe: str = "today 12-m"
    ) -> Dict[str, float]:
        """Fetch Google Trends interest over time for keywords.

        Returns a dict mapping keyword to average relative search interest (0-100).
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._fetch_sync, keywords, timeframe
        )

    def _fetch_sync(self, keywords: List[str], timeframe: str) -> Dict[str, float]:
        """Synchronous Google Trends fetch (runs in thread executor)."""
        try:
            from pytrends.request import TrendReq

            pytrend = TrendReq(hl=self.hl, tz=self.tz)
            pytrend.build_payload(keywords, cat=0, timeframe=timeframe, geo=self.geo)
            df = pytrend.interest_over_time()

            if df.empty:
                logger.warning("Google Trends returned empty data for %s", keywords)
                return {kw: 50.0 for kw in keywords}

            # Get average interest per keyword
            results: Dict[str, float] = {}
            for kw in keywords:
                if kw in df.columns:
                    series = df[kw].dropna()
                    if not series.empty:
                        avg_interest = float(series.mean())
                        results[kw] = max(0.0, min(100.0, avg_interest))
                    else:
                        results[kw] = 50.0
                else:
                    results[kw] = 50.0

            logger.info("Google Trends data: %s", results)
            return results

        except Exception as error:  # pylint: disable=broad-except
            logger.error("Google Trends fetch failed: %s", error, exc_info=True)
            return {kw: 50.0 for kw in keywords}

    async def fetch_related_queries(
        self, keyword: str
    ) -> Dict[str, List[str]]:
        """Fetch related rising queries for a keyword.

        Returns dict with 'rising' and 'top' query lists.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._fetch_related_sync, keyword)

    def _fetch_related_sync(self, keyword: str) -> Dict[str, List[str]]:
        """Synchronous related queries fetch."""
        try:
            from pytrends.request import TrendReq

            pytrend = TrendReq(hl=self.hl, tz=self.tz)
            pytrend.build_payload([keyword], cat=0, timeframe="today 12-m", geo=self.geo)
            related = pytrend.related_queries()

            rising: List[str] = []
            top: List[str] = []

            if keyword in related and related[keyword] is not None:
                if "rising" in related[keyword]:
                    rising = related[keyword]["rising"]["query"].tolist()
                if "top" in related[keyword]:
                    top = related[keyword]["top"]["query"].tolist()

            logger.info(
                "Related queries for '%s': rising=%s, top=%s", keyword, rising[:5], top[:5]
            )
            return {"rising": rising, "top": top}

        except Exception as error:  # pylint: disable=broad-except
            logger.error("Related queries fetch failed for '%s': %s", keyword, error)
            return {"rising": [], "top": []}

    async def enhance_crowd_score(
        self,
        destination_name: str,
        base_score: int,
        interests: List[str] | None = None,
    ) -> Dict[str, Any]:
        """Enhance a base crowd score with Google Trends and footfall data.

        Combines three data sources:
        1. Rule-based base score (0-100) from the existing system
        2. Google Trends search volume interest (0-100)
        3. Real footfall visitor counts from the Uttarakhand tourism dataset

        The function calibrates the base score using:
        - If Google Trends interest > 70: add up to 20 points (potentially higher crowds)
        - If Google Trends interest < 30: subtract up to 15 points (potentially lower crowds)
        - If footfall data available: adjust proportionally to known visitor volumes
        - Higher footfall = higher baseline expectation, but normalized

        Returns dict with:
        - enhanced_score: combined score (0-100), rounded
        - trends_data: Google Trends metrics (avg interest per keyword)
        - footfall_data: real visitor counts (domestic, foreign, total)
        - category: destination category from the footfall dataset
        - confidence: combined confidence score (0.0-1.0)
        """
        # Step 1: Generate search keywords for this destination
        keywords = self._generate_keywords(destination_name, interests or [])

        if not keywords:
            # No keywords: just return footfall-based calibration
            footfall = get_destination_footfall(destination_name)
            cat = get_destination_categories().get(destination_name, "Unknown")
            return {
                "enhanced_score": base_score,
                "trends_data": {},
                "footfall_data": footfall,
                "category": cat,
                "confidence": 0.3,
            }

        # Step 2: Fetch Google Trends interest data (with caching)
        cache_key = "+".join(keywords)
        now = datetime.utcnow()
        if cache_key in self._cache:
            cached_at, cached_data = self._cache[cache_key]
            if now - cached_at < self._cache_ttl:
                trends_data = cached_data
            else:
                trends_data = await self.fetch_interest_over_time(keywords)
                self._cache[cache_key] = (now, trends_data)
        else:
            trends_data = await self.fetch_interest_over_time(keywords)
            self._cache[cache_key] = (datetime.utcnow(), trends_data)

        # Step 3: Get footfall data for this destination
        footfall = get_destination_footfall(destination_name)
        category = get_destination_categories().get(destination_name, "Unknown")

        # Step 4: Calibrate the score
        # Start with base score
        enhanced_score = base_score

        # Google Trends adjustment
        trends_adjustment = 0.0
        trends_keywords: Dict[str, float] = {}
        for kw, interest in trends_data.items():
            trends_keywords[kw] = interest
            if interest > 70:  # High interest = potentially higher crowds
                increase = min(20, (interest - 50) * 0.5)  # 0-20 point boost
                trends_adjustment += increase
            elif interest < 30:  # Low interest = potentially lower crowds
                decrease = min(15, (50 - interest) * 0.3)  # 0-15 point reduction
                trends_adjustment -= decrease

        # Footfall adjustment
        # Normalize footfall to a 0-1 scale relative to state total
        state_total = get_statewide_footfall()["total"]
        if state_total > 0 and footfall["total"] > 0:
            footfall_ratio = min(1.0, footfall["total"] / state_total)
        else:
            footfall_ratio = 0.0

        # If destination has significant footfall, adjust score proportionally
        if footfall["total"] > 10000:  # Significant destination
            # Scale adjustment: 0-15 points based on footfall proportion
            footfall_adjustment = footfall_ratio * 15.0
        else:
            # Small destination: smaller adjustment
            footfall_adjustment = footfall_ratio * 5.0

        # Apply combined adjustments
        enhanced_score = base_score + trends_adjustment + footfall_adjustment
        enhanced_score = max(0, min(100, enhanced_score))

        # Calculate confidence based on data quality
        confidence_components: List[float] = []

        # Google Trends confidence: based on how many keywords had data
        valid_trends = sum(1 for v in trends_data.values() if v > 0)
        trends_confidence = min(1.0, valid_trends / max(len(keywords), 1))
        confidence_components.append(trends_confidence)

        # Footfall confidence: based on whether we matched a known destination
        if footfall["total"] > 0:
            footfall_confidence = 0.6 + 0.2 * min(1.0, footfall["total"] / 1_000_000)
        else:
            footfall_confidence = 0.3
        confidence_components.append(footfall_confidence)

        # Category confidence: whether we found a known category
        cat = get_destination_categories().get(destination_name, "")
        if cat and cat != "Unknown":
            category_confidence = 0.5
        else:
            category_confidence = 0.1
        confidence_components.append(category_confidence)

        confidence = sum(confidence_components) / len(confidence_components)

        return {
            "enhanced_score": round(enhanced_score),
            "trends_data": trends_data,
            "footfall_data": footfall,
            "category": category,
            "confidence": round(confidence, 2),
        }

    def _generate_keywords(
        self, destination_name: str, interests: List[str] | None
    ) -> List[str]:
        """Generate Google Trends search keywords for a destination."""
        keywords: List[str] = [destination_name.lower().strip()]

        if interests:
            normalized = [i.strip().casefold() for i in interests[:3]]
            keywords.extend(normalized)

        modifiers = ["travel", "tourism", "visiting", "best", "crowd"]
        keywords.extend(modifiers)

        # Deduplicate while preserving order
        seen: set = set()
        unique_keywords: List[str] = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique_keywords.append(kw)

        return unique_keywords[:5]


# Convenience wrapper
async def enhance_crowd_score_with_trends(
    destination_name: str,
    base_score: int,
    interests: List[str] | None = None,
) -> Dict[str, Any]:
    """Convenience wrapper for the trend insights service."""
    service = TrendInsights._ensure_service()
    return await service.enhance_crowd_score(destination_name, base_score, interests)