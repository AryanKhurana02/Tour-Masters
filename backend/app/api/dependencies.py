from collections.abc import Iterator
import sqlite3

from fastapi import HTTPException, Request

from app.db.database import connect_database


def get_database(request: Request) -> Iterator[sqlite3.Connection]:
    settings = request.app.state.settings
    try:
        with connect_database(settings.database_path) as connection:
            yield connection
    except FileNotFoundError as error:
        raise HTTPException(
            status_code=503,
            detail="Curated catalogue is not initialized; run the backend seed command first.",
        ) from error
