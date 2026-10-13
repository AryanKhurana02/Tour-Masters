from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from fastapi import HTTPException

from app.schemas.booking import DemoBookingRequest


def _inventory_rows(
    connection: sqlite3.Connection,
    homestay_id: int,
    check_in: date,
    check_out: date,
) -> list[sqlite3.Row]:
    return connection.execute(
        "SELECT inventory_date, total_units, available_units, inventory_mode, "
        "source_label, reviewed_at FROM homestay_inventory "
        "WHERE homestay_id = ? AND enabled = 1 AND inventory_date >= ? "
        "AND inventory_date < ? ORDER BY inventory_date",
        (homestay_id, check_in.isoformat(), check_out.isoformat()),
    ).fetchall()


def get_mock_inventory(
    connection: sqlite3.Connection,
    *,
    homestay_id: int,
    check_in: date,
    check_out: date,
) -> dict[str, Any]:
    if check_out <= check_in or (check_out - check_in).days > 30:
        raise HTTPException(status_code=422, detail="Choose dates for 1 to 30 nights.")
    stay = connection.execute(
        "SELECT id FROM homestays WHERE id = ? AND enabled = 1",
        (homestay_id,),
    ).fetchone()
    if stay is None:
        raise HTTPException(status_code=404, detail="Homestay was not found.")

    rows = _inventory_rows(connection, homestay_id, check_in, check_out)
    return {
        "homestay_id": homestay_id,
        "check_in": check_in,
        "check_out": check_out,
        "inventory_mode": "demo_mock",
        "days": [
            {
                "homestay_id": homestay_id,
                "date": row["inventory_date"],
                "total_units": row["total_units"],
                "available_units": row["available_units"],
                "inventory_mode": row["inventory_mode"],
                "source_label": row["source_label"],
                "reviewed_at": row["reviewed_at"],
            }
            for row in rows
        ],
        "warnings": [
            "These dates show mock inventory for a demo, not a homestay's actual availability."
        ],
    }


def create_demo_booking_request(
    connection: sqlite3.Connection,
    payload: DemoBookingRequest,
) -> dict[str, Any]:
    connection.execute("BEGIN IMMEDIATE")
    try:
        existing = connection.execute(
            "SELECT * FROM booking_requests WHERE client_request_id = ?",
            (str(payload.client_request_id),),
        ).fetchone()
        if existing is not None:
            if (
                existing["homestay_id"] != payload.homestay_id
                or existing["check_in"] != payload.check_in.isoformat()
                or existing["check_out"] != payload.check_out.isoformat()
                or existing["guest_count"] != payload.guest_count
            ):
                raise HTTPException(
                    status_code=409,
                    detail="This request ID was already used for a different demo request.",
                )
            receipt = _receipt_from_row(existing, payload.client_request_id)
            connection.commit()
            return receipt

        stay = connection.execute(
            "SELECT id FROM homestays WHERE id = ? AND enabled = 1",
            (payload.homestay_id,),
        ).fetchone()
        if stay is None:
            raise HTTPException(status_code=404, detail="Homestay was not found.")

        rows = _inventory_rows(
            connection,
            payload.homestay_id,
            payload.check_in,
            payload.check_out,
        )
        required_nights = (payload.check_out - payload.check_in).days
        inventory_by_date = {row["inventory_date"]: row for row in rows}
        missing_dates = [
            (payload.check_in + timedelta(days=offset)).isoformat()
            for offset in range(required_nights)
            if (payload.check_in + timedelta(days=offset)).isoformat() not in inventory_by_date
        ]
        if missing_dates:
            raise HTTPException(
                status_code=409,
                detail="Mock inventory is not provided for every selected night.",
            )
        if any(inventory_by_date[day]["available_units"] < 1 for day in inventory_by_date):
            raise HTTPException(
                status_code=409,
                detail="The mock inventory shows no units for one or more selected nights.",
            )

        request_id = uuid4()
        created_at = datetime.now(timezone.utc).isoformat()
        connection.execute(
            "INSERT INTO booking_requests "
            "(id, client_request_id, homestay_id, check_in, check_out, guest_count, status, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, 'demo_submitted', ?)",
            (
                str(request_id),
                str(payload.client_request_id),
                payload.homestay_id,
                payload.check_in.isoformat(),
                payload.check_out.isoformat(),
                payload.guest_count,
                created_at,
            ),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise

    return {
        "request_id": request_id,
        "client_request_id": payload.client_request_id,
        "homestay_id": payload.homestay_id,
        "check_in": payload.check_in,
        "check_out": payload.check_out,
        "guest_count": payload.guest_count,
        "status": "demo_submitted",
        "inventory_mode": "demo_mock",
        "non_binding": True,
        "created_at": created_at,
    }


def _receipt_from_row(row: sqlite3.Row, client_request_id: UUID) -> dict[str, Any]:
    return {
        "request_id": UUID(row["id"]),
        "client_request_id": client_request_id,
        "homestay_id": row["homestay_id"],
        "check_in": row["check_in"],
        "check_out": row["check_out"],
        "guest_count": row["guest_count"],
        "status": row["status"],
        "inventory_mode": "demo_mock",
        "non_binding": True,
        "created_at": row["created_at"],
    }
