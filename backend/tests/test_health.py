from app.api.health import get_health
from app.main import app


def test_health_endpoint_returns_ok() -> None:
    assert get_health() == {"status": "ok"}


def test_health_endpoint_is_registered() -> None:
    operation = app.openapi()["paths"]["/api/health"]["get"]

    assert operation["responses"]["200"]
