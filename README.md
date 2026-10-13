# PahadPath

PahadPath is a homestay discovery PWA for Uttarakhand. Travellers choose a place, date and interests, compare backend-ranked quieter destinations and listed local stays, review illustrative sample inventory, and save a non-binding demo request on this device. Crowd numbers are estimates, not live counts. The sample catalogue and inventory are not independently verified and do not represent reservations or guaranteed availability.

## Components

- `backend/`: FastAPI routes, Pydantic contracts, SQLite schema and seed loader, deterministic crowd scoring and destination ranking, itinerary fallback, mock inventory, and non-binding demo requests.
- `data/`: curated catalogue templates and clearly identified illustrative homestay inventory.
- `frontend/`: React + Vite PWA, responsive homestay discovery screens, offline saved-trip/request records, and shared data note. Tailwind is not installed; the existing project styles use CSS variables and stylesheets.
- `checkpoints/`: requirements-to-plan and plan-to-task traceability.

## Run locally (three lines)

1. Backend: `cd backend` → create/activate Python 3.11 environment → `pip install -r requirements.txt` → copy `.env.example` to `.env`.
2. Backend: `python -m app.db.seed` → `python -m uvicorn app.main:app --reload` → check `http://127.0.0.1:8000/api/health`.
3. Frontend: `cd frontend` → `npm install` → `npm run dev`; checks: backend `python -m pytest -q`, frontend `npm test` and `npm run build`.

The available workspace interpreter used during validation was Python 3.12.10. Python 3.11 is the target but has not yet been verified in this environment.

## Configuration and curated data

The backend reads only `backend/.env` plus process environment variables, with process environment taking precedence. Relative `DATABASE_PATH` values are resolved under `backend/`. Keep credentials in this file; never use a `VITE_*` secret. CORS accepts explicit origins only; the example origin is the local Vite dev server. LLM text generation defaults off.

`python -m app.db.seed` initializes the versioned SQLite schema and transactionally upserts the CSV rows by stable integer ID. The current templates are empty by design, so the catalogue and recommendation APIs return no invented places until records are reviewed and added. See [data/README.md](./data/README.md) for fields, provenance and consent requirements. Invalid headers, ranges, references, dates, duplicate IDs or missing provenance fail the import; corrections must be made in the CSVs.

## API surface

- `GET /api/health`
- `GET /api/destinations?region=&tag=`
- `GET /api/destinations/{id}` (includes reviewed alternative links)
- `GET /api/homestays?destination_id={id}`
- `POST /api/recommendations`
- `POST /api/itineraries`
- `GET /api/homestays/{id}/inventory?check_in=&check_out=`
- `POST /api/booking-requests` (creates a non-binding demo request only)

Errors use an `error` object with stable code, generic or safe message, and request ID. Pydantic validation errors do not echo rejected input. Requests return `X-Request-ID`; request logs include method, status, duration and correlation ID, not request bodies. Recommendation and itinerary endpoints use process-local SlowAPI limits of 30/minute and 10/minute; use a shared gateway/limiter before multi-worker deployment.

## Product rules enforced by the backend

- Crowd score: `round(.35 * popularity + .30 * date_demand + .20 * event_pressure + .15 * weather_visit_tendency)`, clamped to 0-100. Missing factors use 50 and add a note. Bands are Quiet 0-34, Moderate 35-59, Busy 60-79, Very busy 80-100. Responses are explicitly estimated and include `data_mode=curated_rule_estimate` and the destination review date.
- Date demand is a documented heuristic: start at 50, add 10 for a weekend, add 20 for a curated best month or subtract 10 for another month. If best months are unavailable, use neutral 50 and a note. It does not infer official holidays. Events are pressure 0-100 only when a reviewed event-calendar window covers the date; otherwise the factor is missing and uses 50.
- Recommendation score is `.45 * interest + .35 * quietness + .10 * travel + .10 * stay`; ranking runs on the server. Missing travel feasibility or unverified stay/budget data uses a disclosed neutral score. No travel duration is inferred from coordinates.
- The itinerary generator owns every ID, date, stay, budget check and day count. Optional generated content is limited to one short free-text sentence per day and cannot supply IDs or structured/factual fields. It is disabled unless configured and a provider adapter is injected; if unavailable or invalid, the deterministic template is returned.
- Contacts/booking links are stored and published only when curation records publication consent. Unknown price, contact, availability and travel time stay unknown.

## Booking and inventory boundaries

- The `demo_mock` inventory is for UI/testing only. Submitting a demo request does not reserve a room, reduce inventory, contact a host, or collect guest contact or payment details.
- The frontend's `services/api.ts` is the only module that calls the backend. Crowd levels and match ranking are computed server-side; the UI displays those returned values.
- Saved trips and demo-request receipts are stored locally with IndexedDB and remain available through `/saved` and `/saved/:id` when the device is offline.
- No authentication, host inventory management, payment processing, real booking confirmation, or external LLM provider is configured.

## Scope and known follow-ups

- Replace illustrative catalogue and inventory rows only after destination/stay data has been sourced, reviewed, and permissioned.
- The LLM adapter is optional and disabled unless explicitly configured; deterministic itinerary text remains the fallback.
- Run the application with curated seed data and test the browse → stay detail → sample dates → demo request → saved receipt flow before deployment. Deployment is not yet configured.
- Frontend `npm audit` reported zero vulnerabilities. A prior backend security review found no actionable findings. Python dependency vulnerability checking did not scan the full resolved transitive graph, so these results are not proof that dependencies are vulnerability-free.
