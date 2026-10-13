from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROUTE_URL = "https://api.openrouteservice.org/v2/directions/driving-car"


class OpenRouteServiceError(RuntimeError):
    pass


def get_driving_route(
    api_key: str,
    *,
    start_lng: float,
    start_lat: float,
    end_lng: float,
    end_lat: float,
) -> dict[str, int]:
    payload = json.dumps(
        {
            "coordinates": [
                [start_lng, start_lat],
                [end_lng, end_lat],
            ],
            "units": "m",
        }
    ).encode("utf-8")
    request = Request(
        ROUTE_URL,
        data=payload,
        headers={
            "Authorization": api_key,
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=8) as response:
            data = json.loads(response.read())
    except HTTPError as error:
        if error.code == 401:
            message = "OpenRouteService rejected the configured API token."
        elif error.code == 403:
            message = "OpenRouteService denied the request; check API access and usage limits."
        else:
            message = f"OpenRouteService returned HTTP {error.code}."
        raise OpenRouteServiceError(message) from error
    except (URLError, TimeoutError) as error:
        raise OpenRouteServiceError("OpenRouteService could not be reached.") from error
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise OpenRouteServiceError("OpenRouteService returned invalid JSON.") from error

    try:
        summary = data["routes"][0]["summary"]
        distance_meters = summary["distance"]
        duration_seconds = summary["duration"]
    except (KeyError, IndexError, TypeError) as error:
        raise OpenRouteServiceError(
            "OpenRouteService returned no usable driving route."
        ) from error

    if (
        isinstance(distance_meters, bool)
        or not isinstance(distance_meters, (int, float))
        or distance_meters <= 0
        or isinstance(duration_seconds, bool)
        or not isinstance(duration_seconds, (int, float))
        or duration_seconds < 0
    ):
        raise OpenRouteServiceError(
            "OpenRouteService returned invalid distance or duration."
        )

    return {
        "distance_meters": round(distance_meters),
        "duration_seconds": round(duration_seconds),
    }
