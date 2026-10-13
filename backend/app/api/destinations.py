import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_database
from app.repositories.destination_repository import (
    get_destination,
    list_alternatives,
    list_destinations,
    list_homestays,
)
from app.schemas.destination import DestinationDetail, DestinationRead, HomestayRead
from app.services.seasonality import get_all_months as get_all_seasonality
from app.services.weather_history import get_all_months_climatology, get_monthly_climatology


router = APIRouter(prefix="/api", tags=["catalogue"])


@router.get("/destinations", response_model=list[DestinationRead])
def destinations(
    region: str | None = Query(default=None, min_length=1, max_length=120),
    tag: str | None = Query(default=None, min_length=1, max_length=40),
    connection: sqlite3.Connection = Depends(get_database),
) -> list[dict]:
    return list_destinations(connection, region=region, tag=tag)


@router.get("/destinations/{destination_id}", response_model=DestinationDetail)
def destination_detail(
    destination_id: int,
    connection: sqlite3.Connection = Depends(get_database),
) -> dict:
    destination = get_destination(connection, destination_id)
    if destination is None:
        raise HTTPException(status_code=404, detail="Destination was not found.")
    return {**destination, "alternatives": list_alternatives(connection, destination_id)}


@router.get("/homestays", response_model=list[HomestayRead])
def homestays(
    destination_id: int = Query(gt=0),
    connection: sqlite3.Connection = Depends(get_database),
) -> list[dict]:
    if get_destination(connection, destination_id) is None:
        raise HTTPException(status_code=404, detail="Destination was not found.")
    return list_homestays(connection, destination_id)


@router.get("/destinations/{destination_id}/weather-history")
def destination_weather_history(
    destination_id: int,
    connection: sqlite3.Connection = Depends(get_database),
) -> dict:
    """Return 5-year monthly climatology and statewide seasonality for a destination."""
    destination = get_destination(connection, destination_id)
    if destination is None:
        raise HTTPException(status_code=404, detail="Destination was not found.")

    climatology = get_all_months_climatology(destination["name"])
    seasonality = get_all_seasonality()

    return {
        "destination_id": destination_id,
        "destination_name": destination["name"],
        "monthly_climatology": climatology,
        "seasonality": seasonality,
    }
