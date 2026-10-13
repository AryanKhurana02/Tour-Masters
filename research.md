# PahadPath Blueprint — Decisions and Assumptions

**Date:** 2026-10-12

These choices make the supplied brief and Low-Level Design executable without adding dependencies or fabricating destination facts.

## Decisions

### Tag-based matching, not embeddings
- **Decision:** MVP interest fit uses curated tag overlap and reviewed alternative links.
- **Rationale:** No embedding/model package is approved; the Low-Level Design calls tags the MVP and embeddings a future enhancement. This is deterministic and explainable.
- **Alternative:** Sentence embeddings/LLM similarity from a diagram or older summary. Deferred pending dependency approval and data/evaluation need.

### Template itinerary before optional LLM
- **Decision:** Complete and test deterministic itinerary generation first; keep LLM off unless explicitly configured.
- **Rationale:** Core demo survives missing keys, provider failures and invalid responses; LLM can produce text only.
- **Alternative:** Making a provider mandatory. Rejected as brittle and inconsistent with fallback requirement.

### Missing weather/event data stays explicit
- **Decision:** Without reviewed input, use 50 and emit a specific note. Weather integration is off the one-day critical path. Event pressure is zero only after a documented check finds no event.
- **Rationale:** No provider, source, or credentials were supplied; missing factors must be neutral and explained.
- **Alternative:** Calling data live or assuming missing events mean none. Rejected as misleading.

### No fabricated seed facts
- **Decision:** Create seed format and validator only; load destination/stay facts once sourced and reviewed.
- **Rationale:** Workspace is empty and the brief forbids invented prices, contacts, availability or travel times.
- **Alternative:** Use plausible example destinations to make the demo look complete. Rejected.

### Dependency and runtime boundary
- **Decision:** Uvicorn is approved for running the FastAPI application; no other additional dependencies are approved.
- **Rationale:** FastAPI application code alone is not an HTTP server, and hidden dependency additions violate the no-new-dependencies rule.

### `.env` configuration without unapproved library
- **Decision:** Backend-only secrets remain in `backend/.env`. Before implementation, choose an approved dependency-free loader/injection mechanism or get approval for a dotenv/settings package. Do not expose values through Vite variables.
- **Rationale:** Neither python-dotenv nor pydantic-settings is listed.

### Offline boundary
- **Decision:** Cache the app shell and explicitly saved itinerary snapshots with referenced essential fields. No offline maps, routing, background refresh or silent overwrite.
- **Rationale:** Matches requested PWA behavior and documented MVP limit.

### Source precedence
- **Decision:** Current brief’s stack, scoring, UX and validation constraints override older support-document stack suggestions.
- **Rationale:** These are the explicit approved project requirements.

## Decisions needed before the app can run end to end

1. Decide how `.env` values are loaded without adding an unapproved package, or approve a package.
2. Supply verified destination, link, event (if available) and homestay records with sources, reviewer/date and host-contact consent.
3. Specify deployment CORS origin and whether a real server-side LLM provider will be used (optional; no provider is assumed).
4. Confirm browser/device for airplane-mode acceptance.

These are visible gates, not grounds to invent values or make the deterministic app depend on an optional integration.

## Phase 1 implementation update

- Uvicorn was explicitly approved by the user and added to `backend/requirements.txt` so FastAPI can run locally.
- Phase 1 dependency installation reported vulnerabilities in Vitest 3 and Tailwind CSS 3. Vitest is upgraded to the patched 4.1.11 line. Tailwind is deferred from the no-UI scaffold; its next major and integration should be selected in the UI phase without introducing an unapproved package.
- The only installed Python interpreter discovered is 3.12.10; backend smoke tests currently run in an isolated project `.venv` using 3.12, not the requested 3.11. Install/select 3.11 before treating Python-version acceptance as complete.