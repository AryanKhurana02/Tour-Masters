from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator


SCHEMA_PATH = Path(__file__).with_name("schema.sql")
MIGRATIONS_PATH = Path(__file__).with_name("migrations")
SCHEMA_VERSION = 5


def _apply_script(connection: sqlite3.Connection, script: str, version: int) -> None:
    try:
        connection.executescript(
            f"BEGIN IMMEDIATE;\n{script}\nPRAGMA user_version = {version};\nCOMMIT;"
        )
    except sqlite3.Error:
        connection.rollback()
        raise


def initialize_database(database_path: str | Path) -> None:
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path, timeout=5.0) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        current_version = connection.execute("PRAGMA user_version").fetchone()[0]
        if current_version > SCHEMA_VERSION:
            raise RuntimeError(
                f"Database schema version {current_version} is newer than supported version {SCHEMA_VERSION}."
            )
        if current_version < 1:
            _apply_script(connection, SCHEMA_PATH.read_text(encoding="utf-8"), 1)
            current_version = 1

        for version in range(current_version + 1, SCHEMA_VERSION + 1):
            migration_path = MIGRATIONS_PATH / f"{version:04d}_*.sql"
            migration_files = sorted(MIGRATIONS_PATH.glob(f"{version:04d}_*.sql"))
            if len(migration_files) != 1:
                raise RuntimeError(
                    f"Expected exactly one database migration for schema version {version} "
                    f"at {migration_path.parent}."
                )
            _apply_script(
                connection,
                migration_files[0].read_text(encoding="utf-8"),
                version,
            )


@contextmanager
def connect_database(database_path: str | Path) -> Generator[sqlite3.Connection, None, None]:
    path = Path(database_path)
    if not path.is_file():
        raise FileNotFoundError(
            f"Catalogue database does not exist at {path}; initialize it and load curated data first."
        )

    # FastAPI may enter and exit a sync yield-dependency on different worker threads.
    connection = sqlite3.connect(path, timeout=5.0, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    try:
        yield connection
    finally:
        connection.close()
