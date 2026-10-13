from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

import pytest

from app.db.database import connect_database
from app.db.seed import DATA_FILES, seed_database


def _write_csv(directory: Path, table: str, rows: list[dict[str, str]]) -> None:
    with (directory / f"{table}.csv").open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=DATA_FILES[table])
        writer.writeheader()
        writer.writerows(rows)


def _seed_files(directory: Path, *, destinations: list[dict[str, str]] | None = None) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for table in DATA_FILES:
        rows = (destinations or []) if table == "destinations" else []
        _write_csv(directory, table, rows)


def _destination(**overrides: str) -> dict[str, str]:
    row = {
        "id": "1",
        "name": "Verified Place",
        "district": "Verified District",
        "region": "Uttarakhand",
        "description": "",
        "tags": "forest;quiet",
        "best_months": "4;5",
        "popularity_score": "",
        "source_label": "Reviewed source",
        "source_url": "",
        "reviewer": "curator",
        "reviewed_at": "2026-10-12",
        "enabled": "1",
    }
    return {**row, **overrides}


def test_empty_templates_initialize_database_without_invented_data(tmp_path: Path) -> None:
    _seed_files(tmp_path / "data")
    counts = seed_database(tmp_path / "catalogue.db", tmp_path / "data")

    assert counts["destinations"] == 0
    with connect_database(tmp_path / "catalogue.db") as connection:
        assert connection.execute("SELECT count(*) FROM destinations").fetchone()[0] == 0


def test_seed_upsert_is_idempotent_and_preserves_unknown_values(tmp_path: Path) -> None:
    data = tmp_path / "data"
    data.mkdir()
    _seed_files(data, destinations=[_destination()])
    database = tmp_path / "catalogue.db"

    seed_database(database, data)
    seed_database(database, data)

    with connect_database(database) as connection:
        row = connection.execute("SELECT name, popularity_score FROM destinations").fetchone()
        assert tuple(row) == ("Verified Place", None)


def test_duplicate_csv_ids_are_rejected_before_inserts(tmp_path: Path) -> None:
    data = tmp_path / "data"
    data.mkdir()
    _seed_files(data, destinations=[_destination(), _destination()])

    with pytest.raises(ValueError, match="duplicate id"):
        seed_database(tmp_path / "catalogue.db", data)

    assert not (tmp_path / "catalogue.db").exists()


def test_missing_provenance_is_rejected(tmp_path: Path) -> None:
    data = tmp_path / "data"
    data.mkdir()
    _seed_files(data, destinations=[_destination(source_label="")])

    with pytest.raises(ValueError, match="source_label is required"):
        seed_database(tmp_path / "catalogue.db", data)


def test_invalid_peak_month_is_rejected(tmp_path: Path) -> None:
    data = tmp_path / "data"
    data.mkdir()
    _seed_files(data, destinations=[_destination(best_months="13")])

    with pytest.raises(ValueError, match="best_months"):
        seed_database(tmp_path / "catalogue.db", data)


def test_unconsented_contact_is_not_retained(tmp_path: Path) -> None:
    data = tmp_path / "data"
    data.mkdir()
    _seed_files(data, destinations=[_destination()])
    _write_csv(
        data,
        "homestays",
        [{
            "id": "1", "destination_id": "1", "name": "Private contact", "village": "",
            "nightly_min": "", "nightly_max": "", "currency": "", "public_contact": "person@example.test",
            "booking_url": "", "publish_contact": "0", "amenities": "", "source_label": "source",
            "source_url": "", "reviewer": "curator", "reviewed_at": "2026-10-12", "enabled": "1",
        }],
    )

    with pytest.raises(ValueError, match="publication consent"):
        seed_database(tmp_path / "catalogue.db", data)


def test_foreign_key_failure_rolls_back_entire_seed(tmp_path: Path) -> None:
    data = tmp_path / "data"
    data.mkdir()
    _seed_files(data, destinations=[_destination()])
    _write_csv(
        data,
        "alternative_links",
        [{
            "id": "1",
            "source_destination_id": "1",
            "alternative_destination_id": "99",
            "match_tags": "",
            "travel_fit": "",
            "source_label": "Reviewed source",
            "source_url": "",
            "reviewer": "curator",
            "reviewed_at": "2026-10-12",
            "enabled": "1",
        }],
    )

    with pytest.raises(ValueError, match="database constraint"):
        seed_database(tmp_path / "catalogue.db", data)

    with connect_database(tmp_path / "catalogue.db") as connection:
        assert connection.execute("SELECT count(*) FROM destinations").fetchone()[0] == 0


def test_database_connections_enable_foreign_keys(tmp_path: Path) -> None:
    database = tmp_path / "catalogue.db"
    _seed_files(tmp_path / "data")
    seed_database(database, tmp_path / "data")

    with connect_database(database) as connection:
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO alternative_links "
                "(id, source_destination_id, alternative_destination_id, source_label, "
                "reviewer, reviewed_at) VALUES (1, 1, 2, 'source', 'reviewer', '2026-10-12')"
            )


def test_schema_version_is_recorded_and_future_versions_are_rejected(tmp_path: Path) -> None:
    database = tmp_path / "catalogue.db"
    _seed_files(tmp_path / "data")
    seed_database(database, tmp_path / "data")

    with connect_database(database) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 2
        connection.execute("PRAGMA user_version = 99")

    with pytest.raises(RuntimeError, match="newer than supported"):
        seed_database(database, tmp_path / "data")


def test_demo_inventory_is_seeded_as_explicit_mock_data(tmp_path: Path) -> None:
    data = tmp_path / "data"
    _seed_files(data, destinations=[_destination()])
    _write_csv(
        data,
        "homestays",
        [{
            "id": "1", "destination_id": "1", "name": "Demo stay", "village": "",
            "nightly_min": "", "nightly_max": "", "currency": "", "public_contact": "",
            "booking_url": "", "publish_contact": "0", "amenities": "",
            "source_label": "DEMO FIXTURE - NOT VERIFIED", "source_url": "",
            "reviewer": "fixture", "reviewed_at": "2026-10-12", "enabled": "1",
        }],
    )
    _write_csv(
        data,
        "homestay_inventory",
        [{
            "id": "1", "homestay_id": "1", "inventory_date": "2026-11-07",
            "total_units": "2", "available_units": "1", "inventory_mode": "demo_mock",
            "source_label": "DEMO MOCK INVENTORY - NOT REAL", "source_url": "",
            "reviewer": "fixture", "reviewed_at": "2026-10-12", "enabled": "1",
        }],
    )

    counts = seed_database(tmp_path / "catalogue.db", data)
    assert counts["homestay_inventory"] == 1
    with connect_database(tmp_path / "catalogue.db") as connection:
        row = connection.execute(
            "SELECT inventory_mode, total_units, available_units FROM homestay_inventory"
        ).fetchone()
    assert tuple(row) == ("demo_mock", 2, 1)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("available_units", "3", "available_units cannot exceed total_units"),
        ("inventory_mode", "live", "inventory_mode must be demo_mock"),
    ],
)
def test_invalid_inventory_fixture_is_rejected(
    tmp_path: Path,
    field: str,
    value: str,
    message: str,
) -> None:
    data = tmp_path / "data"
    _seed_files(data)
    inventory = {
        "id": "1", "homestay_id": "1", "inventory_date": "2026-11-07",
        "total_units": "2", "available_units": "1", "inventory_mode": "demo_mock",
        "source_label": "DEMO MOCK INVENTORY - NOT REAL", "source_url": "",
        "reviewer": "fixture", "reviewed_at": "2026-10-12", "enabled": "1",
    }
    inventory[field] = value
    _write_csv(data, "homestay_inventory", [inventory])

    with pytest.raises(ValueError, match=message):
        seed_database(tmp_path / "catalogue.db", data)
