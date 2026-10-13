from pathlib import Path

from app.config import Settings
from app.main import create_app
from tests.asgi_client import TestClient


def test_catalogue_lists_only_enabled_curated_records(test_client: TestClient) -> None:
    response = test_client.get("/api/destinations?region=Uttarakhand&tag=hiking")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [2]
    assert response.json()[0]["source_label"] == "Reviewed source"


def test_catalogue_detail_and_homestays_are_destination_bound(test_client: TestClient) -> None:
    destination = test_client.get("/api/destinations/1")
    stays = test_client.get("/api/homestays?destination_id=2")

    assert destination.status_code == 200
    assert [item["destination"]["id"] for item in destination.json()["alternatives"]] == [3, 2]
    assert stays.status_code == 200
    assert [stay["destination_id"] for stay in stays.json()] == [2]
    assert stays.json()[0]["public_contact"] is None
    assert stays.json()[0]["booking_url"] is None


def test_missing_catalogue_records_have_stable_404s(test_client: TestClient) -> None:
    response = test_client.get("/api/destinations/999")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_missing_database_returns_actionable_error(tmp_path: Path) -> None:
    settings = Settings(
        database_path=tmp_path / "not-created.db",
        cors_origins=("http://localhost:5173",),
        enable_llm=False,
    )
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/destinations")

    assert response.status_code == 503
    assert "seed command" in response.json()["error"]["message"]


def test_request_id_is_validated_and_returned_in_header(test_client: TestClient) -> None:
    safe = test_client.get("/api/health", headers={"X-Request-ID": "ui-42"})
    unsafe = test_client.get("/api/health", headers={"X-Request-ID": "bad id"})

    assert safe.headers["x-request-id"] == "ui-42"
    assert unsafe.headers["x-request-id"] != "bad id"


def test_cors_allows_only_configured_origin(test_client: TestClient) -> None:
    allowed = test_client.request(
        "OPTIONS",
        "/api/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    denied = test_client.get("/api/health", headers={"Origin": "https://untrusted.example"})

    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "access-control-allow-origin" not in denied.headers
