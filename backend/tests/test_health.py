from app.api.health import get_health
from app.main import app


def test_health_endpoint_returns_ok() -> None:
    assert get_health() == {"status": "ok"}


def test_health_endpoint_is_registered() -> None:
    operation = app.openapi()["paths"]["/api/health"]["get"]

    assert operation["responses"]["200"]


def test_data_sources_endpoint_reports_missing_weather_until_refreshed(test_client) -> None:
    response = test_client.get("/api/data-sources")

    assert response.status_code == 200
    sources = {source["source"]: source for source in response.json()["sources"]}
    assert sources["open_meteo_forecast"]["status"] == "missing"
    assert sources["open_meteo_forecast"]["retrieved_at"] is None
    assert sources["open_meteo_archive"]["status"] == "missing"
