import json
from datetime import date

import pytest

from app.integrations.llm_client import LLMProviderError, parse_text_only_response
from app.services.itinerary import build_itinerary
from app.schemas.itinerary import ItineraryRequest
from app.db.database import connect_database
from tests.asgi_client import TestClient


class FakeTextGenerator:
    def __init__(self, response: str) -> None:
        self.response = response

    def generate(self, prompt: str) -> str:
        assert "Do not provide IDs" in prompt
        return self.response


class FailedTextGenerator:
    def generate(self, _prompt: str) -> str:
        if not _prompt:
            raise ValueError("prompt must not be empty")
        raise LLMProviderError("provider unavailable")


def test_text_output_rejects_ids_and_other_structural_fields() -> None:
    response = json.dumps({"day_text": ["A calm pause and a gentle look around."], "destination_id": 1})

    with pytest.raises(ValueError, match="only the day_text"):
        parse_text_only_response(response, 1)


def test_text_output_rejects_factual_claims() -> None:
    with pytest.raises(ValueError, match="prohibited factual claim"):
        parse_text_only_response(
            json.dumps({"day_text": ["Travel for 20 minutes to a lovely viewpoint."]}),
            1,
        )


def test_valid_llm_output_changes_only_the_text_field(catalogue_path) -> None:
    request = ItineraryRequest(
        start_date=date(2026, 10, 17), days=1, destination_ids=[2], use_llm=True
    )
    text = "Take a gentle pause and enjoy the day at your own pace."

    with connect_database(catalogue_path) as connection:
        result = build_itinerary(
            connection,
            request,
            request_id="test-id",
            llm_enabled=True,
            text_generator=FakeTextGenerator(json.dumps({"day_text": [text]})),
        )

    assert result["generation_mode"] == "llm_text_assisted"
    assert result["days"][0]["destination_id"] == 2
    assert result["days"][0]["date"] == date(2026, 10, 17)
    assert result["days"][0]["blocks"][0]["text"] == text
    assert result["days"][0]["crowd"]["data_mode"] == "curated_rule_estimate"


def test_disabled_llm_uses_template(catalogue_path) -> None:
    request = ItineraryRequest(
        start_date=date(2026, 10, 17), days=1, destination_ids=[2], use_llm=True
    )

    with connect_database(catalogue_path) as connection:
        result = build_itinerary(
            connection, request, request_id="test-id", llm_enabled=False,
            text_generator=FakeTextGenerator(json.dumps({"day_text": ["A gentle day outdoors."]})),
        )

    assert result["generation_mode"] == "rule_fallback"
    assert any("disabled" in warning for warning in result["warnings"])


@pytest.mark.parametrize(
    ("generator", "response"),
    [
        (FailedTextGenerator(), "provider unavailable"),
        (FakeTextGenerator(json.dumps({"day_text": ["Travel 20 minutes and relax."]})), "failed validation"),
    ],
)
def test_provider_failure_or_invalid_text_falls_back(catalogue_path, generator, response: str) -> None:
    request = ItineraryRequest(
        start_date=date(2026, 10, 17), days=1, destination_ids=[2], use_llm=True
    )

    with connect_database(catalogue_path) as connection:
        result = build_itinerary(
            connection, request, request_id="test-id", llm_enabled=True,
            text_generator=generator,
        )

    assert result["generation_mode"] == "rule_fallback"
    assert any(
        response in warning or "Optional text generation failed" in warning
        for warning in result["warnings"]
    )


def test_api_itinerary_response_has_exact_day_count(test_client: TestClient) -> None:
    response = test_client.post(
        "/api/itineraries",
        json={
            "start_date": "2026-10-17",
            "days": 2,
            "destination_ids": [2],
            "use_llm": True,
        },
    )

    assert response.status_code == 200
    assert response.json()["generation_mode"] == "rule_fallback"
    assert len(response.json()["days"]) == 2
    assert response.json()["request_id"] == response.headers["x-request-id"]
