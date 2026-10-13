from datetime import datetime, timezone

from app.db.database import connect_database
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


def test_recommendation_uses_fresh_weather_forecast_from_sqlite(
    test_client: TestClient,
    catalogue_path,
) -> None:
    with connect_database(catalogue_path) as connection:
        with connection:
            connection.execute(
                """
                INSERT INTO weather_forecasts (
                    destination_id, forecast_date, temp_max, temp_min, temp_mean,
                    precipitation_mm, weather_visit_tendency, retrieved_at, expires_at, source_url
                ) VALUES (2, '2026-10-17', 20, 10, 15, 0, 100,
                          '2026-10-13T12:00:00+00:00', '2099-10-14T12:00:00+00:00',
                          'https://open-meteo.com/en/docs')
                """
            )

    response = test_client.post("/api/recommendations", json=_request())

    assert response.status_code == 200
    crowd = response.json()["items"][0]["crowd"]
    assert crowd["weather_visit_tendency"] == 100
    assert crowd["score"] == 42
    assert any("Open-Meteo forecast" in note for note in crowd["notes"])


def test_recommendations_without_start_place_search_region_wide(test_client: TestClient) -> None:
    payload = _request(avoid_crowds=False)
    payload.pop("start_destination_id")

    response = test_client.post("/api/recommendations", json=payload)

    assert response.status_code == 200
    assert {item["destination"]["id"] for item in response.json()["items"]} == {1, 2, 3, 4}


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
