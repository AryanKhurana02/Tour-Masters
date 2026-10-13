# Curated seed data

The current CSVs contain **synthetic demo fixtures** so the interface and complete homestay discovery flow can be exercised. Every record is labelled `DEMO FIXTURE - NOT VERIFIED`; the places, descriptions, scores, links, stays, and review dates are illustrative and are not travel guidance or real listings. The UI must keep a prominent end-of-page data note visible whenever these fixtures are loaded.

Before any real-user or production launch, replace the fixture rows with facts checked against verifiable sources, record a real reviewer and review date, and collect any required contact-publication consent. Never present fixture crowd estimates as observed counts, or fabricate real prices, availability, contact details, or travel times.

`python -m app.db.seed` creates `backend/pahadpath.db` and imports the CSV rows as an idempotent upsert by stable integer ID. All files are applied in one SQLite transaction; an invalid row or foreign key rolls the import back. Removed CSV rows are not deleted from the database: disable a record explicitly with `enabled=0` and retain its provenance.

Columns:

- `destinations.csv`: `id,name,district,region,description,tags,best_months,popularity_score,source_label,source_url,reviewer,reviewed_at,enabled`. Separate tags/month numbers with semicolons. Leave `popularity_score` empty when unknown.
- `alternative_links.csv`: `id,source_destination_id,alternative_destination_id,match_tags,travel_fit,source_label,source_url,reviewer,reviewed_at,enabled`. `travel_fit` is curated feasibility, not a duration or distance.
- `homestays.csv`: `id,destination_id,name,village,nightly_min,nightly_max,currency,public_contact,booking_url,publish_contact,amenities,source_label,source_url,reviewer,reviewed_at,enabled`. Prices are integer amounts in the stated three-letter currency. Do not put a contact or booking URL in this file unless explicit publication consent is recorded with `publish_contact=1`.
- `homestay_inventory.csv`: `id,homestay_id,inventory_date,total_units,available_units,inventory_mode,source_label,source_url,reviewer,reviewed_at,enabled`. This is **synthetic demo-only inventory**, not host-provided stock. `inventory_mode` must be `demo_mock`; unit counts and dates must never be presented as real availability. A submitted demo request is non-binding and does not reserve or decrement units.
- `local_events.csv`: `id,destination_id,region,name,starts_on,ends_on,pressure,source_label,source_url,reviewer,reviewed_at,enabled`.
- `event_calendar_reviews.csv`: `id,region,starts_on,ends_on,source_label,source_url,reviewer,reviewed_at,enabled`. A reviewed coverage row is required before absence of an event can be treated as zero pressure.

Dates must be ISO `YYYY-MM-DD`; score fields are integers from 0 to 100; booleans are `0` or `1`. Empty optional values stay unknown, not zero.
