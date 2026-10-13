from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Sequence

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config import load_settings
from app.db.database import connect_database, initialize_database
from app.integrations.openmeteo import refresh_weather


def main(argv: Sequence[str] | None = None) -> int:
    del argv
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    settings = load_settings()
    initialize_database(settings.database_path)
    raw_directory = PROJECT_ROOT / "data" / "raw" / "weather"
    with connect_database(settings.database_path) as connection:
        report = refresh_weather(connection, raw_directory=raw_directory)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return int(any(source["status"] != "ok" for source in report["sources"]))


if __name__ == "__main__":
    raise SystemExit(main())
