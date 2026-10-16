from contextlib import AbstractContextManager
import sqlite3
from pathlib import Path
from threading import Thread

import pytest

from app.db.database import SCHEMA_PATH, connect_database, initialize_database


def test_schema_v1_migrates_additively_to_latest(tmp_path: Path) -> None:
    database = tmp_path / "legacy.db"
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        connection.execute(
            "INSERT INTO destinations "
            "(id, name, district, region, source_label, reviewer, reviewed_at) "
            "VALUES (1, 'Existing place', 'District', 'Uttarakhand', "
            "'Reviewed source', 'curator', '2026-10-12')"
        )
        connection.execute(
            "INSERT INTO homestays "
            "(id, destination_id, name, source_label, reviewer, reviewed_at) "
            "VALUES (1, 1, 'Existing stay', 'Reviewed source', 'curator', '2026-10-12')"
        )
        connection.execute("PRAGMA user_version = 1")

    initialize_database(database)
    initialize_database(database)

    with sqlite3.connect(database) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 5
        assert connection.execute("SELECT name FROM destinations WHERE id = 1").fetchone() == (
            "Existing place",
        )
        assert connection.execute("SELECT name FROM homestays WHERE id = 1").fetchone() == (
            "Existing stay",
        )
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        assert {
            "homestay_inventory",
            "booking_requests",
            "weather_locations",
            "weather_climatology",
            "weather_forecasts",
            "data_source_refreshes",
            "live_tourist_metrics",
        } <= tables
        climatology_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(weather_climatology)")
        }
        assert {"mean_cloud_cover_pct", "mean_wind_speed_kmh", "hci_score"} <= climatology_columns
        forecast_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(weather_forecasts)")
        }
        assert {"cloud_cover_pct", "wind_speed_kmh", "hci_score"} <= forecast_columns


def test_fresh_database_applies_all_migrations(tmp_path: Path) -> None:
    database = tmp_path / "fresh.db"

    initialize_database(database)

    with connect_database(database) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 5
        with pytest.raises(sqlite3.IntegrityError):
            with connection:
                connection.execute(
                    "INSERT INTO homestay_inventory "
                    "(id, homestay_id, inventory_date, total_units, available_units, "
                    "inventory_mode, source_label, reviewer, reviewed_at) "
                    "VALUES (1, 999, '2026-11-07', 2, 1, 'demo_mock', "
                    "'DEMO MOCK INVENTORY - NOT REAL', 'fixture', '2026-10-12')"
                )
        assert connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'index' "
            "AND name = 'idx_homestay_inventory_date'"
        ).fetchone() is not None
        assert connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'index' "
            "AND name = 'idx_live_tourist_metrics_destination_timestamp'"
        ).fetchone() is not None


def test_connection_can_be_closed_by_a_different_worker_thread(tmp_path: Path) -> None:
    database = tmp_path / "catalogue.db"
    initialize_database(database)
    manager: AbstractContextManager[sqlite3.Connection] = connect_database(database)
    connections: list[sqlite3.Connection] = []
    errors: list[BaseException] = []

    def enter_context() -> None:
        try:
            connections.append(manager.__enter__())
        except BaseException as error:
            errors.append(error)

    def exit_context() -> None:
        try:
            manager.__exit__(None, None, None)
        except BaseException as error:
            errors.append(error)

    enter_thread = Thread(target=enter_context)
    enter_thread.start()
    enter_thread.join()
    exit_thread = Thread(target=exit_context)
    exit_thread.start()
    exit_thread.join()

    assert errors == []
    assert len(connections) == 1
