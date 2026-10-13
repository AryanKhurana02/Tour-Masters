from __future__ import annotations

import sqlite3
from datetime import date
from typing import Any


def _split_values(value: str) -> list[str]:
    return [part.strip() for part in value.split(";") if part.strip()]


def destination_from_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "district": row["district"],
        "region": row["region"],
        "description": row["description"],
        "tags": _split_values(row["tags"]),
        "best_months": [int(month) for month in _split_values(row["best_months"])],
        "popularity_score": row["popularity_score"],
        "source_label": row["source_label"],
        "source_url": row["source_url"],
        "reviewer": row["reviewer"],
        "reviewed_at": row["reviewed_at"],
    }


def homestay_from_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "destination_id": row["destination_id"],
        "name": row["name"],
        "village": row["village"],
        "nightly_min": row["nightly_min"],
        "nightly_max": row["nightly_max"],
        "currency": row["currency"],
        "public_contact": row["public_contact"] if row["publish_contact"] else None,
        "booking_url": row["booking_url"] if row["publish_contact"] else None,
        "amenities": _split_values(row["amenities"]),
        "source_label": row["source_label"],
        "source_url": row["source_url"],
        "reviewer": row["reviewer"],
        "reviewed_at": row["reviewed_at"],
    }


def list_destinations(
    connection: sqlite3.Connection,
    *,
    region: str | None = None,
    tag: str | None = None,
) -> list[dict[str, Any]]:
    rows = connection.execute(
        "SELECT * FROM destinations WHERE enabled = 1 "
        "AND (? IS NULL OR region = ? COLLATE NOCASE) ORDER BY name COLLATE NOCASE, id",
        (region, region),
    ).fetchall()
    destinations = [destination_from_row(row) for row in rows]
    if tag is not None:
        normalized_tag = tag.casefold()
        destinations = [
            item for item in destinations
            if normalized_tag in {value.casefold() for value in item["tags"]}
        ]
    return destinations


def get_destination(
    connection: sqlite3.Connection,
    destination_id: int,
) -> dict[str, Any] | None:
    row = connection.execute(
        "SELECT * FROM destinations WHERE id = ? AND enabled = 1",
        (destination_id,),
    ).fetchone()
    return destination_from_row(row) if row else None


def list_alternatives(
    connection: sqlite3.Connection,
    destination_id: int,
) -> list[dict[str, Any]]:
    rows = connection.execute(
        "SELECT d.*, l.match_tags, l.travel_fit, l.source_label AS link_source_label, "
        "l.source_url AS link_source_url, l.reviewer AS link_reviewer, "
        "l.reviewed_at AS link_reviewed_at "
        "FROM alternative_links AS l "
        "JOIN destinations AS d ON d.id = l.alternative_destination_id "
        "WHERE l.source_destination_id = ? AND l.enabled = 1 AND d.enabled = 1 "
        "ORDER BY d.name COLLATE NOCASE, d.id",
        (destination_id,),
    ).fetchall()
    return [
        {
            "destination": destination_from_row(row),
            "match_tags": _split_values(row["match_tags"]),
            "travel_fit": row["travel_fit"],
            "source_label": row["link_source_label"],
            "source_url": row["link_source_url"],
            "reviewer": row["link_reviewer"],
            "reviewed_at": row["link_reviewed_at"],
        }
        for row in rows
    ]


def list_homestays(
    connection: sqlite3.Connection,
    destination_id: int,
) -> list[dict[str, Any]]:
    rows = connection.execute(
        "SELECT h.* FROM homestays AS h JOIN destinations AS d "
        "ON d.id = h.destination_id "
        "WHERE h.destination_id = ? AND h.enabled = 1 AND d.enabled = 1 "
        "ORDER BY h.name COLLATE NOCASE, h.id",
        (destination_id,),
    ).fetchall()
    return [homestay_from_row(row) for row in rows]


def get_recommendation_candidates(
    connection: sqlite3.Connection,
    *,
    region: str,
    source_destination_id: int | None,
) -> list[dict[str, Any]]:
    if source_destination_id is None:
        rows = connection.execute(
            "SELECT d.*, NULL AS link_tags, NULL AS travel_fit "
            "FROM destinations AS d WHERE d.enabled = 1 AND d.region = ? COLLATE NOCASE "
            "ORDER BY d.id",
            (region,),
        ).fetchall()
    else:
        rows = connection.execute(
            "SELECT d.*, l.match_tags AS link_tags, l.travel_fit "
            "FROM alternative_links AS l "
            "JOIN destinations AS d ON d.id = l.alternative_destination_id "
            "WHERE l.source_destination_id = ? AND l.enabled = 1 AND d.enabled = 1 "
            "AND d.region = ? COLLATE NOCASE "
            "ORDER BY d.id",
            (source_destination_id, region),
        ).fetchall()
    return [
        {
            **destination_from_row(row),
            "link_tags": _split_values(row["link_tags"] or ""),
            "travel_fit": row["travel_fit"],
        }
        for row in rows
    ]


def get_event_pressure(
    connection: sqlite3.Connection,
    *,
    region: str,
    destination_id: int,
    target_date: date,
) -> int | None:
    reviewed = connection.execute(
        "SELECT 1 FROM event_calendar_reviews "
        "WHERE enabled = 1 AND region = ? COLLATE NOCASE "
        "AND starts_on <= ? AND ends_on >= ? LIMIT 1",
        (region, target_date.isoformat(), target_date.isoformat()),
    ).fetchone()
    if not reviewed:
        return None

    event = connection.execute(
        "SELECT MAX(pressure) FROM local_events "
        "WHERE enabled = 1 AND region = ? COLLATE NOCASE "
        "AND starts_on <= ? AND ends_on >= ? "
        "AND (destination_id IS NULL OR destination_id = ?)",
        (region, target_date.isoformat(), target_date.isoformat(), destination_id),
    ).fetchone()[0]
    if event is not None:
        return int(event)
    return 0


def get_destination_for_itinerary(
    connection: sqlite3.Connection,
    destination_id: int,
) -> dict[str, Any] | None:
    return get_destination(connection, destination_id)


def get_homestay_for_itinerary(
    connection: sqlite3.Connection,
    homestay_id: int,
) -> dict[str, Any] | None:
    row = connection.execute(
        "SELECT h.* FROM homestays AS h JOIN destinations AS d "
        "ON d.id = h.destination_id "
        "WHERE h.id = ? AND h.enabled = 1 AND d.enabled = 1",
        (homestay_id,),
    ).fetchone()
    return homestay_from_row(row) if row else None
