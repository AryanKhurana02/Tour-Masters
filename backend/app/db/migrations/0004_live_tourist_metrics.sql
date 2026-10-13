PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS live_tourist_metrics (
    id INTEGER PRIMARY KEY CHECK (id > 0),
    destination_id INTEGER NOT NULL REFERENCES destinations(id) ON DELETE CASCADE,
    timestamp TEXT NOT NULL CHECK (datetime(timestamp) IS NOT NULL),
    live_crowd_index INTEGER NOT NULL CHECK (live_crowd_index BETWEEN 0 AND 100),
    data_source TEXT NOT NULL CHECK (length(trim(data_source)) > 0),
    UNIQUE (destination_id, timestamp)
);

CREATE INDEX IF NOT EXISTS idx_live_tourist_metrics_destination_timestamp
    ON live_tourist_metrics(destination_id, timestamp DESC);