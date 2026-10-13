from datetime import date

import sqlite3
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.api.dependencies import get_database
from app.api.rate_limit import limiter
from app.schemas.booking import (
    DemoBookingReceipt,
    DemoBookingRequest,
    MockInventoryResponse,
)
from app.services.booking import create_demo_booking_request, get_mock_inventory


router = APIRouter(prefix="/api", tags=["demo bookings"])


@router.get(
    "/homestays/{homestay_id}/inventory",
    response_model=MockInventoryResponse,
)
def homestay_inventory(
    homestay_id: int,
    check_in: date = Query(),
    check_out: date = Query(),
    connection: sqlite3.Connection = Depends(get_database),
) -> dict:
    return get_mock_inventory(
        connection,
        homestay_id=homestay_id,
        check_in=check_in,
        check_out=check_out,
    )


@router.post("/booking-requests", response_model=DemoBookingReceipt)
@limiter.limit("10/minute")
def submit_demo_booking_request(
    request: Request,
    payload: DemoBookingRequest,
    connection: sqlite3.Connection = Depends(get_database),
) -> dict:
    if not payload.check_in < payload.check_out:
        raise HTTPException(status_code=422, detail="Check-out must be after check-in.")
    return create_demo_booking_request(connection, payload)
