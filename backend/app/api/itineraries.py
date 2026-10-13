import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.dependencies import get_database
from app.api.errors import request_id_for
from app.api.rate_limit import limiter
from app.schemas.itinerary import ItineraryRequest, ItineraryResponse
from app.services.itinerary import build_itinerary
from app.services.itinerary_validation import ItineraryValidationError


router = APIRouter(prefix="/api", tags=["itineraries"])


@router.post("/itineraries", response_model=ItineraryResponse)
@limiter.limit("10/minute")
def create_itinerary(
    request: Request,
    payload: ItineraryRequest,
    connection: sqlite3.Connection = Depends(get_database),
) -> dict:
    settings = request.app.state.settings
    try:
        return build_itinerary(
            connection,
            payload,
            request_id=request_id_for(request),
            llm_enabled=settings.enable_llm,
            text_generator=request.app.state.text_generator,
        )
    except ItineraryValidationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
