from tests.asgi_client import TestClient


def test_recommendation_to_itinerary_uses_only_returned_curated_ids(test_client: TestClient) -> None:
    recommendation = test_client.post(
        "/api/recommendations",
        json={
            "region": "Uttarakhand",
            "start_destination_id": 1,
            "start_date": "2026-10-17",
            "days": 1,
            "interests": ["hiking"],
        },
    )

    assert recommendation.status_code == 200
    selected_id = recommendation.json()["items"][0]["destination"]["id"]
    itinerary = test_client.post(
        "/api/itineraries",
        json={
            "start_date": "2026-10-17",
            "days": 1,
            "destination_ids": [selected_id],
        },
    )

    assert itinerary.status_code == 200
    result = itinerary.json()
    assert result["days"][0]["destination_id"] == selected_id
    assert result["days"][0]["destination_name"] == "Quiet Alternative"
    assert result["generation_mode"] == "rule_fallback"
