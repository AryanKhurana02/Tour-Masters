import sqlite3
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends

from app.api.dependencies import get_database

router = APIRouter(prefix="/api", tags=["health"])
FORECAST_FRESHNESS_HOURS = 4
ARCHIVE_FRESHNESS_DAYS = 45


@router.get("/health")
def get_health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/data-sources")
def get_data_sources(
    connection: sqlite3.Connection = Depends(get_database),
) -> dict[str, list[dict[str, str | int | None]]]:
    freshness = {
        "open_meteo_forecast": timedelta(hours=FORECAST_FRESHNESS_HOURS),
        "open_meteo_archive": timedelta(days=ARCHIVE_FRESHNESS_DAYS),
    }
    rows = {
        row["source_key"]: row
        for row in connection.execute(
            "SELECT source_key, status, retrieved_at, last_success_at, records_updated, details "
            "FROM data_source_refreshes"
        ).fetchall()
    }
    now = datetime.now(timezone.utc)
    sources: list[dict[str, str | int | None]] = []
    for source_key, max_age in freshness.items():
        row = rows.get(source_key)
        if row is None:
            sources.append({
                "source": source_key,
                "status": "missing",
                "retrieved_at": None,
                "last_success_at": None,
                "records_updated": 0,
                "details": "No refresh has been completed.",
            })
            continue
        last_success = row["last_success_at"]
        status = str(row["status"])
        if last_success:
            timestamp = datetime.fromisoformat(last_success)
            if now - timestamp.astimezone(timezone.utc) > max_age and status == "ok":
                status = "stale"
        sources.append({
            "source": source_key,
            "status": status,
            "retrieved_at": row["retrieved_at"],
            "last_success_at": last_success,
            "records_updated": int(row["records_updated"]),
            "details": row["details"],
        })
    return {"sources": sources}
