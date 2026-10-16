from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from app.db.database import connect_database, initialize_database
from app.integrations.openmeteo import refresh_weather
from app.repositories.weather_repository import get_weather_visit_tendency


class _Variable:
    def __init__(self, values: list[float]) -> None:
        self._values = values

    def ValuesAsNumpy(self) -> list[float]:
        return self._values


class _Daily:
    def __init__(self, series: list[list[float]]) -> None:
        self._series = series

    def Variables(self, index: int) -> _Variable:
        return _Variable(self._series[index])


class _Response:
    def __init__(self, series: list[list[float]]) -> None:
        self._daily = _Daily(series)

    def Daily(self) -> _Daily:
        return self._daily


class _Client:
    def __init__(self, series: list[list[float]]) -> None:
        self.series = series
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def weather_api(
        self,
        url: str,
        params: dict[str, Any],
        timeout: int = 30,
    ) -> list[_Response]:
        self.calls.append((url, params))
        return [_Response(self.series)]


def _create_weather_database(database_path: Path) -> None:
    initialize_database(database_path)
    with connect_database(database_path) as connection:
        with connection:
            connection.execute(
                """
                INSERT INTO destinations (
                    id, name, district, region, source_label, reviewer, reviewed_at
                ) VALUES (1, 'Test Place', 'District', 'Uttarakhand', 'Test source',
                          'reviewer', '2026-10-13')
                """
            )
            connection.execute(
                """
                INSERT INTO weather_locations (
                    id, destination_id, latitude, longitude, timezone, source_label,
                    source_url, reviewer, reviewed_at
                ) VALUES (1, 1, 30.1, 80.2, 'Asia/Kolkata', 'Test coordinates',
                          'https://example.test/place', 'reviewer', '2026-10-13')
                """
            )


def _series(
    *,
    maximums: list[float] | None = None,
    minimums: list[float] | None = None,
    means: list[float] | None = None,
    rain: list[float] | None = None,
    cloud: list[float] | None = None,
    wind: list[float] | None = None,
) -> list[list[float]]:
    maxs = maximums if maximums is not None else [20.0, 30.0, 10.0]
    n = len(maxs)

    def pick(values: list[float] | None, fallback: list[float]) -> list[float]:
        if values is not None:
            return values
        return (fallback * ((n // len(fallback)) + 1))[:n]

    return [
        maxs,
        pick(minimums, [10.0, 15.0, 2.0]),
        pick(means, [15.0, 22.0, 6.0]),
        pick(rain, [0.0, 10.0, 2.0]),
        pick(cloud, [40.0, 60.0, 30.0]),
        pick(wind, [8.0, 20.0, 12.0]),
    ]


def test_refresh_persists_five_year_monthly_climate_and_sixteen_day_forecast(
    tmp_path: Path,
) -> None:
    database = tmp_path / "catalogue.db"
    _create_weather_database(database)
    archive_client = _Client(_series())
    forecast_client = _Client(_series(maximums=[20.0, 20.0], minimums=[10.0, 10.0],
                                      means=[15.0, 15.0], rain=[0.0, 0.0]))
    factory_calls: list[tuple[str, int]] = []

    def client_factory(path: str | Path, *, expire_after: int) -> _Client:
        factory_calls.append((str(path), expire_after))
        return archive_client if "archive" in str(path) else forecast_client

    with connect_database(database) as connection:
        report = refresh_weather(
            connection,
            now=datetime(2026, 10, 13, 12, tzinfo=timezone.utc),
            client_factory=client_factory,
            raw_directory=tmp_path / "raw",
        )

    assert [source["status"] for source in report["sources"]] == ["ok", "ok"]
    assert len(factory_calls) == 2
    archive_url, archive_params = archive_client.calls[0]
    assert archive_url == "https://archive-api.open-meteo.com/v1/archive"
    assert archive_params["start_date"] == "2021-10-08"
    assert archive_params["end_date"] == "2026-10-07"
    assert archive_params["daily"] == [
        "temperature_2m_max",
        "temperature_2m_min",
        "temperature_2m_mean",
        "precipitation_sum",
        "cloudcover_mean",
        "windspeed_10m_max",
    ]
    assert forecast_client.calls[0][0] == "https://api.open-meteo.com/v1/forecast"
    assert forecast_client.calls[0][1]["forecast_days"] == 16

    with connect_database(database) as connection:
        climate = connection.execute(
            "SELECT * FROM weather_climatology WHERE destination_id = 1 AND calendar_month = 10"
        ).fetchone()
        forecast = connection.execute(
            "SELECT * FROM weather_forecasts WHERE destination_id = 1 AND forecast_date = '2026-10-13'"
        ).fetchone()
        tendency = get_weather_visit_tendency(
            connection,
            destination_id=1,
            target_date=date(2026, 10, 13),
            now=datetime(2026, 10, 13, 12, tzinfo=timezone.utc),
        )

    assert climate["sample_count"] == 3
    assert climate["mean_temp_max"] == pytest.approx(20.0)
    assert climate["mean_precipitation_mm"] == pytest.approx(4.0)
    assert climate["hci_score"] is not None
    assert forecast["weather_visit_tendency"] == 100
    # Holiday Climate Index: T(15C)=10, A(40%)=7, Rd(0mm)=10, W(8km/h)=10 -> 94.
    assert forecast["hci_score"] == 94
    assert tendency is not None and tendency["value"] == 94
    assert "forecast" in str(tendency["note"]).lower()
    assert (tmp_path / "raw" / "archive" / "open_meteo_archive_1.csv").is_file()
    assert (tmp_path / "raw" / "forecast" / "open_meteo_forecast_1.csv").is_file()


def test_refresh_is_idempotent_and_skips_recent_archive(tmp_path: Path) -> None:
    database = tmp_path / "catalogue.db"
    _create_weather_database(database)
    archive_client = _Client(_series())
    forecast_client = _Client(_series(maximums=[18.0], minimums=[9.0], means=[13.0], rain=[2.0]))
    clients = iter([archive_client, forecast_client])
    now = datetime(2026, 10, 13, 12, tzinfo=timezone.utc)

    def client_factory(path: str | Path, *, expire_after: int) -> _Client:
        return next(clients)

    with connect_database(database) as connection:
        refresh_weather(
            connection,
            now=now,
            client_factory=client_factory,
            raw_directory=tmp_path / "raw",
        )
    forecast_client_2 = _Client(_series(maximums=[19.0], minimums=[9.0], means=[14.0], rain=[1.0]))

    def forecast_only_factory(path: str | Path, *, expire_after: int) -> _Client:
        return forecast_client_2

    with connect_database(database) as connection:
        report = refresh_weather(
            connection,
            now=now.replace(hour=13),
            client_factory=forecast_only_factory,
            raw_directory=tmp_path / "raw",
        )
        climate_count = connection.execute(
            "SELECT count(*) FROM weather_climatology"
        ).fetchone()[0]

    assert report["sources"][0]["records_updated"] == 0
    assert report["sources"][1]["status"] == "ok"
    assert climate_count == 1
    assert len(forecast_client_2.calls) == 1


def test_missing_refresh_uses_monthly_climate_then_neutral_when_absent(
    tmp_path: Path,
) -> None:
    database = tmp_path / "catalogue.db"
    _create_weather_database(database)

    with connect_database(database) as connection:
        assert get_weather_visit_tendency(
            connection,
            destination_id=1,
            target_date=date(2026, 10, 20),
        ) is None
        connection.execute(
            """
            INSERT INTO weather_climatology (
                destination_id, calendar_month, mean_temp_max, mean_temp_min,
                mean_temp, mean_precipitation_mm, weather_visit_tendency,
                sample_count, retrieved_at, source_url
            ) VALUES (1, 10, 20, 10, 15, 2, 72, 155, '2026-10-13T12:00:00+00:00',
                      'https://open-meteo.com/en/docs/historical-weather-api')
            """
        )
        fallback = get_weather_visit_tendency(
            connection,
            destination_id=1,
            target_date=date(2026, 10, 20),
        )

    assert fallback is not None and fallback["value"] == 72
    assert "climatology" in str(fallback["note"]).lower()


def test_invalid_openmeteo_daily_values_are_not_saved(tmp_path: Path) -> None:
    database = tmp_path / "catalogue.db"
    _create_weather_database(database)
    broken_client = _Client(
        [[float("nan")], [float("nan")], [float("nan")], [float("nan")],
         [float("nan")], [float("nan")]]
    )
    forecast_client = _Client(_series(maximums=[20.0], minimums=[10.0],
                                      means=[15.0], rain=[0.0]))

    def client_factory(path: str | Path, *, expire_after: int) -> _Client:
        return broken_client if "archive" in str(path) else forecast_client

    with connect_database(database) as connection:
        report = refresh_weather(
            connection,
            now=datetime(2026, 10, 13, 12, tzinfo=timezone.utc),
            client_factory=client_factory,
            raw_directory=tmp_path / "raw",
        )
        count = connection.execute("SELECT count(*) FROM weather_climatology").fetchone()[0]

    assert report["sources"][0]["status"] == "missing"
    assert report["sources"][1]["status"] == "ok"
    assert count == 0


def test_weather_location_seed_is_applied_for_active_places(tmp_path: Path) -> None:
    project_data = Path(__file__).resolve().parents[2] / "data"
    from app.db.seed import seed_database

    database = tmp_path / "catalogue.db"
    seed_database(database, project_data)
    with connect_database(database) as connection:
        locations = connection.execute(
            """
            SELECT d.name, wl.latitude, wl.longitude
            FROM weather_locations AS wl
            JOIN destinations AS d ON d.id = wl.destination_id
            WHERE d.enabled = 1 AND wl.enabled = 1
            ORDER BY d.id
            """
        ).fetchall()

    assert len(locations) == 5
    assert {row["name"] for row in locations} == {
        "Almora", "Munsiyari", "Kausani", "Binsar", "Mussoorie"
    }
    assert all(-90 <= row["latitude"] <= 90 and -180 <= row["longitude"] <= 180 for row in locations)
