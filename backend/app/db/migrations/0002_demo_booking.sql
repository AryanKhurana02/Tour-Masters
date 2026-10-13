CREATE TABLE IF NOT EXISTS homestay_inventory (
    id INTEGER PRIMARY KEY CHECK (id > 0),
    homestay_id INTEGER NOT NULL REFERENCES homestays(id) ON DELETE CASCADE,
    inventory_date TEXT NOT NULL CHECK (date(inventory_date) IS NOT NULL),
    total_units INTEGER NOT NULL CHECK (total_units >= 0),
    available_units INTEGER NOT NULL CHECK (available_units >= 0),
    inventory_mode TEXT NOT NULL CHECK (inventory_mode = 'demo_mock'),
    source_label TEXT NOT NULL CHECK (length(trim(source_label)) > 0),
    source_url TEXT,
    reviewer TEXT NOT NULL CHECK (length(trim(reviewer)) > 0),
    reviewed_at TEXT NOT NULL CHECK (date(reviewed_at) IS NOT NULL),
    enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
    CHECK (available_units <= total_units),
    UNIQUE (homestay_id, inventory_date)
);

CREATE INDEX IF NOT EXISTS idx_homestay_inventory_date
    ON homestay_inventory(homestay_id, inventory_date, enabled);

CREATE TABLE IF NOT EXISTS booking_requests (
    id TEXT PRIMARY KEY,
    client_request_id TEXT NOT NULL UNIQUE,
    homestay_id INTEGER NOT NULL REFERENCES homestays(id) ON DELETE RESTRICT,
    check_in TEXT NOT NULL CHECK (date(check_in) IS NOT NULL),
    check_out TEXT NOT NULL CHECK (date(check_out) IS NOT NULL),
    guest_count INTEGER NOT NULL CHECK (guest_count BETWEEN 1 AND 8),
    status TEXT NOT NULL CHECK (status = 'demo_submitted'),
    created_at TEXT NOT NULL CHECK (datetime(created_at) IS NOT NULL),
    CHECK (check_in < check_out),
    CHECK (julianday(check_out) - julianday(check_in) <= 30)
);

CREATE INDEX IF NOT EXISTS idx_booking_requests_created_at
    ON booking_requests(created_at);
