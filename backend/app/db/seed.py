from __future__ import annotations

import csv
import sqlite3
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app.db.database import connect_database, initialize_database
from app.config import load_settings


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_FILES: dict[str, tuple[str, ...]] = {
    "destinations": (
        "id", "name", "district", "region", "description", "tags", "best_months",
        "popularity_score", "source_label", "source_url", "reviewer", "reviewed_at", "enabled",
    ),
    "alternative_links": (
        "id", "source_destination_id", "alternative_destination_id", "match_tags",
        "travel_fit", "source_label", "source_url", "reviewer", "reviewed_at", "enabled",
    ),
    "homestays": (
        "id", "destination_id", "name", "village", "nightly_min", "nightly_max", "currency",
        "public_contact", "booking_url", "publish_contact", "amenities", "source_label",
        "source_url", "reviewer", "reviewed_at", "enabled",
    ),
    "homestay_inventory": (
        "id", "homestay_id", "inventory_date", "total_units", "available_units",
        "inventory_mode", "source_label", "source_url", "reviewer", "reviewed_at", "enabled",
    ),
    "local_events": (
        "id", "destination_id", "region", "name", "starts_on", "ends_on", "pressure",
        "source_label", "source_url", "reviewer", "reviewed_at", "enabled",
    ),
    "event_calendar_reviews": (
        "id", "region", "starts_on", "ends_on", "source_label", "source_url", "reviewer",
        "reviewed_at", "enabled",
    ),
}


def _required(row: dict[str, str], name: str, file_path: Path, row_number: int) -> str:
    value = row.get(name, "").strip()
    if not value:
        raise ValueError(f"{file_path.name}:{row_number}: {name} is required.")
    return value


def _integer(
    row: dict[str, str],
    name: str,
    file_path: Path,
    row_number: int,
    *,
    minimum: int | None = None,
    maximum: int | None = None,
    optional: bool = False,
) -> int | None:
    raw = row.get(name, "").strip()
    if not raw and optional:
        return None
    try:
        value = int(raw)
    except ValueError as error:
        raise ValueError(f"{file_path.name}:{row_number}: {name} must be an integer.") from error
    if minimum is not None and value < minimum:
        raise ValueError(f"{file_path.name}:{row_number}: {name} must be at least {minimum}.")
    if maximum is not None and value > maximum:
        raise ValueError(f"{file_path.name}:{row_number}: {name} must be at most {maximum}.")
    return value


def _flag(row: dict[str, str], name: str, file_path: Path, row_number: int) -> int:
    value = _integer(row, name, file_path, row_number, minimum=0, maximum=1)
    if value is None:
        raise ValueError(f"{file_path.name}:{row_number}: {name} is required.")
    return value


def _date(row: dict[str, str], name: str, file_path: Path, row_number: int) -> str:
    raw = _required(row, name, file_path, row_number)
    try:
        parsed = date.fromisoformat(raw)
    except ValueError as error:
        raise ValueError(f"{file_path.name}:{row_number}: {name} must use YYYY-MM-DD.") from error
    if parsed.isoformat() != raw:
        raise ValueError(f"{file_path.name}:{row_number}: {name} must use YYYY-MM-DD.")
    return raw


def _url(row: dict[str, str], name: str, file_path: Path, row_number: int) -> str | None:
    value = row.get(name, "").strip() or None
    if value is not None:
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError(f"{file_path.name}:{row_number}: {name} must be an HTTP(S) URL.")
    return value


def _tags(row: dict[str, str], name: str, file_path: Path, row_number: int) -> str:
    parts = [part.strip() for part in row.get(name, "").split(";") if part.strip()]
    if len(parts) != len({part.casefold() for part in parts}):
        raise ValueError(f"{file_path.name}:{row_number}: {name} contains duplicate values.")
    return ";".join(parts)


def _months(row: dict[str, str], file_path: Path, row_number: int) -> str:
    months = _tags(row, "best_months", file_path, row_number)
    if months and any(not part.isdigit() or not 1 <= int(part) <= 12 for part in months.split(";")):
        raise ValueError(f"{file_path.name}:{row_number}: best_months must contain month numbers 1-12.")
    return months


def _record(table: str, row: dict[str, str], file_path: Path, row_number: int) -> tuple[Any, ...]:
    record_id = _integer(row, "id", file_path, row_number, minimum=1)
    assert record_id is not None
    provenance = (
        _required(row, "source_label", file_path, row_number),
        _url(row, "source_url", file_path, row_number),
        _required(row, "reviewer", file_path, row_number),
        _date(row, "reviewed_at", file_path, row_number),
    )

    if table == "destinations":
        popularity_score = _integer(
            row, "popularity_score", file_path, row_number,
            minimum=0, maximum=100, optional=True,
        )
        return (
            record_id,
            _required(row, "name", file_path, row_number),
            _required(row, "district", file_path, row_number),
            _required(row, "region", file_path, row_number),
            row.get("description", "").strip(),
            _tags(row, "tags", file_path, row_number),
            _months(row, file_path, row_number),
            popularity_score,
            *provenance,
            _flag(row, "enabled", file_path, row_number),
        )

    if table == "alternative_links":
        return (
            record_id,
            _integer(row, "source_destination_id", file_path, row_number, minimum=1),
            _integer(row, "alternative_destination_id", file_path, row_number, minimum=1),
            _tags(row, "match_tags", file_path, row_number),
            _integer(row, "travel_fit", file_path, row_number, minimum=0, maximum=100, optional=True),
            *provenance,
            _flag(row, "enabled", file_path, row_number),
        )

    if table == "homestays":
        price_min = _integer(row, "nightly_min", file_path, row_number, minimum=0, optional=True)
        price_max = _integer(row, "nightly_max", file_path, row_number, minimum=0, optional=True)
        currency = row.get("currency", "").strip().upper() or None
        if price_min is not None and (currency is None or len(currency) != 3):
            raise ValueError(f"{file_path.name}:{row_number}: a priced homestay needs a 3-letter currency.")
        if price_min is None and (price_max is not None or currency is not None):
            raise ValueError(f"{file_path.name}:{row_number}: price maximum/currency require nightly_min.")
        contact = row.get("public_contact", "").strip() or None
        booking_url = _url(row, "booking_url", file_path, row_number)
        publish_contact = _flag(row, "publish_contact", file_path, row_number)
        if not publish_contact and (contact is not None or booking_url is not None):
            raise ValueError(
                f"{file_path.name}:{row_number}: do not store contact details without publication consent."
            )
        if publish_contact and contact is None and booking_url is None:
            raise ValueError(f"{file_path.name}:{row_number}: publishing requires a consented contact or booking URL.")
        return (
            record_id,
            _integer(row, "destination_id", file_path, row_number, minimum=1),
            _required(row, "name", file_path, row_number),
            row.get("village", "").strip(),
            price_min,
            price_max,
            currency,
            contact,
            booking_url,
            publish_contact,
            _tags(row, "amenities", file_path, row_number),
            *provenance,
            _flag(row, "enabled", file_path, row_number),
        )

    if table == "homestay_inventory":
        total_units = _integer(row, "total_units", file_path, row_number, minimum=0)
        available_units = _integer(row, "available_units", file_path, row_number, minimum=0)
        if total_units is None or available_units is None:
            raise ValueError(f"{file_path.name}:{row_number}: inventory counts are required.")
        if available_units > total_units:
            raise ValueError(
                f"{file_path.name}:{row_number}: available_units cannot exceed total_units."
            )
        inventory_mode = _required(row, "inventory_mode", file_path, row_number)
        if inventory_mode != "demo_mock":
            raise ValueError(
                f"{file_path.name}:{row_number}: inventory_mode must be demo_mock."
            )
        return (
            record_id,
            _integer(row, "homestay_id", file_path, row_number, minimum=1),
            _date(row, "inventory_date", file_path, row_number),
            total_units,
            available_units,
            inventory_mode,
            *provenance,
            _flag(row, "enabled", file_path, row_number),
        )

    if table == "local_events":
        start = _date(row, "starts_on", file_path, row_number)
        end = _date(row, "ends_on", file_path, row_number)
        if start > end:
            raise ValueError(f"{file_path.name}:{row_number}: starts_on must not follow ends_on.")
        destination_id = _integer(row, "destination_id", file_path, row_number, minimum=1, optional=True)
        pressure = _integer(row, "pressure", file_path, row_number, minimum=0, maximum=100)
        if pressure is None:
            raise ValueError(f"{file_path.name}:{row_number}: pressure is required.")
        return (
            record_id,
            destination_id,
            _required(row, "region", file_path, row_number),
            _required(row, "name", file_path, row_number),
            start,
            end,
            pressure,
            *provenance,
            _flag(row, "enabled", file_path, row_number),
        )

    start = _date(row, "starts_on", file_path, row_number)
    end = _date(row, "ends_on", file_path, row_number)
    if start > end:
        raise ValueError(f"{file_path.name}:{row_number}: starts_on must not follow ends_on.")
    return (
        record_id,
        _required(row, "region", file_path, row_number),
        start,
        end,
        *provenance,
        _flag(row, "enabled", file_path, row_number),
    )


def _load_csv(table: str, data_directory: Path) -> list[tuple[Any, ...]]:
    file_path = data_directory / f"{table}.csv"
    expected_headers = DATA_FILES[table]
    with file_path.open(encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        if tuple(reader.fieldnames or ()) != expected_headers:
            raise ValueError(
                f"{file_path.name}: expected exact headers: {','.join(expected_headers)}."
            )
        records: list[tuple[Any, ...]] = []
        seen_ids: set[int] = set()
        for row_number, row in enumerate(reader, start=2):
            if None in row:
                raise ValueError(f"{file_path.name}:{row_number}: too many columns.")
            if all(not (value or "").strip() for value in row.values()):
                continue
            record = _record(table, row, file_path, row_number)
            record_id = record[0]
            if record_id in seen_ids:
                raise ValueError(f"{file_path.name}:{row_number}: duplicate id {record_id}.")
            seen_ids.add(record_id)
            records.append(record)
    return records


def seed_database(
    database_path: str | Path,
    data_directory: str | Path,
) -> dict[str, int]:
    directory = Path(data_directory)
    if not directory.is_dir():
        raise FileNotFoundError(f"Curated data directory does not exist: {directory}")
    records_by_table = {table: _load_csv(table, directory) for table in DATA_FILES}
    initialize_database(database_path)

    with connect_database(database_path) as connection:
        try:
            with connection:
                for table, records in records_by_table.items():
                    columns = DATA_FILES[table]
                    placeholders = ", ".join("?" for _ in columns)
                    assignments = ", ".join(
                        f"{column}=excluded.{column}" for column in columns if column != "id"
                    )
                    sql = (
                        f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders}) "
                        f"ON CONFLICT(id) DO UPDATE SET {assignments}"
                    )
                    for record in records:
                        connection.execute(sql, record)
        except sqlite3.IntegrityError as error:
            raise ValueError(f"Curated seed violates a database constraint: {error}") from error
    return {table: len(records) for table, records in records_by_table.items()}


def main() -> None:
    settings = load_settings()
    counts = seed_database(settings.database_path, PROJECT_ROOT / "data")
    summary = ", ".join(f"{table}={count}" for table, count in counts.items())
    print(f"Initialized {settings.database_path}; imported {summary}.")


if __name__ == "__main__":
    main()
