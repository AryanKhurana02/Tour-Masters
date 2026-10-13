# PahadPath — Complete MVP Blueprint and Implementation Plan

**Date:** 2026-10-12  
**Scope:** One-day, Uttarakhand-first trip-planner PWA  
**Status:** First-layer blueprint; workspace was empty at planning time

## Summary

Build a small, honest, end-to-end PWA that accepts a short trip request, recommends curated quieter look-alike destinations, explains backend-owned crowd estimates, presents only reviewed homestay facts, creates a validated day-wise itinerary, and lets the traveler reopen a saved plan offline. Keep the backend as the sole owner of crowd and recommendation scoring. Make the deterministic path complete before enabling any optional text-only LLM.

Execution path: **curated data → API contracts and backend rules → mobile-first frontend → offline save/reopen → end-to-end acceptance**. Use a modular FastAPI application with SQLite and a React/Vite/TypeScript PWA. Use curated tag overlap rather than embeddings; no new dependencies or external providers are assumed.

## First Layer: Component Blueprint

| Component | Owns | Contract / boundary | MVP implementation |
|---|---|---|---|
| Curated data and maintenance | Destination, alternative, event, and homestay records; provenance; seed validation | Supplies reviewed records only; unknown facts remain null/unknown | SQLite schema plus versioned CSV seed files and deterministic loader |
| Backend API | HTTP routes, Pydantic v2 models, stable errors, CORS, rate limits | `/api/*` JSON contracts; routes call services/repositories, not formulas | FastAPI modular monolith; slowapi on recommendation/itinerary routes |
| Crowd estimation | Normalize factors, impute missing inputs, calculate score/band, explain provenance | Returns score, level, components, notes, `data_mode`, `reviewed_at` | Pure deterministic Python service; no frontend score calculations |
| Recommendation | Eligibility, interest/quietness/travel/stay fit, ranking and reasons | Known IDs only; relaxed pool gets explicit warning | Curated alternative links and tag overlap; no embedding/model package |
| Itinerary | Template schedule, IDs/budget/day-count validation, optional text-generation adapter | LLM output is untrusted text; all factual data resolved from SQLite | Template is complete default; optional LLM disabled unless configured |
| Frontend PWA | Request, results, estimate explanation, stays, itinerary, saved trips | Displays backend values; client validation is UX only | React, Vite, TypeScript, Tailwind, React Router, Framer Motion, Lucide |
| Offline experience | App-shell caching, saved trip persistence/reopen | Explicitly saved validated plan and essential linked data; no silent overwrite | vite-plugin-pwa service worker and idb/IndexedDB |
| Quality, privacy, operations | Tests, demo readiness, secret handling, honest claims | Secrets never reach Vite/client; failures stay visible | pytest, Vitest, backend `.env`, manual offline acceptance |

### Dependency and ownership flow

1. Curators validate provenance and seed records.
2. API validates a request and calls services/repositories.
3. Backend calculates crowd and ranking outputs and returns typed responses.
4. Frontend displays results and submits only user choices/constraints.
5. Backend generates or templates the itinerary, then validates IDs and constraints.
6. Frontend saves that validated response and required referenced records in IndexedDB; the service worker caches the shell separately.

### MVP non-goals

No login/profile/host dashboard, booking/payments/live availability, observed or predictive live crowd counts, semantic embeddings/vector database, required external weather service, offline map tiles/routing, native app, microservices, or deployment-specific infrastructure. Coordinates may be shown as curated data; route/travel time is never inferred from coordinates.

## Technical Context

**Runtime:** Python 3.11; TypeScript with React and Vite.  
**Allowed dependencies:** React, Vite, TypeScript, Tailwind, Framer Motion, Lucide, React Router, idb, vite-plugin-pwa, Vitest; FastAPI, Pydantic v2, SQLite, slowapi, pytest; optional server-side LLM only. No additions without approval.  
**Storage:** SQLite for curated server data; IndexedDB via `idb` for saved trips.  
**API:** FastAPI JSON endpoints under `/api`; ISO `YYYY-MM-DD`; stable integer catalogue IDs.  
**Testing:** pytest for services/schema/API; Vitest for frontend/UI/storage; manual airplane-mode acceptance.  
**Constraints:** one-day MVP; mobile-first from 360px; API owns scores; secrets backend-only; honest estimates; saved trip works offline.

### API Contract

- `GET /api/health` → service health.
- `GET /api/destinations?region=&tag=` → filtered curated catalogue.
- `GET /api/destinations/{id}` → destination detail and curated alternatives.
- `GET /api/homestays?destination_id={id}` → enabled reviewed stays.
- `POST /api/recommendations` → validated trip request and ranked records with reasons/crowd breakdown.
- `POST /api/itineraries` → selected IDs/constraints; template or validated optional-LLM itinerary.

Use 422 for schema/submitted-plan validation; 404 for missing resource lookup; 400 for an impossible business request; 500 for unexpected failures (details only in server logs). Provider failure uses deterministic fallback, not a 503, when the core path remains available.

Recommendation request: region, optional `start_destination_id`, `start_date`, `days` (1–7), bounded interests, optional `budget_per_night_max`, `avoid_crowds`, and optional curated-feasibility constraint. Do not use unverified travel time. Response: request ID, `data_mode`, destination ID/name, rank score, crowd score/level/components/notes/review date, fit components, reasons and any relaxed-pool warning.

Itinerary request: start date, 1–7 days, non-empty known destination IDs, interests, optional per-night budget and optional LLM opt-in. Response: generation mode, exactly requested dated days, allowed time blocks, destination/stay IDs, backend-authored text/reasons, crowd snapshot and warnings. Names, contacts, prices, availability and route facts must come from reviewed records or be omitted; never accept them as LLM-sourced facts.

## Product Rules and Data Contracts

### Crowd estimate (backend only)

```text
score = clamp(round(0.35 * popularity + 0.30 * date_demand
                  + 0.20 * event_pressure + 0.15 * weather_visit_tendency), 0, 100)
```

Factors are 0–100. Missing factor contributes **50** and adds a specific note. Event pressure is zero only if the period was checked and no event found; unknown/unverified event data uses 50 plus a note. Weather is a visit-tendency factor, not a safety score; with no verified input, use 50 and say weather was unavailable. Preserve `data_mode="curated_rule_estimate"` and non-empty `reviewed_at` from curated data. Always display **estimated**, number, text band, source and review detail; never colour alone.

| Score | Label |
|---:|---|
| 0–34 | Quiet |
| 35–59 | Moderate |
| 60–79 | Busy |
| 80–100 | Very busy |

Date demand uses deterministic documented month/season, weekend and available curated holiday rules. Do not imply an official calendar unless one is actually sourced and reviewed.

### Destination ranking (backend only)

```text
rank = 0.45 * interest_fit + 0.35 * quietness_fit
     + 0.10 * travel_fit + 0.10 * stay_fit
quietness_fit = 100 - crowd_score
```

Factors are 0–100. Interest fit is overlap of requested and curated tags. Travel fit is disclosed curated feasibility/broad-distance score only, never a travel duration. Stay fit uses reviewed stays and disclosed budget overlap; absent price is unknown, not zero. Filter ineligible/disabled/unreviewed alternatives before scoring. If candidate pool is broadened, state that in response and UI.

### SQLite entities and curation contract

- `destinations`: stable ID, name, district/region, nullable verified coordinates, description, tags, best months, baseline popularity, source label, reviewer/review date, enabled flag.
- `alternative_links`: source/alternative destination FKs, match tags, reviewer notes/metadata, enabled flag, unique pair, no self-links.
- `homestays`: destination FK, name/village, nullable price range/currency, consented public contact/booking link, amenities, source/verification metadata, enabled/publish-contact flags. Contact unpublished by default.
- `local_events` (optional): optional destination FK, date interval, bounded demand pressure, source/review metadata, enabled flag. Missing/unverified data means 50 + note, not assumed absence.

Enforce FKs/checks for ranges, dates, prices and booleans. Plan for ~15–20 reviewed destinations and 8–10 stays; these are targets, not fabricated content. Seed validation stops on duplicates, broken FKs, invalid values or missing provenance. No sample record is shown as verified without a real source.
## User Journey and Screens

1. **Trip request:** starting place or region, dates/day count, interest tags, stay budget and crowd preference; labeled controls and inline validation.
2. **Recommendations:** ranked alternatives, estimated crowd number and word, breakdown/notes, reviewed date, rank reasons, optional stay facts, relaxed-filter warnings.
3. **Destination/stay detail:** API-provided facts only, explicit unavailable states and source/review dates; no generated booking claims.
4. **Itinerary:** requested day/date count, time blocks, destination/stay cards, generation mode and constraints/warnings.
5. **Saved trips/offline:** saved timestamp, offline-ready summary, reopen validated itinerary and included place/stay/contact details; show offline state and disable network-only generation clearly.

## Design System: Topographic Dawn

- Tokens: paper `#F6F2EA`, card `#FBF8F2`, ink `#1B1F1D`, soft `#5C625E`, pine `#1F3A32`, saffron `#C9972F` (only accent), hairline `#DDD5C5`.
- Crowd pairs: Quiet `#DDE7D8/#2F4F3A`; Moderate `#F3E2B8/#7A5A12`; Busy `#F0D2C6/#8A3F22`; Very busy `#E8BFAE/#6F2D16`. Always show word and number as well as color.
- Fraunces headings, Inter body, no text below 12px, 16px card radius, hairline border, no default shadow (hover only).
- Contour SVG around 5% and paper grain around 3%, decorative and never impair contrast.
- Mobile-first at 360px; minimum 44px tap targets; semantic controls, labels, visible focus and readable contrast.
- Framer Motion only opacity/position; 150–400ms, optional 900ms hero dial, one hero animation per screen, honor reduced motion.

## Offline and Failure Strategy

- Service worker caches built app shell/assets; API responses are not authoritative saved state.
- On explicit Save, store complete validated itinerary, saved timestamp, and essential referenced destination/stay fields in IndexedDB. Never silently replace saved snapshot with newer data.
- Offline reload opens shell and saved plans; network-dependent actions show a clear offline message. Coordinates are informational; offline maps/routing are not promised.
- Missing weather/event input: neutral 50 and note. LLM disabled, timeout, failure, malformed JSON or invalid ID: deterministic template with generation-mode label. Empty alternatives: empty or explicitly relaxed result, never invented names. Missing SQLite/seed: fail fast; no fabricated demo records.

## Security, Privacy, and Operations

- Secrets only in `backend/.env`; commit blank `.env.example`, ignore `.env` and SQLite/build outputs. Load configuration server-side with approved stack; never use `VITE_*` for secrets. Document the dependency-free `.env` mechanism before implementation; no dotenv package without approval.
- Restrict CORS to configured origins. Validate dates, days, IDs, list sizes, interests, budgets and body sizes server-side. Apply slowapi limits to recommendations/itinerary (especially optional LLM).
- No login or server profiles. Publish host contact only with consent. Minimize LLM context; never send secrets/private identifiers. Log request ID, duration and failure category, not keys/unnecessary user content.
- Crowd estimates are not road/trail/weather safety advice. Do not assert closures/access without reviewed source.

## Constitution Check

| Principle / constraint | Result | Plan consequence |
|---|---|---|
| Backend owns scores | Pass | Scoring/ranking only in backend; client renders response. |
| Estimates transparent, never live claims | Pass | Exact formula, neutral missing value + note, labels, mode, review date and breakdown. |
| LLM optional and text-only | Pass | Template first; backend resolves IDs/facts and validates. |
| Do not invent facts | Pass | Curated catalog; unknown price/contact/time stays unknown; seed gate. |
| Secrets backend-only | Pass | Backend `.env`, ignored; no frontend provider calls/secrets. |
| Approved stack only | Pass | Curated tags instead of embedding packages; no additions without approval. |
| Offline scope is saved trip, not maps | Pass | App shell + IndexedDB snapshot. |
| Calm, accessible, mobile-first UI | Pass | Tokens, typography, minimums, reduced motion and estimate semantics are acceptance criteria. |
| Workspace currently empty | Pass with planning constraint | Scaffold deliberate structure; do not assume existing code/data. |

## Applied Guidelines

No project-specific `skills/guidelines/` directory or migration guidelines were present in the scanned workspace. This blueprint applies the user-supplied stack, scoring, validation, privacy, offline and design rules plus the supplied Low-Level Design. Explicit current user constraints take precedence over older stack suggestions in supporting materials.

## Implementation Steps and Tasks

### Phase 1 — Setup

**Status:** Setup scaffold complete; user-facing UI remains intentionally deferred. Backend tests and live HTTP health checks pass, frontend Vitest/build pass, and npm audit reported zero vulnerabilities. Python checks used 3.12.10; Python 3.11 compatibility is not yet verified.

#### Step 1.1 — Establish the approved monorepo skeleton
- **Requirements:** REQ-012, REQ-013
- **Description:** Create frontend/backend/data layout, manifests, tests, environment examples and ignore rules. Keep both apps runnable independently; add no unapproved tool/package.

- [x] T001 [Plan:1.1] Create `frontend/src/{components,pages,services,types,assets}`, `frontend/public`, `backend/app/{api,schemas,services,repositories,db,integrations}`, `backend/tests`, `data`, and `checkpoints` directories.
- [x] T002 [P] [Plan:1.1] Initialize `frontend/package.json`, Vite/TypeScript entry/config files and scripts with approved frontend packages only.
- [x] T003 [P] [Plan:1.1] Add `backend/requirements.txt` and `backend/app/main.py` using approved Python packages and health endpoint placeholder.
- [x] T004 [Plan:1.1] Add root `.gitignore` for `backend/.env`, SQLite files, build output, `node_modules`, Python caches and generated artifacts; add blank `backend/.env.example`.

### Phase 2 — Foundational contracts and data

**Status:** Complete. SQLite schema/versioning, transactional curated-data loader, API schemas/configuration, request-ID errors, CORS and endpoint limits are implemented and covered by 59 passing backend tests. Pylance reports no backend errors; live health/catalogue/recommendation smoke checks pass. A read-only backend security review found no actionable issues. Python dependency CVE checking was only a best-effort model-knowledge check, not a complete advisory scan. Curated CSVs remain header-only pending verified source data.

#### Step 2.1 — Define validated curated data and persistence
- **Requirements:** REQ-001, REQ-006, REQ-012
- **Description:** Implement reviewed-record schema, seed format, SQLite constraints and fail-fast seed checks before recommendation code consumes data.

- [x] T005 [Plan:2.1] Implement `backend/app/db/schema.sql` for destinations, alternative links, homestays and optional events with FKs, uniqueness, checks and indexes.
- [x] T006 [Plan:2.1] Implement `backend/app/db/database.py` for explicit SQLite initialization, FK enforcement, connections and actionable missing-database errors.
- [x] T007 [P] [Plan:2.1] Define reviewed seed headers/rules in `data/README.md` and add empty/template CSVs without invented destination records.
- [x] T008 [Plan:2.1] Implement `backend/app/db/seed.py` to load curated CSVs transactionally and fail on duplicates, missing provenance, invalid ranges/coordinates or broken FKs.
- [x] T009 [Plan:2.1] Add `backend/tests/test_seed.py` for duplicate IDs, invalid references, missing metadata, valid unknowns and deterministic re-seeding.

#### Step 2.2 — Freeze API shapes, configuration and errors
- **Requirements:** REQ-002, REQ-003, REQ-007, REQ-008, REQ-012, REQ-013
- **Description:** Publish request/response schemas and shared error semantics before client/server integration. Backend-only config uses approved stack; no guessed fields.

- [x] T010 [Plan:2.2] Define request/response models in `backend/app/schemas/{destination,recommendation,itinerary}.py` using constrained Pydantic v2 fields and score/ID/date shapes.
- [x] T011 [Plan:2.2] Implement `backend/app/config.py` for server-only config, CORS origins, feature flags and fail-fast invalid settings without exposing secrets.
- [x] T012 [Plan:2.2] Implement `backend/app/api/errors.py`, request-ID-safe error mapping and route registration/CORS in `backend/app/main.py`.
- [x] T013 [Plan:2.2] Configure slowapi in `backend/app/main.py` and apply documented limits to recommendation/itinerary endpoints; do not rate-limit health.

### Phase 3 — US1 (P1): Find estimated quieter alternatives

**Status:** Backend catalogue, crowd estimates, date-demand heuristic, server-side ranking and recommendation routes/tests implemented and verified. Live empty-catalogue behavior is correct; no reviewed production catalogue records have been supplied.

#### Step 3.1 — Serve curated catalogue records
- **Requirements:** REQ-001, REQ-006
- **Description:** Expose only enabled curated records with provenance; give explicit empty/not-found responses.

- [x] T014 [US1] [Plan:3.1] Implement `backend/app/repositories/destination_repository.py` for destination, alternative, event and homestay parameterized SQLite queries.
- [x] T015 [US1] [Plan:3.1] Implement `backend/app/api/destinations.py` for destination list/detail and `GET /api/homestays?destination_id=...`.
- [x] T016 [P] [US1] [Plan:3.1] Add `backend/tests/test_catalogue_api.py` for filters, empty catalog, missing IDs, disabled records and destination-bound stays.

#### Step 3.2 — Calculate transparent crowd estimates
- **Requirements:** REQ-002, REQ-003
- **Description:** Implement exact weighted rule, bounds, bands, neutral missing values/notes, response provenance; distinguish weather tendency from safety.

- [x] T017 [US1] [Plan:3.2] Implement `backend/app/services/crowd_score.py` with weights, clamp, band boundaries, missing notes, `curated_rule_estimate`, reviewed timestamp.
- [x] T018 [P] [US1] [Plan:3.2] Add `backend/tests/test_crowd_score.py` for formula, rounding, bounds, band boundaries, missing=50 notes and metadata.
- [x] T019 [US1] [Plan:3.2] Implement `backend/app/services/date_demand.py` for documented season/weekend/curated-calendar rules and explicit unknown-calendar handling.

#### Step 3.3 — Rank alternatives on the backend
- **Requirements:** REQ-004, REQ-005, REQ-006
- **Description:** Filter known, enabled, reviewed links; apply prescribed ranking; explain tags, quietness and practical-fit limitations.

- [x] T020 [US1] [Plan:3.3] Implement `backend/app/services/recommendation.py` for filters, tag interest fit, quietness, curated travel feasibility, stay/budget fit, weighted rank and reasons.
- [x] T021 [P] [US1] [Plan:3.3] Add `backend/tests/test_recommendation.py` for weights/order, unknown price, disabled/unreviewed exclusion and relaxed-pool warnings.
- [x] T022 [US1] [Plan:3.1,3.2,3.3] Implement `backend/app/api/recommendations.py` and register `POST /api/recommendations`; return validated catalog IDs and explanations.
- [x] T023 [US1] [Plan:3.1,3.2,3.3] Add `backend/tests/test_recommendations_api.py` for malformed requests, unknown start IDs, stable contract, empty/broadened pool and no fabricated fallback.
### Phase 4 — US2 (P1): Generate a valid itinerary

**Status:** Deterministic itinerary generation and structural validation are implemented and tested. Text-only provider interface/fallback is ready for a provider choice; no external LLM is configured or called.

#### Step 4.1 — Build and validate deterministic itinerary first
- **Requirements:** REQ-007, REQ-008, REQ-009
- **Description:** Complete the journey without an LLM. Resolve names/factual fields from SQLite; enforce selected IDs, stay relationship, exact day count, date order, allowed blocks and budget semantics.

- [x] T024 [US2] [Plan:4.1] Implement `backend/app/services/itinerary_validation.py` for destination/stay IDs, duplicate stops, stay association, dates/day count, allowed blocks, budgets and prohibited claims.
- [x] T025 [US2] [Plan:4.1] Implement `backend/app/services/itinerary.py` deterministic template from reviewed records, with stable response and `rule_fallback` mode.
- [x] T026 [P] [US2] [Plan:4.1] Add `backend/tests/test_itinerary.py` for valid schedules, unknown IDs, bad day/date, unrelated stays, budgets and unsupported facts.
- [x] T027 [US2] [Plan:4.1] Implement `backend/app/api/itineraries.py` for `POST /api/itineraries` and documented business errors.

#### Step 4.2 — Add optional text generation behind validated fallback
- **Requirements:** REQ-008, REQ-012
- **Description:** Optional provider-neutral adapter may suggest text, never scores, IDs, costs, contacts, availability or travel facts. Disabled by default; do not add an SDK without approval.

- [x] T028 [US2] [Plan:4.2] Define optional text-only adapter in `backend/app/integrations/llm_client.py`, feature-gated by backend config and minimal curated context.
- [x] T029 [US2] [Plan:4.2] Route optional output through schema parsing, catalog/factual validation and deterministic fallback in `backend/app/services/itinerary.py`.
- [x] T030 [P] [US2] [Plan:4.2] Add `backend/tests/test_llm_fallback.py` for disabled provider, timeout/failure, malformed response, unknown ID and valid text-only output.

### Phase 5 — US3 (P1): Complete the mobile-first trip-planning UI

#### Step 5.1 — Establish shared types, tokens and request flow
- **Requirements:** REQ-010, REQ-011, REQ-013
- **Description:** Build design foundation and typed API client; client validation aids input only, never scores or invents data.

- [ ] T031 [P] [US3] [Plan:5.1] Define API-aligned types in `frontend/src/types/api.ts` for destinations, crowd, recommendations, stays and itinerary.
- [ ] T032 [P] [US3] [Plan:5.1] Configure Topographic Dawn tokens, typography, contour/grain and reduced-motion-safe styles in `frontend/tailwind.config.ts` and `frontend/src/styles.css`.
- [ ] T033 [US3] [Plan:5.1] Implement typed API functions and visible network errors in `frontend/src/services/api.ts`; use only public backend base URL.
- [ ] T034 [US3] [Plan:5.1] Implement `frontend/src/pages/HomePage.tsx` and `frontend/src/components/TripRequestForm.tsx` with labeled controls, mobile layout, supported validation/loading/error states.
- [ ] T035 [US3] [Plan:5.1] Wire `frontend/src/App.tsx` and React Router for home/results/itinerary/saved trips and not-found.

#### Step 5.2 — Render recommendations, estimates and curated stays
- **Requirements:** REQ-002, REQ-003, REQ-004, REQ-005, REQ-006, REQ-011
- **Description:** Display backend rank, provenance and missing notes; no score derivation or color-only labels.

- [ ] T036 [US3] [Plan:5.2] Implement `frontend/src/components/CrowdBreakdown.tsx` with score, estimate word, band, components, notes, mode and review date.
- [ ] T037 [US3] [Plan:5.2] Implement DestinationCard, RecommendationList and HomestayCard with API reasons, unknown states and no unsupported claims.
- [ ] T038 [US3] [Plan:5.2] Implement `frontend/src/pages/ResultsPage.tsx` and detail view with explicit relaxed-filter warnings.
- [ ] T039 [P] [US3] [Plan:5.2] Add Vitest coverage for crowd labels, notes, unknown stay fields, reasons and accessible labels.

#### Step 5.3 — Render validated itineraries and recoverable errors
- **Requirements:** REQ-007, REQ-008, REQ-011
- **Description:** Show exact backend day/date structure, generation mode and warnings.

- [ ] T040 [US3] [Plan:5.3] Implement `frontend/src/pages/ItineraryPage.tsx` and `frontend/src/components/ItineraryDay.tsx` for date/time blocks, stays, warnings, mode and save action.
- [ ] T041 [P] [US3] [Plan:5.3] Add Vitest coverage for itinerary rendering, fallback label, validation errors and loading/retry states.

### Phase 6 — US4 (P1): Save and reopen a trip offline

#### Step 6.1 — Cache shell and persist validated snapshots
- **Requirements:** REQ-009, REQ-010
- **Description:** Cache app shell and separately persist the explicitly saved validated plan with essential referenced data. Do not treat cached API response as a saved trip.

- [ ] T042 [Plan:6.1] Configure `frontend/vite.config.ts` and `frontend/public/manifest.webmanifest` for app-shell cache and navigation fallback, not API cache-as-truth.
- [ ] T043 [Plan:6.2] Implement `frontend/src/services/offlineStore.ts` with idb versioning, atomic save/read/list/delete, saved time and referenced-data snapshot.
- [ ] T044 [Plan:6.2] Implement SavedTripsPage, SaveForOfflineButton and OfflineBanner for reopen, storage errors, offline state and network-action messaging.
- [ ] T045 [P] [Plan:6.2] Add Vitest coverage for IndexedDB save/read, snapshot completeness, versioning, missing trip and offline states.
- [ ] T046 [Plan:6.1,6.2] Execute browser acceptance: generate → save → refresh → disable network → reopen → verify only curated referenced contact/coordinates/warnings.

### Phase 7 — Polish and end-to-end acceptance

#### Step 7.1 — Verify journeys, privacy and failure behavior
- **Requirements:** REQ-002, REQ-003, REQ-005, REQ-007, REQ-008, REQ-009, REQ-012, REQ-013
- **Description:** Prove the deterministic full flow, explicit failures, secret boundaries and offline behavior on target browser/device.

- [x] T047 [Plan:7.1] Add `backend/tests/test_api_flow.py` for health/catalog/recommendations/itinerary/errors/rate-limits/no-LLM.
- [ ] T048 [Plan:7.1] Add frontend Vitest flow coverage for request → results → itinerary → save and visible errors with contract fixtures.
- [ ] T049 [Plan:7.1] Review visible destination/stay source, review date, consent, unknowns and unsupported claims; block unverified demo data.
- [ ] T050 [Plan:7.1] Verify secrets absent from frontend bundle, requests, logs and committed files; review CORS, input bounds and rate limits.
- [ ] T051 [Plan:7.1] Run pytest, npm test/build; manually validate 360px, keyboard/focus, reduced motion and airplane-mode reopen.

#### Step 7.2 — Freeze demo and handoff
- **Requirements:** REQ-001 through REQ-013
- **Description:** Document reproducible setup, seed/config, API behavior, limitations and demo checklist. Freeze scope rather than add unapproved dependencies/features.

- [x] T052 [Plan:7.2] Write root `README.md` with component map, runtime prerequisites, three-line run steps, seed/env instructions, tests/build and limitations.
- [ ] T053 [Plan:7.2] Verify clean start and three-minute demo twice from fresh local database; record results against Done-when list.

### Execution order and critical dependencies

1. T001–T004 establish skeleton; frontend/backend manifest work may parallel after directories exist.
2. T005–T013 establish schema, seed validation and API contracts. Do not integrate against guessed fields.
3. T014–T023 deliver discovery; crowd/rank tests gate UI score claims.
4. T024–T030 complete no-LLM itinerary before optional adapter.
5. T031–T041 implement UI against frozen contracts; fixtures are dev-only, not production fallback data.
6. T042–T046 depend on validated response shape; test after explicit save.
7. T047–T053 gate release/demo. One-day schedule is a prioritization target, not grounds to skip data review or offline test.

## Project Structure

```text
pahadpath/
  README.md
  .gitignore
  data/{README.md,destinations.csv,alternative_links.csv,homestays.csv,local_events.csv}
  backend/
    .env.example
    requirements.txt
    app/
      main.py
      config.py
      api/{errors.py,destinations.py,recommendations.py,itineraries.py}
      schemas/{destination.py,recommendation.py,itinerary.py}
      services/{crowd_score.py,date_demand.py,recommendation.py,itinerary.py,itinerary_validation.py}
      repositories/destination_repository.py
      db/{schema.sql,database.py,seed.py}
      integrations/llm_client.py       # optional, disabled by default
    tests/
  frontend/
    package.json
    vite.config.ts
    tailwind.config.ts
    public/manifest.webmanifest
    src/{main.tsx,App.tsx,styles.css}
    src/types/api.ts
    src/services/{api.ts,offlineStore.ts}
    src/components/{TripRequestForm.tsx,CrowdBreakdown.tsx,DestinationCard.tsx,RecommendationList.tsx,HomestayCard.tsx,ItineraryDay.tsx,OfflineBanner.tsx,SaveForOfflineButton.tsx}
    src/pages/{HomePage.tsx,ResultsPage.tsx,ItineraryPage.tsx,SavedTripsPage.tsx}
    tests/
  checkpoints/{spec-to-plan.yaml,plan-to-tasks.yaml}
```

## Run Guidance (three lines)

1. Backend: `cd backend` → activate a Python 3.11 environment → `pip install -r requirements.txt`.
2. Backend: `python -m uvicorn app.main:app --reload` (health check: `http://127.0.0.1:8000/api/health`).
3. Frontend: `cd frontend` → `npm install` → `npm run dev`; validate with `npm test` and `npm run build`.
## Requirement Mapping

| REQ ID | Description | Plan Items | Implementation Evidence |
|---|---|---|---|
| REQ-001 | Curated destination catalogue and provenance | 2.1, 3.1, 7.2 | `backend/app/db/schema.sql`, `seed.py`, repository, `data/` |
| REQ-002 | Backend-owned weighted crowd estimate and components | 2.2, 3.2, 3.3, 5.2, 7.1 | `crowd_score.py`, response schema, crowd/API tests |
| REQ-003 | Correct bands, estimated wording, missing notes, mode and review date | 2.2, 3.2, 5.2, 7.1 | crowd service, CrowdBreakdown.tsx, scoring/UI tests |
| REQ-004 | Backend rank uses prescribed weighted formula | 3.3 | `recommendation.py`, ranking tests |
| REQ-005 | Known quieter look-alikes, reasons and explicit relaxed filters | 3.1, 3.3, 5.2, 7.1 | recommendation API/service, cards and tests |
| REQ-006 | Curated stays only; unknown price/contact/availability not invented | 2.1, 3.1, 3.3, 5.2 | homestay schema/seed, HomestayCard.tsx, provenance review |
| REQ-007 | Itinerary respects known IDs, dates, requested days and budget | 2.2, 4.1, 5.3, 7.1 | itinerary schemas/service/validator/API and tests |
| REQ-008 | Optional text-only LLM, validation and deterministic fallback | 2.2, 4.1, 4.2, 5.3, 7.1 | LLM adapter/service/fallback tests and UI mode |
| REQ-009 | Save/reopen validated itinerary plus essential data offline | 4.1, 6.1, 7.1 | offlineStore.ts, SavedTripsPage.tsx, offline acceptance |
| REQ-010 | Installable PWA shell and honest offline scope | 5.1, 6.1 | Vite PWA config, web manifest, offline banner |
| REQ-011 | Topographic Dawn accessible responsive UI and motion constraints | 5.1, 5.2, 5.3, 7.1 | Tailwind tokens/styles/components and UI checks |
| REQ-012 | Backend-only secrets, validation, CORS/rate limits and privacy | 1.1, 2.1, 2.2, 4.2, 7.1 | ignore/env/config/main, API and security checks |
| REQ-013 | Approved stack, executable verification and reproducible demo | 1.1, 2.2, 7.1, 7.2 | manifests, test suites, README and clean-start demo |

## Done When

- A traveler enters supported preferences and receives reviewed known alternatives with reasons and backend-computed crowd/rank details.
- Every crowd result says **estimated**, shows score/band, missing-input notes, `data_mode="curated_rule_estimate"`, and `reviewed_at`.
- Backend applies exact crowd/rank weights and thresholds; frontend contains no score calculation.
- Stay, route, price, contact and availability claims come only from reviewed/consented data; unknown stays unknown.
- Itinerary has exactly requested days and known IDs; without LLM key a labeled template succeeds; invalid LLM output cannot bypass validation.
- Saved trip reopens after refresh with network disabled and includes only the saved plan and essential referenced data.
- At 360px UI meets typography/tap-target requirements, has non-color-only semantics and honors reduced motion.
- No backend secret reaches frontend; automated tests/build and manual offline acceptance pass.
- Clean startup and documented demo run twice without fabricated seed data or unapproved dependencies.

## Complexity Tracking

No constitution violations. No extra runtime or data infrastructure is planned. LLM/weather integrations remain outside the MVP critical path.