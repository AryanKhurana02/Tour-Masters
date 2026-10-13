PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS destinations (
    id INTEGER PRIMARY KEY CHECK (id > 0),
    name TEXT NOT NULL CHECK (length(trim(name)) BETWEEN 1 AND 120),
    district TEXT NOT NULL CHECK (length(trim(district)) BETWEEN 1 AND 120),
    region TEXT NOT NULL CHECK (length(trim(region)) BETWEEN 1 AND 120),
    description TEXT NOT NULL DEFAULT '',
    tags TEXT NOT NULL DEFAULT '',
    best_months TEXT NOT NULL DEFAULT '',
    popularity_score INTEGER CHECK (popularity_score BETWEEN 0 AND 100),
    source_label TEXT NOT NULL CHECK (length(trim(source_label)) > 0),
    source_url TEXT,
    reviewer TEXT NOT NULL CHECK (length(trim(reviewer)) > 0),
    reviewed_at TEXT NOT NULL CHECK (date(reviewed_at) IS NOT NULL),
    enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1))
);

CREATE INDEX IF NOT EXISTS idx_destinations_region_enabled
    ON destinations(region, enabled);

CREATE TABLE IF NOT EXISTS alternative_links (
    id INTEGER PRIMARY KEY CHECK (id > 0),
    source_destination_id INTEGER NOT NULL REFERENCES destinations(id) ON DELETE CASCADE,
    alternative_destination_id INTEGER NOT NULL REFERENCES destinations(id) ON DELETE CASCADE,
    match_tags TEXT NOT NULL DEFAULT '',
    travel_fit INTEGER CHECK (travel_fit BETWEEN 0 AND 100),
    source_label TEXT NOT NULL CHECK (length(trim(source_label)) > 0),
    source_url TEXT,
    reviewer TEXT NOT NULL CHECK (length(trim(reviewer)) > 0),
    reviewed_at TEXT NOT NULL CHECK (date(reviewed_at) IS NOT NULL),
    enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
    CHECK (source_destination_id <> alternative_destination_id),
    UNIQUE (source_destination_id, alternative_destination_id)
);

CREATE INDEX IF NOT EXISTS idx_alternative_links_source
    ON alternative_links(source_destination_id, enabled);

CREATE TABLE IF NOT EXISTS homestays (
    id INTEGER PRIMARY KEY CHECK (id > 0),
    destination_id INTEGER NOT NULL REFERENCES destinations(id) ON DELETE CASCADE,
    name TEXT NOT NULL CHECK (length(trim(name)) BETWEEN 1 AND 120),
    village TEXT NOT NULL DEFAULT '',
    nightly_min INTEGER CHECK (nightly_min IS NULL OR nightly_min >= 0),
    nightly_max INTEGER CHECK (nightly_max IS NULL OR nightly_max >= 0),
    currency TEXT,
    public_contact TEXT,
    booking_url TEXT,
    publish_contact INTEGER NOT NULL DEFAULT 0 CHECK (publish_contact IN (0, 1)),
    amenities TEXT NOT NULL DEFAULT '',
    source_label TEXT NOT NULL CHECK (length(trim(source_label)) > 0),
    source_url TEXT,
    reviewer TEXT NOT NULL CHECK (length(trim(reviewer)) > 0),
    reviewed_at TEXT NOT NULL CHECK (date(reviewed_at) IS NOT NULL),
    enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
    CHECK (nightly_min IS NULL OR nightly_max IS NULL OR nightly_min <= nightly_max),
    CHECK ((nightly_min IS NULL AND nightly_max IS NULL AND currency IS NULL)
        OR (nightly_min IS NOT NULL AND currency IS NOT NULL AND length(trim(currency)) = 3)),
    CHECK (publish_contact = 0 OR public_contact IS NOT NULL OR booking_url IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS idx_homestays_destination_enabled
    ON homestays(destination_id, enabled);

CREATE TABLE IF NOT EXISTS local_events (
    id INTEGER PRIMARY KEY CHECK (id > 0),
    destination_id INTEGER REFERENCES destinations(id) ON DELETE CASCADE,
    region TEXT NOT NULL CHECK (length(trim(region)) > 0),
    name TEXT NOT NULL CHECK (length(trim(name)) BETWEEN 1 AND 160),
    starts_on TEXT NOT NULL CHECK (date(starts_on) IS NOT NULL),
    ends_on TEXT NOT NULL CHECK (date(ends_on) IS NOT NULL),
    pressure INTEGER NOT NULL CHECK (pressure BETWEEN 0 AND 100),
    source_label TEXT NOT NULL CHECK (length(trim(source_label)) > 0),
    source_url TEXT,
    reviewer TEXT NOT NULL CHECK (length(trim(reviewer)) > 0),
    reviewed_at TEXT NOT NULL CHECK (date(reviewed_at) IS NOT NULL),
    enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
    CHECK (starts_on <= ends_on)
);

CREATE INDEX IF NOT EXISTS idx_local_events_window
    ON local_events(region, starts_on, ends_on, enabled);

CREATE TABLE IF NOT EXISTS event_calendar_reviews (
    id INTEGER PRIMARY KEY CHECK (id > 0),
    region TEXT NOT NULL CHECK (length(trim(region)) > 0),
    starts_on TEXT NOT NULL CHECK (date(starts_on) IS NOT NULL),
    ends_on TEXT NOT NULL CHECK (date(ends_on) IS NOT NULL),
    source_label TEXT NOT NULL CHECK (length(trim(source_label)) > 0),
    source_url TEXT,
    reviewer TEXT NOT NULL CHECK (length(trim(reviewer)) > 0),
    reviewed_at TEXT NOT NULL CHECK (date(reviewed_at) IS NOT NULL),
    enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
    CHECK (starts_on <= ends_on),
    UNIQUE (region, starts_on, ends_on)
);

CREATE INDEX IF NOT EXISTS idx_event_calendar_reviews_window
    ON event_calendar_reviews(region, starts_on, ends_on, enabled);
