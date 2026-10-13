from __future__ import annotations

import json
import sqlite3
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request

import pytest

from app.config import Settings
from app.integrations.openrouteservice import (
    ROUTE_URL,
    OpenRouteServiceError,
    get_driving_route,
)
from app.main import create_app
from tests.asgi_client import TestClient


class _Response:
    def __init__(self, payload: dict) -> None:
        self._body = BytesIO(json.dumps(payload).encode("utf-8"))

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_: object) -> None:
        self._body.close()

    def read(self) -> bytes:
        return self._body.read()


def _get_route(api_key: str = "server-only-token") -> dict[str, int]:
    return get_driving_route(
        api_key,
        start_lng=78.0322,
        start_lat=30.3165,
        end_lng=78.0664,
        end_lat=30.4598,
    )


def test_route_request_uses_ors_driving_car_endpoint_and_lon_lat_order() -> None:
    with patch(
        "app.integrations.openrouteservice.urlopen",
        return_value=_Response(
            {"routes": [{"summary": {"distance": 34567.4, "duration": 3720}}]}
        ),
    ) as open_url:
        route = _get_route()

    request = open_url.call_args.args[0]
    assert isinstance(request, Request)
    assert request.full_url == ROUTE_URL
    assert request.get_header("Authorization") == "server-only-token"
    assert request.get_header("Accept") == "application/json"
    assert json.loads(request.data) == {
        "coordinates": [[78.0322, 30.3165], [78.0664, 30.4598]],
        "units": "m",
    }
    assert open_url.call_args.kwargs == {"timeout": 8}
    assert route == {"distance_meters": 34567, "duration_seconds": 3720}


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"routes": []},
        {"routes": [{"summary": {"distance": 0, "duration": 3720}}]},
        {"routes": [{"summary": {"distance": 10, "duration": -1}}]},
    ],
)
def test_route_rejects_invalid_provider_response(payload: dict) -> None:
    with patch(
        "app.integrations.openrouteservice.urlopen",
        return_value=_Response(payload),
    ):
        with pytest.raises(OpenRouteServiceError):
            _get_route()


@pytest.mark.parametrize(
    ("status", "message"),
    [
        (401, "rejected the configured API token"),
        (403, "check API access and usage limits"),
    ],
)
def test_route_provider_auth_errors_are_actionable_but_do_not_expose_body(
    status: int,
    message: str,
) -> None:
    provider_error = HTTPError(
        ROUTE_URL,
        status,
        "Provider error",
        hdrs=None,
        fp=BytesIO(b"provider body must not be echoed"),
    )
    with patch(
        "app.integrations.openrouteservice.urlopen",
        side_effect=provider_error,
    ):
        with pytest.raises(OpenRouteServiceError, match=message) as error:
            _get_route()
    assert "provider body must not be echoed" not in str(error.value)


def test_route_endpoint_requires_configured_token_and_mussoorie_destination(
    catalogue_path: Path,
) -> None:
    with sqlite3.connect(catalogue_path) as connection:
        connection.execute(
            "INSERT INTO destinations "
            "(id, name, district, region, description, tags, best_months, popularity_score, "
            "source_label, source_url, reviewer, reviewed_at, enabled) "
            "VALUES (5, 'Mussoorie', 'Dehradun', 'Uttarakhand', '', '', '', NULL, "
            "'source', 'https://example.test/mussoorie', 'reviewer', '2026-10-13', 1)"
        )
        connection.commit()
    settings = Settings(
        database_path=catalogue_path,
        cors_origins=("http://localhost:5173",),
        enable_llm=False,
    )
    with TestClient(create_app(settings)) as client:
        missing_token = client.get("/api/destinations/5/route-from-hub")
        not_case_study = client.get("/api/destinations/2/route-from-hub")

    assert missing_token.status_code == 503
    assert "ORS_API_KEY" in missing_token.json()["error"]["message"]
    assert not_case_study.status_code == 422


def test_route_endpoint_returns_only_separate_mussoorie_route_context(
    catalogue_path: Path,
) -> None:
    with sqlite3.connect(catalogue_path) as connection:
        connection.execute(
            "INSERT INTO destinations "
            "(id, name, district, region, description, tags, best_months, popularity_score, "
            "source_label, source_url, reviewer, reviewed_at, enabled) "
            "VALUES (5, 'Mussoorie', 'Dehradun', 'Uttarakhand', '', '', '', NULL, "
            "'source', 'https://example.test/mussoorie', 'reviewer', '2026-10-13', 1)"
        )
        connection.commit()
    settings = Settings(
        database_path=catalogue_path,
        cors_origins=("http://localhost:5173",),
        enable_llm=False,
        ors_api_key="server-only-token",
    )
    with TestClient(create_app(settings)) as client:
        with patch(
            "app.api.routes.get_driving_route",
            return_value={"distance_meters": 34567, "duration_seconds": 3720},
        ) as get_route:
            response = client.get("/api/destinations/5/route-from-hub")

    assert response.status_code == 200
    data = response.json()
    assert data["destination_name"] == "Mussoorie"
    assert data["origin_label"] == "Dehradun hub"
    assert data["distance_meters"] == 34567
    assert data["duration_seconds"] == 3720
    assert data["source"] == "OpenRouteService"
    assert data["estimated"] is True
    assert any("accessibility" in note for note in data["notes"])
    assert get_route.call_args.args[0] == "server-only-token"
    assert get_route.call_args.kwargs["start_lng"] == 78.0322
    assert "server-only-token" not in response.text
