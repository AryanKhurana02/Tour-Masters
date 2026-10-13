import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.dependencies import get_database
from app.api.errors import request_id_for
from app.api.rate_limit import limiter
from app.repositories.destination_repository import get_destination
from app.schemas.recommendation import RecommendationRequest, RecommendationResponse
from app.services.recommendation import recommend


router = APIRouter(prefix="/api", tags=["recommendations"])


@router.post("/recommendations", response_model=RecommendationResponse)
@limiter.limit("30/minute")
def create_recommendations(
    request: Request,
    payload: RecommendationRequest,
    connection: sqlite3.Connection = Depends(get_database),
) -> dict:
    if payload.start_destination_id is not None:
        origin = get_destination(connection, payload.start_destination_id)
        if origin is None:
            raise HTTPException(status_code=404, detail="Starting destination was not found.")
        if origin["region"].casefold() != payload.region.casefold():
            raise HTTPException(
                status_code=400,
                detail="Starting destination must belong to the requested region.",
            )
    items, warnings = recommend(connection, payload)
    return {
        "request_id": request_id_for(request),
        "items": items,
        "warnings": warnings,
    }
