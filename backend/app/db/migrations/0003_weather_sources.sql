PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS weather_locations (
    id INTEGER PRIMARY KEY CHECK (id > 0),
    destination_id INTEGER NOT NULL UNIQUE REFERENCES destinations(id) ON DELETE CASCADE,
    latitude REAL NOT NULL CHECK (latitude BETWEEN -90 AND 90),
    longitude REAL NOT NULL CHECK (longitude BETWEEN -180 AND 180),
    elevation_m REAL CHECK (elevation_m IS NULL OR elevation_m BETWEEN -500 AND 9000),
    timezone TEXT NOT NULL CHECK (length(trim(timezone)) > 0),
    source_label TEXT NOT NULL CHECK (length(trim(source_label)) > 0),
    source_url TEXT NOT NULL,
    reviewer TEXT NOT NULL CHECK (length(trim(reviewer)) > 0),
    reviewed_at TEXT NOT NULL CHECK (date(reviewed_at) IS NOT NULL),
    enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1))
);

CREATE TABLE IF NOT EXISTS weather_climatology (
    destination_id INTEGER NOT NULL REFERENCES destinations(id) ON DELETE CASCADE,
    calendar_month INTEGER NOT NULL CHECK (calendar_month BETWEEN 1 AND 12),
    mean_temp_max REAL NOT NULL,
    mean_temp_min REAL NOT NULL,
    mean_temp REAL NOT NULL,
    mean_precipitation_mm REAL NOT NULL CHECK (mean_precipitation_mm >= 0),
    weather_visit_tendency INTEGER NOT NULL CHECK (weather_visit_tendency BETWEEN 0 AND 100),
    sample_count INTEGER NOT NULL CHECK (sample_count > 0),
    retrieved_at TEXT NOT NULL CHECK (datetime(retrieved_at) IS NOT NULL),
    source_url TEXT NOT NULL,
    PRIMARY KEY (destination_id, calendar_month)
);

CREATE TABLE IF NOT EXISTS weather_forecasts (
    destination_id INTEGER NOT NULL REFERENCES destinations(id) ON DELETE CASCADE,
    forecast_date TEXT NOT NULL CHECK (date(forecast_date) IS NOT NULL),
    temp_max REAL NOT NULL,
    temp_min REAL NOT NULL,
    temp_mean REAL NOT NULL,
    precipitation_mm REAL NOT NULL CHECK (precipitation_mm >= 0),
    weather_visit_tendency INTEGER NOT NULL CHECK (weather_visit_tendency BETWEEN 0 AND 100),
    retrieved_at TEXT NOT NULL CHECK (datetime(retrieved_at) IS NOT NULL),
    expires_at TEXT NOT NULL CHECK (datetime(expires_at) IS NOT NULL),
    source_url TEXT NOT NULL,
    PRIMARY KEY (destination_id, forecast_date)
);

CREATE INDEX IF NOT EXISTS idx_weather_forecasts_expiry
    ON weather_forecasts(forecast_date, expires_at);

CREATE TABLE IF NOT EXISTS data_source_refreshes (
    source_key TEXT PRIMARY KEY CHECK (length(trim(source_key)) > 0),
    status TEXT NOT NULL CHECK (status IN ('ok', 'missing', 'stale')),
    retrieved_at TEXT NOT NULL CHECK (datetime(retrieved_at) IS NOT NULL),
    last_success_at TEXT CHECK (last_success_at IS NULL OR datetime(last_success_at) IS NOT NULL),
    records_updated INTEGER NOT NULL CHECK (records_updated >= 0),
    details TEXT NOT NULL DEFAULT ''
);
