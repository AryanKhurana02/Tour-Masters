from __future__ import annotations

import sqlite3
from datetime import date, datetime, timezone


def _resolve_value(row: sqlite3.Row) -> tuple[int, bool]:
    """Prefer the HCI score; fall back to the legacy visit tendency."""
    if "hci_score" in row.keys() and row["hci_score"] is not None:
        return int(row["hci_score"]), True
    return int(row["weather_visit_tendency"]), False


def get_weather_visit_tendency(
    connection: sqlite3.Connection,
    *,
    destination_id: int,
    target_date: date,
    now: datetime | None = None,
) -> dict[str, int | str] | None:
    current_time = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    current_time_text = current_time.isoformat(timespec="seconds")
    forecast = connection.execute(
        """
        SELECT weather_visit_tendency, hci_score, retrieved_at
        FROM weather_forecasts
        WHERE destination_id = ? AND forecast_date = ? AND expires_at > ?
        """,
        (destination_id, target_date.isoformat(), current_time_text),
    ).fetchone()
    if forecast is not None:
        value, used_hci = _resolve_value(forecast)
        detail = (
            "Holiday Climate Index for this date is used"
            if used_hci
            else "weather affects this estimate but is not a live crowd count"
        )
        return {
            "value": value,
            "note": (
                f"Open-Meteo forecast retrieved at {forecast['retrieved_at']} UTC; "
                f"{detail}."
            ),
        }

    climatology = connection.execute(
        """
        SELECT weather_visit_tendency, hci_score, retrieved_at
        FROM weather_climatology
        WHERE destination_id = ? AND calendar_month = ?
        """,
        (destination_id, target_date.month),
    ).fetchone()
    if climatology is not None:
        value, used_hci = _resolve_value(climatology)
        detail = (
            "Holiday Climate Index for this month is used"
            if used_hci
            else "weather affects this estimate but is not a live crowd count"
        )
        return {
            "value": value,
            "note": (
                f"Open-Meteo five-year historical weather climatology retrieved at "
                f"{climatology['retrieved_at']} UTC was used; no fresh forecast was "
                f"available and the {detail}."
            ),
        }
    return None
