from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

import pytest

from app.services.crowd_evaluation import (
    CrowdBenchmark,
    evaluate_crowd_benchmarks,
    load_holiday_crowd_benchmarks,
)


def _holiday_csv_rows() -> list[dict[str, str]]:
    return [
        {
            "holiday": "Republic Day",
            "year": "2022",
            "date": "2022-01-26",
            "crowded_destinations": "Mussoorie;Auli;Rishikesh",
            "quieter_destinations": "Chopta;Khirsu;Munsiyari",
            "provenance_status": "user_supplied_unverified",
        },
        {
            "holiday": "Republic Day",
            "year": "2023",
            "date": "2023-01-26",
            "crowded_destinations": "Mussoorie;Auli;Rishikesh",
            "quieter_destinations": "Chopta;Khirsu;Munsiyari",
            "provenance_status": "user_supplied_unverified",
        },
        {
            "holiday": "Republic Day",
            "year": "2024",
            "date": "2024-01-26",
            "crowded_destinations": "Mussoorie;Auli;Rishikesh",
            "quieter_destinations": "Chopta;Khirsu;Munsiyari",
            "provenance_status": "user_supplied_unverified",
        },
        {
            "holiday": "Maha Shivratri",
            "year": "2024",
            "date": "2024-03-08",
            "crowded_destinations": "Haridwar;Rishikesh;Neelkanth Mahadev",
            "quieter_destinations": "Binsar;Kausani;Lansdowne",
            "provenance_status": "user_supplied_unverified",
        },
        {
            "holiday": "Holi",
            "year": "2025",
            "date": "2025-03-14",
            "crowded_destinations": "Nainital;Mussoorie;Dehradun",
            "quieter_destinations": "Pangot;Mukteshwar;Kanatal",
            "provenance_status": "user_supplied_unverified",
        },
        {
            "holiday": "Good Friday",
            "year": "2025",
            "date": "2025-04-18",
            "crowded_destinations": "Rishikesh;Nainital;Jim Corbett National Park",
            "quieter_destinations": "Sattal;Naukuchiatal;Ranikhet",
            "provenance_status": "user_supplied_unverified",
        },
        {
            "holiday": "Buddha Purnima",
            "year": "2026",
            "date": "2026-05-31",
            "crowded_destinations": "Nainital;Rishikesh;Haridwar",
            "quieter_destinations": "Binsar;Munsiyari;Kausani",
            "provenance_status": "user_supplied_unverified",
        },
        {
            "holiday": "Independence Day",
            "year": "2026",
            "date": "2026-08-15",
            "crowded_destinations": "Mussoorie;Rishikesh;Dehradun",
            "quieter_destinations": "Munsiyari;Chopta;Naukuchiatal",
            "provenance_status": "user_supplied_unverified",
        },
        {
            "holiday": "Diwali",
            "year": "2022",
            "date": "2022-10-24",
            "crowded_destinations": "Haridwar;Rishikesh;Nainital",
            "quieter_destinations": "Binsar;Kanatal;Lansdowne",
            "provenance_status": "user_supplied_unverified",
        },
    ]


def _benchmark() -> CrowdBenchmark:
    return CrowdBenchmark(
        holiday="Test holiday",
        year=2026,
        target_date=date(2026, 1, 26),
        crowded_destinations=("Mussoorie",),
        quieter_destinations=("Munsiyari",),
        provenance_status="user_supplied_unverified",
    )


def test_imported_holiday_csv_has_nine_rows_and_year_span(tmp_path: Path) -> None:
    csv_path = tmp_path / "holiday_crowd_mapping.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "holiday",
                "year",
                "date",
                "crowded_destinations",
                "quieter_destinations",
                "provenance_status",
            ],
        )
        writer.writeheader()
        writer.writerows(_holiday_csv_rows())

    benchmarks = load_holiday_crowd_benchmarks(csv_path)

    assert len(benchmarks) == 9
    assert {benchmark.year for benchmark in benchmarks} == {2022, 2023, 2024, 2025, 2026}
    assert {benchmark.target_date.year for benchmark in benchmarks} == {2022, 2023, 2024, 2025, 2026}
    assert all(benchmark.provenance_status == "user_supplied_unverified" for benchmark in benchmarks)
    assert all(benchmark.crowded_destinations and benchmark.quieter_destinations for benchmark in benchmarks)


def test_pairwise_ordering_and_coverage_are_evaluated_without_ground_truth_claims() -> None:
    benchmark = _benchmark()
    scores = {
        (benchmark.target_date, "Mussoorie"): 80,
        (benchmark.target_date, "Munsiyari"): 30,
    }

    result = evaluate_crowd_benchmarks([benchmark], scores, minimum_scored_pairs=1)

    assert result["possible_pairs"] == 1
    assert result["scored_pairs"] == 1
    assert result["coverage"] == 1.0
    assert result["concordant"] == 1
    assert result["tied"] == 0
    assert result["discordant"] == 0
    assert result["status"] == "evaluated"

    insufficient = evaluate_crowd_benchmarks(
        [benchmark],
        {(benchmark.target_date, "Mussoorie Mall Road"): 90},
        minimum_scored_pairs=1,
    )

    assert insufficient["status"] == "insufficient_coverage"
    assert insufficient["scored_pairs"] == 0
    assert any(item["name"] == "Munsiyari" for item in insufficient["missing_place_names"])
    assert any(item["name"] == "Mussoorie" for item in insufficient["missing_place_names"])


@pytest.mark.parametrize("score", [-1, 101, 50.5, True])
def test_evaluator_rejects_invalid_model_scores_if_validation_is_exposed(score: object) -> None:
    benchmark = _benchmark()

    with pytest.raises(ValueError, match="integer from 0 to 100"):
        evaluate_crowd_benchmarks(
            [benchmark],
            {
                (benchmark.target_date, "Mussoorie"): score,  # type: ignore[dict-item]
                (benchmark.target_date, "Munsiyari"): 20,
            },
        )
