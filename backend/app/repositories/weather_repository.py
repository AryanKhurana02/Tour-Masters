from __future__ import annotations

import sqlite3
from datetime import date, datetime, timezone


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
        SELECT weather_visit_tendency, retrieved_at
        FROM weather_forecasts
        WHERE destination_id = ? AND forecast_date = ? AND expires_at > ?
        """,
        (destination_id, target_date.isoformat(), current_time_text),
    ).fetchone()
    if forecast is not None:
        return {
            "value": int(forecast["weather_visit_tendency"]),
            "note": (
                f"Open-Meteo forecast retrieved at {forecast['retrieved_at']} UTC; "
                "weather affects this estimate but is not a live crowd count."
            ),
        }

    climatology = connection.execute(
        """
        SELECT weather_visit_tendency, retrieved_at
        FROM weather_climatology
        WHERE destination_id = ? AND calendar_month = ?
        """,
        (destination_id, target_date.month),
    ).fetchone()
    if climatology is not None:
        return {
            "value": int(climatology["weather_visit_tendency"]),
            "note": (
                f"Open-Meteo five-year historical weather climatology retrieved at "
                f"{climatology['retrieved_at']} UTC was used; no fresh forecast was available."
            ),
        }
    return None
