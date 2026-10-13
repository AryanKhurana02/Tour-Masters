from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.dependencies import get_database
from app.api.rate_limit import limiter
from app.config import Settings
from app.integrations.openrouteservice import OpenRouteServiceError, get_driving_route
from app.repositories.destination_repository import get_destination
from app.schemas.route import RouteEstimate


router = APIRouter(prefix="/api", tags=["route context"])
_MUSSOORIE_DESTINATION_ID = 5
_DEHRADUN_HUB = (78.0322, 30.3165)
_MUSSOORIE_APPROXIMATE_CENTER = (78.0664, 30.4598)


@router.get(
    "/destinations/{destination_id}/route-from-hub",
    response_model=RouteEstimate,
)
@limiter.limit("5/minute")
def route_from_dehradun_hub(
    request: Request,
    destination_id: int,
    connection: sqlite3.Connection = Depends(get_database),
) -> dict:
    destination = get_destination(connection, destination_id)
    if destination is None:
        raise HTTPException(status_code=404, detail="Destination was not found.")
    if destination_id != _MUSSOORIE_DESTINATION_ID or destination["name"] != "Mussoorie":
        raise HTTPException(
            status_code=422,
            detail="Route context is available only for the Mussoorie case study.",
        )

    settings: Settings = request.app.state.settings
    if not settings.ors_api_key:
        raise HTTPException(
            status_code=503,
            detail="OpenRouteService is not configured; set ORS_API_KEY in backend/.env.",
        )

    try:
        route = get_driving_route(
            settings.ors_api_key,
            start_lng=_DEHRADUN_HUB[0],
            start_lat=_DEHRADUN_HUB[1],
            end_lng=_MUSSOORIE_APPROXIMATE_CENTER[0],
            end_lat=_MUSSOORIE_APPROXIMATE_CENTER[1],
        )
    except OpenRouteServiceError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    return {
        "destination_id": destination["id"],
        "origin_label": "Dehradun hub",
        "destination_name": destination["name"],
        **route,
        "estimated": True,
        "source": "OpenRouteService",
        "retrieved_at": datetime.now(timezone.utc),
        "notes": [
            "This is an OpenRouteService driving estimate between approximate Dehradun and Mussoorie town-centre coordinates, not door-to-door navigation.",
            "Route distance and duration may change and do not report road closures, road safety, weather hazards, or accessibility conditions.",
            "This Dehradun hub baseline is separate from the crowd estimate and is not a personalized route.",
        ],
    }


@router.get(
    "/destinations/{destination_id}/live-metrics",
    tags=["live metrics"],
)
def get_live_metrics(
    destination_id: int,
    connection: sqlite3.Connection = Depends(get_database),
) -> dict:
    destination = get_destination(connection, destination_id)
    if destination is None:
        raise HTTPException(status_code=404, detail="Destination was not found.")

    cutoff = datetime.now(timezone.utc) - timedelta(hours=2)
    metric = connection.execute(
        """
        SELECT live_crowd_index, data_source, timestamp
        FROM live_tourist_metrics
        WHERE destination_id = ? AND timestamp >= ?
        ORDER BY timestamp DESC
        LIMIT 1
        """,
        (destination_id, cutoff.isoformat(timespec="seconds")),
    ).fetchone()

    if not metric:
        return {
            "live_crowd_index": 50,
            "data_source": "fallback_estimate",
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "note": "Live data not yet available. Using neutral estimate.",
        }

    return {
        "destination_id": destination_id,
        "live_crowd_index": metric["live_crowd_index"],
        "data_source": metric["data_source"],
        "timestamp": metric["timestamp"],
    }
