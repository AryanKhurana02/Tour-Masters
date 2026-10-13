from __future__ import annotations

import json
import re
from typing import Protocol


class TextOnlyGenerator(Protocol):
    def generate(self, prompt: str) -> str:
        """Return JSON containing exactly one short text string per requested day."""
        raise NotImplementedError


class LLMProviderError(Exception):
    """Raised by a provider adapter when its configured service is unavailable."""


_UNSAFE_CLAIM = re.compile(
    r"\d|[$€£₹]|"
    r"\b(?:INR|USD|EUR|GBP|price|cost|contact|phone|email|book|booking|available|"
    r"availability|minutes?|hours?|kilomet(?:er|re)s?|miles?|closed|open|permit|"
    r"weather|safe|dangerous)\b",
    re.IGNORECASE,
)


def create_text_prompt(day_count: int) -> str:
    return (
        "Write gentle, non-factual itinerary prose only. Return JSON with exactly one key, "
        '"day_text", whose value is an array of exactly '
        f"{day_count} short strings, one for each day. Do not provide IDs, names, dates, "
        "times, prices, contact or booking details, availability, travel or distance claims, "
        "weather, safety, access or closure claims. Keep each string general and optional; "
        "all itinerary facts are supplied separately by the application."
    )


def parse_text_only_response(raw_response: str, expected_days: int) -> list[str]:
    try:
        payload = json.loads(raw_response)
    except json.JSONDecodeError as error:
        raise ValueError("LLM response was not valid JSON.") from error
    if not isinstance(payload, dict) or set(payload) != {"day_text"}:
        raise ValueError("LLM response must contain only the day_text field.")
    day_text = payload["day_text"]
    if not isinstance(day_text, list) or len(day_text) != expected_days:
        raise ValueError("LLM response must contain exactly one text entry per itinerary day.")
    normalized: list[str] = []
    for text in day_text:
        if not isinstance(text, str):
            raise ValueError("LLM day text must be a string.")
        value = text.strip()
        if not 8 <= len(value) <= 280:
            raise ValueError("LLM day text must contain between 8 and 280 characters.")
        if _UNSAFE_CLAIM.search(value):
            raise ValueError("LLM day text contains a prohibited factual claim.")
        normalized.append(value)
    return normalized
