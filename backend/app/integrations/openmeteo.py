from __future__ import annotations

import csv
import logging
import math
import sqlite3
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Protocol
from zoneinfo import ZoneInfo

from requests.exceptions import RequestException


ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_SOURCE_URL = "https://open-meteo.com/en/docs/historical-weather-api"
FORECAST_SOURCE_URL = "https://open-meteo.com/en/docs"
FORECAST_TTL = timedelta(hours=3)
ARCHIVE_REFRESH_INTERVAL = timedelta(days=30)
ARCHIVE_CACHE_TTL_SECONDS = 30 * 24 * 60 * 60
FORECAST_CACHE_TTL_SECONDS = int(FORECAST_TTL.total_seconds())
DAILY_VARIABLES = (
    "temperature_2m_max",
    "temperature_2m_min",
    "temperature_2m_mean",
    "precipitation_sum",
)
logger = logging.getLogger("pahadpath.openmeteo")


class DailyWeather(Protocol):
    def Time(self) -> int: ...

    def Variables(self, index: int) -> Any: ...


class WeatherResponse(Protocol):
    def Daily(self) -> DailyWeather: ...


class OpenMeteoClient(Protocol):
    def weather_api(
        self,
        url: str,
        params: dict[str, Any],
        timeout: int,
    ) -> list[WeatherResponse]: ...


def create_client(cache_path: str | Path, *, expire_after: int) -> OpenMeteoClient:
    try:
        import openmeteo_requests
        import requests_cache
        from retry_requests import retry
    except ImportError as error:
        raise RuntimeError(
            "Open-Meteo refresh dependencies are missing; install backend/requirements.txt."
        ) from error

    cache_file = Path(cache_path)
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_session = requests_cache.CachedSession(
        str(cache_file),
        expire_after=expire_after,
        headers={
            "User-Agent": "PahadPath/0.1 weather-data refresh (offline-first trip planner)"
        },
    )
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    return openmeteo_requests.Client(session=retry_session)


def _weather_tendency(temp_max: float, temp_min: float, precipitation_mm: float) -> int:
    rain_friction = min(60.0, max(0.0, precipitation_mm) * 2.0)
    temperature_friction = min(
        25.0,
        max(0.0, 8.0 - temp_min) * 1.25 + max(0.0, temp_max - 32.0) * 1.25,
    )
    return max(0, min(100, round(100.0 - rain_friction - temperature_friction)))


def _values(response: WeatherResponse) -> list[list[float]]:
    daily = response.Daily()
    if daily is None:
        raise ValueError("Open-Meteo response did not include daily weather data.")
    series: list[list[float]] = []
    for index in range(len(DAILY_VARIABLES)):
        variable = daily.Variables(index)
        if variable is None:
            raise ValueError("Open-Meteo response is missing a requested daily variable.")
        values = variable.ValuesAsNumpy()
        series.append([float(value) for value in values])
    if len({len(values) for values in series}) != 1:
        raise ValueError("Open-Meteo daily weather series have inconsistent lengths.")
    return series


def _daily_rows(
    response: WeatherResponse,
    *,
    first_date: date,
    expected_days: int,
) -> list[dict[str, float | str]]:
    series = _values(response)
    rows: list[dict[str, float | str]] = []
    for index in range(min(expected_days, len(series[0]))):
        values = [column[index] for column in series]
        if not all(math.isfinite(value) and abs(value) < 1e10 for value in values):
            continue
        temp_max, temp_min, temp_mean, precipitation = values
        if precipitation < 0:
            continue
        target_date = first_date + timedelta(days=index)
        rows.append(
            {
                "date": target_date.isoformat(),
                "temp_max": temp_max,
                "temp_min": temp_min,
                "temp_mean": temp_mean,
                "precipitation_mm": precipitation,
                "weather_visit_tendency": _weather_tendency(
                    temp_max,
                    temp_min,
                    precipitation,
                ),
            }
        )
    if not rows:
        raise ValueError("Open-Meteo response contained no usable daily weather values.")
    return rows


def _params(location: sqlite3.Row, *, timezone_name: str) -> dict[str, Any]:
    params: dict[str, Any] = {
        "latitude": location["latitude"],
        "longitude": location["longitude"],
        "daily": list(DAILY_VARIABLES),
        "timezone": timezone_name,
        "temperature_unit": "celsius",
        "precipitation_unit": "mm",
    }
    if location["elevation_m"] is not None:
        params["elevation"] = location["elevation_m"]
    return params


def _write_raw_csv(
    raw_directory: Path,
    location: sqlite3.Row,
    source: str,
    rows: list[dict[str, float | str]],
) -> None:
    raw_directory.mkdir(parents=True, exist_ok=True)
    file_path = raw_directory / f"{source}_{location['destination_id']}.csv"
    fields = (
        "date",
        "temp_max",
        "temp_min",
        "temp_mean",
        "precipitation_mm",
        "weather_visit_tendency",
    )
    with file_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _upsert_climatology(
    connection: sqlite3.Connection,
    destination_id: int,
    rows: list[dict[str, float | str]],
    retrieved_at: str,
) -> int:
    grouped: dict[int, list[dict[str, float | str]]] = defaultdict(list)
    for row in rows:
        month = date.fromisoformat(str(row["date"])).month
        grouped[month].append(row)

    for month, month_rows in grouped.items():
        count = len(month_rows)
        means = {
            field: sum(float(row[field]) for row in month_rows) / count
            for field in ("temp_max", "temp_min", "temp_mean", "precipitation_mm")
        }
        tendency = round(
            sum(int(row["weather_visit_tendency"]) for row in month_rows) / count
        )
        connection.execute(
            """
            INSERT INTO weather_climatology (
                destination_id, calendar_month, mean_temp_max, mean_temp_min, mean_temp,
                mean_precipitation_mm, weather_visit_tendency, sample_count,
                retrieved_at, source_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(destination_id, calendar_month) DO UPDATE SET
                mean_temp_max=excluded.mean_temp_max,
                mean_temp_min=excluded.mean_temp_min,
                mean_temp=excluded.mean_temp,
                mean_precipitation_mm=excluded.mean_precipitation_mm,
                weather_visit_tendency=excluded.weather_visit_tendency,
                sample_count=excluded.sample_count,
                retrieved_at=excluded.retrieved_at,
                source_url=excluded.source_url
            """,
            (
                destination_id,
                month,
                means["temp_max"],
                means["temp_min"],
                means["temp_mean"],
                means["precipitation_mm"],
                tendency,
                count,
                retrieved_at,
                ARCHIVE_SOURCE_URL,
            ),
        )
    return len(grouped)


def _upsert_forecast(
    connection: sqlite3.Connection,
    destination_id: int,
    rows: list[dict[str, float | str]],
    retrieved_at: str,
    expires_at: str,
) -> int:
    for row in rows:
        connection.execute(
            """
            INSERT INTO weather_forecasts (
                destination_id, forecast_date, temp_max, temp_min, temp_mean,
                precipitation_mm, weather_visit_tendency, retrieved_at, expires_at, source_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(destination_id, forecast_date) DO UPDATE SET
                temp_max=excluded.temp_max,
                temp_min=excluded.temp_min,
                temp_mean=excluded.temp_mean,
                precipitation_mm=excluded.precipitation_mm,
                weather_visit_tendency=excluded.weather_visit_tendency,
                retrieved_at=excluded.retrieved_at,
                expires_at=excluded.expires_at,
                source_url=excluded.source_url
            """,
            (
                destination_id,
                row["date"],
                row["temp_max"],
                row["temp_min"],
                row["temp_mean"],
                row["precipitation_mm"],
                row["weather_visit_tendency"],
                retrieved_at,
                expires_at,
                FORECAST_SOURCE_URL,
            ),
        )
    return len(rows)


def _record_source_status(
    connection: sqlite3.Connection,
    *,
    source_key: str,
    status: str,
    retrieved_at: str,
    successful: bool,
    records_updated: int,
    details: str,
) -> None:
    connection.execute(
        """
        INSERT INTO data_source_refreshes (
            source_key, status, retrieved_at, last_success_at, records_updated, details
        ) VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(source_key) DO UPDATE SET
            status=excluded.status,
            retrieved_at=excluded.retrieved_at,
            last_success_at=CASE
                WHEN excluded.last_success_at IS NOT NULL THEN excluded.last_success_at
                ELSE data_source_refreshes.last_success_at
            END,
            records_updated=excluded.records_updated,
            details=excluded.details
        """,
        (
            source_key,
            status,
            retrieved_at,
            retrieved_at if successful else None,
            records_updated,
            details,
        ),
    )


def _refresh_source(
    connection: sqlite3.Connection,
    locations: list[sqlite3.Row],
    *,
    source_key: str,
    url: str,
    client: OpenMeteoClient,
    start_date: date,
    expected_days: int,
    retrieved_at: str,
    raw_directory: Path,
    forecast: bool,
    now: datetime,
) -> dict[str, Any]:
    successes = 0
    failures: list[str] = []
    updated = 0
    expires_at = (datetime.fromisoformat(retrieved_at) + FORECAST_TTL).isoformat()
    with connection:
        for location in locations:
            try:
                parameters = _params(location, timezone_name=location["timezone"])
                location_start_date = (
                    now.astimezone(ZoneInfo(location["timezone"])).date()
                    if forecast
                    else start_date
                )
                if forecast:
                    parameters["forecast_days"] = expected_days
                else:
                    parameters["start_date"] = start_date.isoformat()
                    parameters["end_date"] = (
                        start_date + timedelta(days=expected_days - 1)
                    ).isoformat()
                responses = client.weather_api(url, params=parameters, timeout=30)
                if not responses:
                    raise ValueError("Open-Meteo returned no locations.")
                rows = _daily_rows(
                    responses[0],
                    first_date=location_start_date,
                    expected_days=expected_days,
                )
                _write_raw_csv(raw_directory, location, source_key, rows)
                destination_id = int(location["destination_id"])
                if forecast:
                    updated += _upsert_forecast(
                        connection,
                        destination_id,
                        rows,
                        retrieved_at,
                        expires_at,
                    )
                else:
                    updated += _upsert_climatology(
                        connection,
                        destination_id,
                        rows,
                        retrieved_at,
                    )
                successes += 1
            except (OSError, RequestException, TypeError, ValueError) as error:
                failures.append(str(location["name"]))
                logger.warning(
                    "Open-Meteo %s refresh failed for destination=%s error=%s",
                    source_key,
                    location["destination_id"],
                    type(error).__name__,
                )

        if not locations:
            status = "missing"
            details = "No enabled weather locations are configured."
        elif failures and successes:
            status = "stale"
            details = f"Refresh failed for {len(failures)} of {len(locations)} destinations."
        elif failures:
            table = "weather_forecasts" if forecast else "weather_climatology"
            existing = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            status = "stale" if existing else "missing"
            details = f"Refresh failed for all {len(failures)} configured destinations."
        else:
            status = "ok"
            details = f"Updated {successes} of {len(locations)} destinations."
        _record_source_status(
            connection,
            source_key=source_key,
            status=status,
            retrieved_at=retrieved_at,
            successful=successes > 0,
            records_updated=updated,
            details=details,
        )

    return {
        "source": source_key,
        "status": status,
        "retrieved_at": retrieved_at,
        "destinations_updated": successes,
        "destinations_failed": failures,
        "records_updated": updated,
        "details": details,
    }


def refresh_weather(
    connection: sqlite3.Connection,
    *,
    now: datetime | None = None,
    client_factory: Any = create_client,
    raw_directory: str | Path,
) -> dict[str, Any]:
    locations = connection.execute(
        """
        SELECT wl.destination_id, wl.latitude, wl.longitude, wl.elevation_m, wl.timezone, d.name
        FROM weather_locations AS wl
        JOIN destinations AS d ON d.id = wl.destination_id
        WHERE wl.enabled = 1 AND d.enabled = 1
        ORDER BY wl.destination_id
        """
    ).fetchall()
    utc_now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    retrieved_at = utc_now.isoformat(timespec="seconds")
    raw_path = Path(raw_directory)

    archive_end = utc_now.date() - timedelta(days=6)
    try:
        archive_start = archive_end.replace(year=archive_end.year - 5) + timedelta(days=1)
    except ValueError:
        archive_start = archive_end.replace(
            year=archive_end.year - 5,
            day=28,
        ) + timedelta(days=1)
    archive_days = (archive_end - archive_start).days + 1
    forecast_days = 16
    forecast_client = client_factory(
        raw_path / "http-cache" / "openmeteo-forecast",
        expire_after=FORECAST_CACHE_TTL_SECONDS,
    )

    archive_state = connection.execute(
        "SELECT status, retrieved_at, last_success_at, records_updated, details "
        "FROM data_source_refreshes WHERE source_key = 'open_meteo_archive'"
    ).fetchone()
    if (
        archive_state is not None
        and archive_state["status"] == "ok"
        and archive_state["last_success_at"] is not None
        and utc_now - datetime.fromisoformat(archive_state["last_success_at"]).astimezone(
            timezone.utc
        ) < ARCHIVE_REFRESH_INTERVAL
    ):
        archive_report: dict[str, Any] = {
            "source": "open_meteo_archive",
            "status": "ok",
            "retrieved_at": archive_state["retrieved_at"],
            "destinations_updated": 0,
            "destinations_failed": [],
            "records_updated": 0,
            "details": "Five-year historical climatology is refreshed every 30 days.",
        }
    else:
        archive_client = client_factory(
            raw_path / "http-cache" / "openmeteo-archive",
            expire_after=ARCHIVE_CACHE_TTL_SECONDS,
        )
        archive_report = _refresh_source(
            connection,
            locations,
            source_key="open_meteo_archive",
            url=ARCHIVE_URL,
            client=archive_client,
            start_date=archive_start,
            expected_days=archive_days,
            retrieved_at=retrieved_at,
            raw_directory=raw_path / "archive",
            forecast=False,
            now=utc_now,
        )
    forecast_report = _refresh_source(
        connection,
        locations,
        source_key="open_meteo_forecast",
        url=FORECAST_URL,
        client=forecast_client,
        start_date=utc_now.date(),
        expected_days=forecast_days,
        retrieved_at=retrieved_at,
        raw_directory=raw_path / "forecast",
        forecast=True,
        now=utc_now,
    )
    report = [
        archive_report,
        forecast_report,
    ]
    return {"retrieved_at": retrieved_at, "sources": report}
