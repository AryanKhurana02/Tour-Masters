from __future__ import annotations

import csv
import itertools
import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Mapping


_REQUIRED_COLUMNS = {
    "holiday",
    "year",
    "date",
    "crowded_destinations",
    "quieter_destinations",
}
_PROVENANCE_COLUMNS = ("provenance_status", "status")


@dataclass(frozen=True)
class CrowdBenchmark:
    holiday: str
    year: int
    target_date: date
    crowded_destinations: tuple[str, ...]
    quieter_destinations: tuple[str, ...]
    provenance_status: str


def normalize_destination_name(name: str) -> str:
    """Normalize spacing and case without making place-name aliases."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", name).strip()).casefold()


def _parse_destination_list(value: str, *, row_number: int, column: str) -> tuple[str, ...]:
    names = tuple(part.strip() for part in value.split(";") if part.strip())
    normalized = [normalize_destination_name(name) for name in names]
    if not names:
        raise ValueError(f"row {row_number}: {column} must contain at least one place name.")
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"row {row_number}: {column} contains duplicate normalized place names.")
    return names


def load_holiday_crowd_benchmarks(
    csv_path: str | Path,
) -> list[CrowdBenchmark]:
    """Load one qualitative crowded-versus-quieter benchmark per holiday date."""
    path = Path(csv_path)
    benchmarks: list[CrowdBenchmark] = []
    seen_dates: set[tuple[str, int, date]] = set()

    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file, strict=True)
        fieldnames = [header.strip() if header else "" for header in (reader.fieldnames or [])]
        if len(fieldnames) != len(set(fieldnames)):
            raise ValueError(f"{path}: CSV header contains duplicate column names.")
        reader.fieldnames = fieldnames
        headers = {header for header in fieldnames if header}
        missing_columns = _REQUIRED_COLUMNS - headers
        provenance_column = next((name for name in _PROVENANCE_COLUMNS if name in headers), None)
        if missing_columns or provenance_column is None:
            missing = sorted(missing_columns)
            if provenance_column is None:
                missing.append("provenance_status (or status)")
            raise ValueError(
                f"{path}: missing required CSV column(s): {', '.join(missing)}."
            )

        for row_number, row in enumerate(reader, start=2):
            if None in row:
                raise ValueError(f"{path}: row {row_number} has more columns than the header.")
            values = {key.strip(): value for key, value in row.items() if key is not None}
            if not any((value or "").strip() for value in values.values()):
                continue

            holiday = (values.get("holiday") or "").strip()
            raw_year = (values.get("year") or "").strip()
            raw_date = (values.get("date") or "").strip()
            provenance_status = (values.get(provenance_column) or "").strip()
            if not holiday:
                raise ValueError(f"{path}: row {row_number} has an empty holiday.")
            if not provenance_status:
                raise ValueError(f"{path}: row {row_number} has an empty {provenance_column}.")
            try:
                year = int(raw_year)
            except ValueError as error:
                raise ValueError(f"{path}: row {row_number} has an invalid year {raw_year!r}.") from error
            try:
                target_date = date.fromisoformat(raw_date)
            except ValueError as error:
                raise ValueError(f"{path}: row {row_number} has an invalid ISO date {raw_date!r}.") from error
            if target_date.year != year:
                raise ValueError(
                    f"{path}: row {row_number} year {year} does not match date {raw_date!r}."
                )

            key = (normalize_destination_name(holiday), year, target_date)
            if key in seen_dates:
                raise ValueError(
                    f"{path}: row {row_number} duplicates holiday/year/date "
                    f"{holiday!r}/{year}/{raw_date}."
                )
            seen_dates.add(key)

            crowded = _parse_destination_list(
                values.get("crowded_destinations") or "",
                row_number=row_number,
                column="crowded_destinations",
            )
            quieter = _parse_destination_list(
                values.get("quieter_destinations") or "",
                row_number=row_number,
                column="quieter_destinations",
            )
            crowded_normalized = {normalize_destination_name(name) for name in crowded}
            overlap = crowded_normalized & {
                normalize_destination_name(name) for name in quieter
            }
            if overlap:
                raise ValueError(
                    f"{path}: row {row_number} places cannot be both crowded and quieter: "
                    f"{', '.join(sorted(overlap))}."
                )

            benchmarks.append(
                CrowdBenchmark(
                    holiday=holiday,
                    year=year,
                    target_date=target_date,
                    crowded_destinations=crowded,
                    quieter_destinations=quieter,
                    provenance_status=provenance_status,
                )
            )
    return benchmarks


def evaluate_crowd_benchmarks(
    benchmarks: list[CrowdBenchmark],
    scores: Mapping[tuple[date, str], int],
    *,
    minimum_scored_pairs: int = 5,
) -> dict[str, object]:
    """Compare all crowded/quieter pairs; higher model scores mean more crowded."""
    if minimum_scored_pairs < 0:
        raise ValueError("minimum_scored_pairs must be non-negative.")

    normalized_scores: dict[tuple[date, str], int] = {}
    for (target_date, destination_name), score in scores.items():
        if isinstance(target_date, datetime):
            target_date = target_date.date()
        if not isinstance(target_date, date):
            raise TypeError("score keys must use datetime.date values.")
        normalized_name = normalize_destination_name(destination_name)
        if normalized_name:
            key = (target_date, normalized_name)
            if key in normalized_scores:
                raise ValueError(
                    f"multiple score keys normalize to the same destination name "
                    f"for {target_date.isoformat()}: {normalized_name!r}."
                )
            if isinstance(score, bool) or not isinstance(score, int) or not 0 <= score <= 100:
                raise ValueError(f"crowd score for {normalized_name!r} must be an integer from 0 to 100.")
            normalized_scores[key] = score

    result_rows: list[dict[str, object]] = []
    total_possible = total_scored = total_concordant = total_tied = total_discordant = 0
    all_missing_names: set[tuple[date, str]] = set()

    for benchmark in benchmarks:
        crowded = [
            (name, normalized_scores.get((benchmark.target_date, normalize_destination_name(name))))
            for name in benchmark.crowded_destinations
        ]
        quieter = [
            (name, normalized_scores.get((benchmark.target_date, normalize_destination_name(name))))
            for name in benchmark.quieter_destinations
        ]
        missing_names = sorted(
            {
                name
                for name, score in itertools.chain(crowded, quieter)
                if score is None
            },
            key=normalize_destination_name,
        )
        possible_pairs = len(crowded) * len(quieter)
        concordant = tied = discordant = scored_pairs = 0
        for (_, crowded_score), (_, quieter_score) in itertools.product(crowded, quieter):
            if crowded_score is None or quieter_score is None:
                continue
            scored_pairs += 1
            if crowded_score > quieter_score:
                concordant += 1
            elif crowded_score == quieter_score:
                tied += 1
            else:
                discordant += 1

        total_possible += possible_pairs
        total_scored += scored_pairs
        total_concordant += concordant
        total_tied += tied
        total_discordant += discordant
        all_missing_names.update((benchmark.target_date, name) for name in missing_names)
        result_rows.append(
            {
                "holiday": benchmark.holiday,
                "year": benchmark.year,
                "date": benchmark.target_date.isoformat(),
                "provenance_status": benchmark.provenance_status,
                "possible_pairs": possible_pairs,
                "scored_pairs": scored_pairs,
                "coverage": scored_pairs / possible_pairs if possible_pairs else 0.0,
                "concordant": concordant,
                "tied": tied,
                "discordant": discordant,
                "missing_place_names": missing_names,
                "status": (
                    "insufficient_coverage"
                    if scored_pairs < minimum_scored_pairs
                    else "evaluated"
                ),
            }
        )

    return {
        "minimum_scored_pairs": minimum_scored_pairs,
        "possible_pairs": total_possible,
        "scored_pairs": total_scored,
        "coverage": total_scored / total_possible if total_possible else 0.0,
        "concordant": total_concordant,
        "tied": total_tied,
        "discordant": total_discordant,
        "missing_place_names": [
            {"date": target_date.isoformat(), "name": name}
            for target_date, name in sorted(
                all_missing_names,
                key=lambda item: (item[0], normalize_destination_name(item[1])),
            )
        ],
        "status": (
            "insufficient_coverage"
            if total_scored < minimum_scored_pairs
            else "evaluated"
        ),
        "benchmarks": result_rows,
    }
