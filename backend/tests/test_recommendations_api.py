from tests.asgi_client import TestClient


def _request(**overrides: object) -> dict:
    return {
        "region": "Uttarakhand",
        "start_destination_id": 1,
        "start_date": "2026-10-17",
        "days": 1,
        "interests": ["hiking"],
        "budget_per_night_max": 1200,
        "avoid_crowds": True,
        **overrides,
    }


def test_recommendation_api_returns_backend_scores_and_provenance(test_client: TestClient) -> None:
    response = test_client.post("/api/recommendations", json=_request())

    assert response.status_code == 200
    result = response.json()
    assert result["request_id"] == response.headers["x-request-id"]
    assert len(result["items"]) == 1
    item = result["items"][0]
    assert item["destination"]["id"] == 2
    assert item["rank_score"] == 82.75
    assert item["crowd"]["score"] == 35
    assert item["crowd"]["level"] == "Moderate"
    assert item["crowd"]["estimated"] is True
    assert item["crowd"]["data_mode"] == "curated_rule_estimate"
    assert item["crowd"]["reviewed_at"] == "2026-09-15"


def test_recommendation_validation_does_not_echo_input_values(test_client: TestClient) -> None:
    response = test_client.post(
        "/api/recommendations",
        json=_request(budget_per_night_max="private-user-value"),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert "private-user-value" not in response.text


def test_unknown_start_destination_returns_not_found(test_client: TestClient) -> None:
    response = test_client.post("/api/recommendations", json=_request(start_destination_id=999))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_empty_alternative_pool_can_be_explicitly_broadened(test_client: TestClient) -> None:
    response = test_client.post(
        "/api/recommendations",
        json=_request(start_destination_id=4, allow_broadened_search=True),
    )

    assert response.status_code == 200
    result = response.json()
    assert any("No reviewed look-alike links" in warning for warning in result["warnings"])
    assert all(item["destination"]["id"] != 4 for item in result["items"])


def test_recommendation_route_is_rate_limited(test_client: TestClient) -> None:
    response = None
    for _ in range(31):
        response = test_client.post("/api/recommendations", json=_request())

    assert response is not None
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "rate_limit_exceeded"
