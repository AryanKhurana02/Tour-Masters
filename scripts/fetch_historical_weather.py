"""Fetch 5-year historical daily weather for key Uttarakhand nodes.

Source: Open-Meteo Archive API (https://open-meteo.com/en/docs/historical-weather-api)
Output: backend/app/data/uttarakhand_historical_weather.csv

Run from anywhere:  py -3.12 scripts/fetch_historical_weather.py

The CSV is consumed by backend/app/services/weather_history.py to compute
offline monthly rainfall climatology per destination (weather friction for
crowd estimates when no fresh forecast is stored).
Now includes HCI variables: cloudcover_mean, windspeed_10m_max
"""

from __future__ import annotations

import csv
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

# Repo-root-relative output so the script works from any working directory.
REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = REPO_ROOT / "backend" / "app" / "data"
OUTPUT_FILE = OUTPUT_DIR / "uttarakhand_historical_weather.csv"

START_DATE = "2021-01-01"
END_DATE = "2026-09-30"  # Multi-year historical range

API_URL = "https://archive-api.open-meteo.com/v1/archive"
# Added cloudcover_mean and windspeed_10m_max for HCI calculation
DAILY_VARS = "temperature_2m_max,temperature_2m_min,precipitation_sum,rain_sum,snowfall_sum,cloudcover_mean,windspeed_10m_max"
TIMEZONE = "Asia%2FKolkata"

# Key Uttarakhand tourist & eco-sensitive nodes.
# Coordinates for catalogue destinations (almora, munsiyari, kausani, binsar,
# mussoorie) are the reviewed OpenStreetMap place nodes recorded in
# data/weather_locations.csv. The remaining nodes use town-centre coordinates.
UTTARAKHAND_NODES = [
    {"id": "almora", "name": "Almora", "lat": 29.601699, "lon": 79.6632635, "type": "cultural_hill_town"},
    {"id": "munsiyari", "name": "Munsiyari", "lat": 30.06546, "lon": 80.23453, "type": "high_himalayan_views"},
    {"id": "kausani", "name": "Kausani", "lat": 29.8539706, "lon": 79.5943657, "type": "panorama_hill_station"},
    {"id": "binsar", "name": "Binsar", "lat": 29.6967018, "lon": 79.7538113, "type": "eco_sanctuary"},
    {"id": "mussoorie", "name": "Mussoorie", "lat": 30.4569012, "lon": 78.0782906, "type": "hill_station"},
    {"id": "dehradun", "name": "Dehradun", "lat": 30.3165, "lon": 78.0322, "type": "foothill_hub"},
    {"id": "nainital", "name": "Nainital", "lat": 29.3919, "lon": 79.4542, "type": "lake_district"},
    {"id": "chopta", "name": "Chopta", "lat": 30.4820, "lon": 79.1802, "type": "high_meadow_bugyal"},
    {"id": "kedarnath", "name": "Kedarnath", "lat": 30.7346, "lon": 79.0669, "type": "high_altitude_sacred"},
    {"id": "haridwar", "name": "Haridwar", "lat": 29.9457, "lon": 78.1642, "type": "religious_cultural"},
    {"id": "rishikesh", "name": "Rishikesh", "lat": 30.0869, "lon": 78.2676, "type": "yoga_rafting_hub"},
]

FIELDNAMES = [
    "destination_id",
    "destination_name",
    "date",
    "year",
    "month",
    "day_of_week",
    "precipitation_mm",
    "rain_mm",
    "snowfall_cm",
    "temp_max_c",
    "temp_min_c",
    "cloud_cover_pct",
    "wind_speed_kmh",
    "high_landslide_risk",
]

REQUEST_TIMEOUT_SECONDS = 60
MAX_ATTEMPTS = 3
PAUSE_BETWEEN_CALLS_SECONDS = 0.4


def _year_chunks(start_date: str, end_date: str) -> list[tuple[str, str]]:
    """Split the range into calendar-year chunks so each response stays small."""
    start = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(end_date)
    chunks: list[tuple[str, str]] = []
    year = start.year
    while year <= end.year:
        chunk_start = max(start, datetime(year, 1, 1))
        chunk_end = min(end, datetime(year, 12, 31))
        chunks.append((chunk_start.date().isoformat(), chunk_end.date().isoformat()))
        year += 1
    return chunks


def _fetch_chunk(lat: float, lon: float, start: str, end: str) -> dict | None:
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start,
        "end_date": end,
        "daily": DAILY_VARS,
        "timezone": "Asia/Kolkata",
    }
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = requests.get(API_URL, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
            if response.status_code == 200:
                return response.json()
            print(
                f"    attempt {attempt}/{MAX_ATTEMPTS}: HTTP {response.status_code} "
                f"for {start}..{end}"
            )
        except requests.RequestException as error:
            print(f"    attempt {attempt}/{MAX_ATTEMPTS}: {type(error).__name__}: {error}")
        if attempt < MAX_ATTEMPTS:
            time.sleep(1.5 * attempt)  # linear backoff
    return None


def fetch_node_historical_weather(node: dict) -> list[dict]:
    """Fetch all daily records for one node, year by year."""
    records: list[dict] = []
    for start, end in _year_chunks(START_DATE, END_DATE):
        payload = _fetch_chunk(node["lat"], node["lon"], start, end)
        if payload is None:
            print(f"    ! giving up on {start}..{end} after {MAX_ATTEMPTS} attempts")
            continue

        daily = payload.get("daily") or {}
        dates = daily.get("time") or []
        if not dates:
            print(f"    ! empty daily payload for {start}..{end}")
            continue

        precipitation = daily.get("precipitation_sum") or []
        rain = daily.get("rain_sum") or []
        snow = daily.get("snowfall_sum") or []
        temp_max = daily.get("temperature_2m_max") or []
        temp_min = daily.get("temperature_2m_min") or []
        cloud_cover = daily.get("cloudcover_mean") or []
        wind_speed = daily.get("windspeed_10m_max") or []

        for index, day in enumerate(dates):
            records.append(
                {
                    "date": day,
                    "precipitation_mm": precipitation[index] if index < len(precipitation) and precipitation[index] is not None else 0.0,
                    "rain_mm": rain[index] if index < len(rain) and rain[index] is not None else 0.0,
                    "snowfall_cm": snow[index] if index < len(snow) and snow[index] is not None else 0.0,
                    "temp_max_c": temp_max[index] if index < len(temp_max) and temp_max[index] is not None else 0.0,
                    "temp_min_c": temp_min[index] if index < len(temp_min) and temp_min[index] is not None else 0.0,
                    "cloud_cover_pct": cloud_cover[index] if index < len(cloud_cover) and cloud_cover[index] is not None else 50,
                    "wind_speed_kmh": wind_speed[index] if index < len(wind_speed) and wind_speed[index] is not None else 10,
                }
            )
        time.sleep(PAUSE_BETWEEN_CALLS_SECONDS)
    return records


def generate_weather_dataset() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    all_rows: list[dict] = []
    print(f"Fetching historical weather {START_DATE}..{END_DATE} for {len(UTTARAKHAND_NODES)} nodes...")

    for node in UTTARAKHAND_NODES:
        print(f"-> {node['name']} ({node['type']})")
        records = fetch_node_historical_weather(node)
        print(f"   {len(records)} daily records")
        for record in records:
            parsed = datetime.strptime(record["date"], "%Y-%m-%d")
            all_rows.append(
                {
                    "destination_id": node["id"],
                    "destination_name": node["name"],
                    "date": record["date"],
                    "year": parsed.year,
                    "month": parsed.month,
                    "day_of_week": parsed.strftime("%A"),
                    "precipitation_mm": round(record["precipitation_mm"], 1),
                    "rain_mm": round(record["rain_mm"], 1),
                    "snowfall_cm": round(record["snowfall_cm"], 1),
                    "temp_max_c": round(record["temp_max_c"], 1),
                    "temp_min_c": round(record["temp_min_c"], 1),
                    "cloud_cover_pct": int(round(record["cloud_cover_pct"])),
                    "wind_speed_kmh": round(record["wind_speed_kmh"], 1),
                    "high_landslide_risk": 1 if record["precipitation_mm"] > 40.0 else 0,
                }
            )

    if not all_rows:
        print("No weather records were fetched (network unavailable?). Aborting CSV write.")
        return 0

    all_rows.sort(key=lambda row: (row["destination_id"], row["date"]))
    with OUTPUT_FILE.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(all_rows)

    retrieved_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    print(f"\nSaved {len(all_rows)} daily records to {OUTPUT_FILE}")
    print(f"Fetched at {retrieved_at} (UTC)")
    return len(all_rows)


if __name__ == "__main__":
    total = generate_weather_dataset()
    sys.exit(0 if total else 1)