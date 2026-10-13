from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from app.config import load_settings
from app.db.database import connect_database, initialize_database


def calculate_live_score() -> int:
    """Calculate a deterministic 'live' score based on time of day and day of week."""
    now = datetime.now(timezone.utc)
    hour = now.hour
    base_score = 50
    time_factor = 20 if 10 <= hour <= 16 else -10
    weekend_factor = 15 if now.weekday() >= 5 else 0
    return max(0, min(100, base_score + time_factor + weekend_factor))


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh live tourist metrics")
    parser.add_argument(
        "--database",
        type=Path,
        help="Path to SQLite database (defaults to settings.database_path)",
    )
    args = parser.parse_args()

    settings = load_settings()
    db_path = args.database or Path(settings.database_path)

    if not db_path.is_file():
        print(f"Database not found at {db_path}. Run seed first.")
        return 1

    try:
        with connect_database(db_path) as connection:
            destinations = connection.execute(
                "SELECT id FROM destinations WHERE enabled = 1"
            ).fetchall()

            if not destinations:
                print("No enabled destinations found.")
                return 0

            now_utc = datetime.now(timezone.utc).isoformat(timespec="seconds")
            score = calculate_live_score()
            data_source = "simulated_live"

            with connection:
                for dest in destinations:
                    connection.execute(
                        """
                        INSERT INTO live_tourist_metrics (destination_id, timestamp, live_crowd_index, data_source)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(destination_id, timestamp) DO UPDATE SET
                            live_crowd_index = excluded.live_crowd_index,
                            data_source = excluded.data_source
                        """,
                        (dest["id"], now_utc, score, data_source),
                    )

            print(f"Updated live metrics for {len(destinations)} destinations (score: {score}, source: {data_source}).")
            return 0

    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())