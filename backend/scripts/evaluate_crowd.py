from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Sequence

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config import load_settings
from app.db.database import connect_database
from app.repositories.destination_repository import get_event_pressure, list_destinations
from app.services.crowd_evaluation import (
    evaluate_crowd_benchmarks,
    load_holiday_crowd_benchmarks,
    normalize_destination_name,
)
from app.services.crowd_score import estimate_crowd
from app.repositories.weather_repository import get_weather_visit_tendency


_DEFAULT_BENCHMARK_PATH = PROJECT_ROOT / "data" / "validation" / "holiday_crowd_mapping.csv"
_WARNINGS = [
    "Workbook-derived comparisons are unverified qualitative validation only; they are not numeric model labels.",
    "The application dataset may be synthetic; benchmark agreement is not evidence of real-world accuracy.",
]


def evaluate(
    benchmark_path: str | Path = _DEFAULT_BENCHMARK_PATH,
    *,
    minimum_scored_pairs: int = 5,
) -> dict[str, object]:
    benchmarks = load_holiday_crowd_benchmarks(benchmark_path)
    settings = load_settings()
    scores: dict[tuple[date, str], int] = {}

    with connect_database(settings.database_path) as connection:
        destinations = list_destinations(connection)
        seen_names: set[str] = set()
        for destination in destinations:
            normalized_name = normalize_destination_name(destination["name"])
            if not normalized_name:
                continue
            if normalized_name in seen_names:
                raise ValueError(
                    "Enabled destinations contain duplicate normalized names; "
                    f"cannot score {destination['name']!r} unambiguously."
                )
            seen_names.add(normalized_name)
            for benchmark_date in sorted({benchmark.target_date for benchmark in benchmarks}):
                event_pressure = get_event_pressure(
                    connection,
                    region=destination["region"],
                    destination_id=destination["id"],
                    target_date=benchmark_date,
                )
                weather_signal = get_weather_visit_tendency(
                    connection,
                    destination_id=destination["id"],
                    target_date=benchmark_date,
                )
                estimate = estimate_crowd(
                    destination,
                    benchmark_date,
                    event_pressure,
                    weather_signal,
                )
                scores[(benchmark_date, normalized_name)] = estimate["score"]

    report = evaluate_crowd_benchmarks(
        benchmarks,
        scores,
        minimum_scored_pairs=minimum_scored_pairs,
    )
    return {
        "warnings": _WARNINGS,
        "evaluation": report,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Qualitatively compare current crowd estimates with holiday crowd mappings."
    )
    parser.add_argument(
        "--benchmark",
        type=Path,
        default=_DEFAULT_BENCHMARK_PATH,
        help=f"Benchmark CSV (default: {_DEFAULT_BENCHMARK_PATH})",
    )
    parser.add_argument(
        "--minimum-scored-pairs",
        type=int,
        default=5,
        help="Minimum scored pair count for sufficient coverage (default: 5).",
    )
    args = parser.parse_args(argv)
    report = evaluate(
        args.benchmark,
        minimum_scored_pairs=args.minimum_scored_pairs,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
