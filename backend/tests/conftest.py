from __future__ import annotations

import csv
from pathlib import Path
from collections.abc import Iterator

import pytest

from app.config import Settings
from app.db.seed import DATA_FILES, seed_database
from app.main import create_app
from tests.asgi_client import TestClient


def write_catalogue(directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    rows = {
        "destinations": [
            {
                "id": "1", "name": "Start Place", "district": "District A", "region": "Uttarakhand",
                "description": "", "tags": "forest", "best_months": "10", "popularity_score": "80",
                "source_label": "Reviewed source", "source_url": "", "reviewer": "curator",
                "reviewed_at": "2026-09-15", "enabled": "1",
            },
            {
                "id": "2", "name": "Quiet Alternative", "district": "District B", "region": "Uttarakhand",
                "description": "", "tags": "hiking;forest", "best_months": "10", "popularity_score": "10",
                "source_label": "Reviewed source", "source_url": "", "reviewer": "curator",
                "reviewed_at": "2026-09-15", "enabled": "1",
            },
            {
                "id": "3", "name": "Busy Alternative", "district": "District C", "region": "Uttarakhand",
                "description": "", "tags": "market", "best_months": "", "popularity_score": "100",
                "source_label": "Reviewed source", "source_url": "", "reviewer": "curator",
                "reviewed_at": "2026-09-15", "enabled": "1",
            },
            {
                "id": "4", "name": "Unlinked Start", "district": "District D", "region": "Uttarakhand",
                "description": "", "tags": "", "best_months": "", "popularity_score": "50",
                "source_label": "Reviewed source", "source_url": "", "reviewer": "curator",
                "reviewed_at": "2026-09-15", "enabled": "1",
            },
        ],
        "alternative_links": [
            {
                "id": "1", "source_destination_id": "1", "alternative_destination_id": "2",
                "match_tags": "hiking", "travel_fit": "", "source_label": "Reviewed source",
                "source_url": "", "reviewer": "curator", "reviewed_at": "2026-09-15", "enabled": "1",
            },
            {
                "id": "2", "source_destination_id": "1", "alternative_destination_id": "3",
                "match_tags": "", "travel_fit": "90", "source_label": "Reviewed source",
                "source_url": "", "reviewer": "curator", "reviewed_at": "2026-09-15", "enabled": "1",
            },
        ],
        "homestays": [
            {
                "id": "1", "destination_id": "2", "name": "Reviewed Homestay", "village": "Village B",
                "nightly_min": "1000", "nightly_max": "1200", "currency": "INR", "public_contact": "",
                "booking_url": "", "publish_contact": "0", "amenities": "meals", "source_label": "Reviewed source",
                "source_url": "", "reviewer": "curator", "reviewed_at": "2026-09-15", "enabled": "1",
            },
        ],
        "local_events": [
            {
                "id": "1", "destination_id": "3", "region": "Uttarakhand", "name": "Reviewed event",
                "starts_on": "2026-10-17", "ends_on": "2026-10-17", "pressure": "100",
                "source_label": "Reviewed source", "source_url": "", "reviewer": "curator",
                "reviewed_at": "2026-09-15", "enabled": "1",
            },
        ],
        "event_calendar_reviews": [
            {
                "id": "1", "region": "Uttarakhand", "starts_on": "2026-10-01", "ends_on": "2026-10-31",
                "source_label": "Reviewed calendar", "source_url": "", "reviewer": "curator",
                "reviewed_at": "2026-09-15", "enabled": "1",
            },
        ],
    }
    for table, headers in DATA_FILES.items():
        with (directory / f"{table}.csv").open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows.get(table, []))
    database_path = directory.parent / "catalogue.db"
    seed_database(database_path, directory)
    return database_path


@pytest.fixture
def catalogue_path(tmp_path: Path) -> Path:
    return write_catalogue(tmp_path / "data")


@pytest.fixture
def test_client(catalogue_path: Path) -> Iterator[TestClient]:
    settings = Settings(
        database_path=catalogue_path,
        cors_origins=("http://localhost:5173",),
        enable_llm=False,
    )
    with TestClient(create_app(settings), client=("127.0.0.5", 55000)) as client:
        yield client
