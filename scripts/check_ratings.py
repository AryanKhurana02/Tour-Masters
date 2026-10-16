#!/usr/bin/env python3
"""Calibration check for the Holiday Climate Index (HCI) crowd formula.

Compares our offline crowd estimate against ground-truth local crowd levels in
``validation/local_ratings.csv`` and reports:

  * Exact match %      (estimated level == reported level)
  * Within-one-level % (levels differ by at most one band)
  * Confidence score   (derived from sample volume and agreement)

The simulation mirrors the production offline pipeline: it uses the same
5-year historical climatology (and therefore the same HCI) that the API uses
when no fresh forecast is stored.

``validation/local_ratings.csv`` is optional. Expected columns:
    destination_id, date, local_reported_crowd_level
where ``local_reported_crowd_level`` is one of Quiet / Moderate / Busy / Very busy.

Usage:
    py -3.12 scripts/check_ratings.py
"""

from __future__ import annotations

import csv
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.crowd_score import crowd_level, estimate_crowd  # noqa: E402
from app.services.seasonality import get_seasonal_demand_for_month  # noqa: E402
from app.services.weather_history import get_historical_weather_friction  # noqa: E402

RATINGS_PATH = REPO_ROOT / "validation" / "local_ratings.csv"

LEVELS = ["Quiet", "Moderate", "Busy", "Very busy"]
LEVEL_INDEX = {level: index for index, level in enumerate(LEVELS)}

# Map the string keys used in the historical CSV back to display names.
CSV_DESTINATION_NAMES = {
    "almora": "Almora",
    "munsiyari": "Munsiyari",
    "kausani": "Kausani",
    "binsar": "Binsar",
    "mussoorie": "Mussoorie",
    "dehradun": "Dehradun",
    "nainital": "Nainital",
    "chopta": "Chopta",
    "kedarnath": "Kedarnath",
    "haridwar": "Haridwar",
    "rishikesh": "Rishikesh",
}


def _load_catalogue() -> dict[str, dict[str, Any]]:
    """Load popularity + best_months from the seeded catalogue DB, if present."""
    catalogue: dict[str, dict[str, Any]] = {}
    try:
        from app.config import load_settings
        from app.db.database import connect_database

        settings = load_settings()
    except Exception:  # pragma: no cover - optional dependency path
        return catalogue

    if not settings.database_path.is_file():
        return catalogue

    try:
        with connect_database(settings.database_path) as connection:
            rows = connection.execute(
                "SELECT name, popularity_score, best_months FROM destinations"
            ).fetchall()
    except Exception:  # pragma: no cover - malformed DB
        return catalogue

    for row in rows:
        best_months = _parse_best_months(row["best_months"])
        catalogue[str(row["name"]).strip().casefold()] = {
            "name": row["name"],
            "popularity_score": row["popularity_score"],
            "best_months": best_months,
        }
    return catalogue


def _parse_best_months(raw: Any) -> list[int]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [int(value) for value in raw]
    months: list[int] = []
    for token in str(raw).replace("[", " ").replace("]", " ").replace(",", " ").split():
        try:
            months.append(int(token))
        except ValueError:
            continue
    return months


def _resolve_destination(
    raw_id: str, catalogue: dict[str, dict[str, Any]]
) -> dict[str, Any] | None:
    key = raw_id.strip()
    if key.isdigit():
        # Numeric ids map to CSV keys by insertion order (almora=1 ... rishikesh=11).
        index = int(key)
        keys = list(CSV_DESTINATION_NAMES.keys())
        if 1 <= index <= len(keys):
            key = keys[index - 1]
    key = key.casefold()
    name = CSV_DESTINATION_NAMES.get(key, key.title())
    if key not in catalogue:
        return None
    entry = dict(catalogue[key])
    entry["name"] = entry.get("name") or name
    return entry


def load_ratings() -> list[dict[str, Any]]:
    if not RATINGS_PATH.exists():
        print(f"Local ratings file not found: {RATINGS_PATH}")
        print("Add validation/local_ratings.csv (see validation/README.md) to calibrate.")
        return []

    ratings: list[dict[str, Any]] = []
    with RATINGS_PATH.open("r", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            try:
                ratings.append(
                    {
                        "destination_id": str(row["destination_id"]),
                        "date": date.fromisoformat(row["date"].strip()),
                        "reported_level": row["local_reported_crowd_level"].strip(),
                    }
                )
            except (KeyError, ValueError) as error:
                print(f"Skipping invalid ratings row {row}: {error}")
    print(f"Loaded {len(ratings)} ground-truth ratings from {RATINGS_PATH}")
    return ratings


def run_calibration() -> dict[str, Any]:
    ratings = load_ratings()
    if not ratings:
        return {"error": "No ratings to compare."}

    catalogue = _load_catalogue()
    results: list[dict[str, Any]] = []

    for rating in ratings:
        destination = _resolve_destination(rating["destination_id"], catalogue)
        if destination is None:
            # Not a catalogue destination; use neutral inputs but real climatology.
            destination = {
                "name": CSV_DESTINATION_NAMES.get(
                    rating["destination_id"].casefold(), rating["destination_id"].title()
                ),
                "popularity_score": None,
                "best_months": [],
            }
        destination["reviewed_at"] = rating["date"]

        month = rating["date"].month
        historical_climate = get_historical_weather_friction(destination["name"], month)
        seasonal_index = get_seasonal_demand_for_month(month)

        estimate = estimate_crowd(
            destination,
            rating["date"],
            event_pressure=50,
            weather_signal=None,
            historical_climate=historical_climate,
            seasonal_index=seasonal_index,
        )

        predicted_level = estimate["level"]
        reported_level = rating["reported_level"]
        predicted_index = LEVEL_INDEX.get(predicted_level)
        reported_index = LEVEL_INDEX.get(reported_level)
        if predicted_index is None or reported_index is None:
            print(f"Skipping unknown level in rating: {rating}")
            continue

        results.append(
            {
                "destination_id": rating["destination_id"],
                "destination_name": destination["name"],
                "date": rating["date"].isoformat(),
                "predicted_level": predicted_level,
                "predicted_score": estimate["score"],
                "reported_level": reported_level,
                "hci_score": (historical_climate or {}).get("hci_score"),
                "exact": predicted_index == reported_index,
                "within_one": abs(predicted_index - reported_index) <= 1,
            }
        )

    if not results:
        return {"error": "No valid comparisons could be made."}

    total = len(results)
    exact = sum(1 for row in results if row["exact"])
    within_one = sum(1 for row in results if row["within_one"])
    exact_pct = exact / total
    within_one_pct = within_one / total

    # Confidence rewards both agreement and sample volume (saturates at 50 points).
    volume_factor = min(1.0, total / 50)
    confidence = round(100 * (0.5 * exact_pct + 0.5 * within_one_pct) * volume_factor, 1)

    return {
        "total": total,
        "exact": exact,
        "exact_pct": round(exact_pct * 100, 1),
        "within_one": within_one,
        "within_one_pct": round(within_one_pct * 100, 1),
        "confidence_score": confidence,
        "predicted_distribution": dict(Counter(row["predicted_level"] for row in results)),
        "reported_distribution": dict(Counter(row["reported_level"] for row in results)),
        "results": results,
    }


def print_report(report: dict[str, Any]) -> None:
    if "error" in report:
        print(f"\n{report['error']}")
        return

    print("\n" + "=" * 58)
    print("HCI CALIBRATION REPORT")
    print("=" * 58)
    print(f"Total comparisons : {report['total']}")
    print(f"Exact matches     : {report['exact']} ({report['exact_pct']}%)")
    print(f"Within one level  : {report['within_one']} ({report['within_one_pct']}%)")
    print(f"Confidence score  : {report['confidence_score']}/100")
    print("-" * 58)
    print(f"Predicted levels  : {report['predicted_distribution']}")
    print(f"Reported levels   : {report['reported_distribution']}")

    mismatches = [row for row in report["results"] if not row["exact"]]
    if mismatches:
        print(f"\nMismatches ({len(mismatches)}):")
        for row in mismatches[:15]:
            print(
                f"  {row['date']} {row['destination_name']}: "
                f"predicted {row['predicted_level']} ({row['predicted_score']}) vs "
                f"reported {row['reported_level']} | HCI {row['hci_score']}"
            )


def main() -> int:
    print("Running HCI calibration check...")
    report = run_calibration()
    print_report(report)
    if "error" in report:
        return 0
    if report["confidence_score"] < 50:
        print("\nLow confidence - HCI thresholds may need tuning.")
    else:
        print("\nCalibration acceptable.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
