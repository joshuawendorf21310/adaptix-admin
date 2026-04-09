# adaptix-admin

Standalone pilot extraction for the Adaptix admin, governance, and feature-flag experience.

## What is included

- FastAPI backend shell for:
  - health
  - local dev auth
  - feature flag CRUD/toggle/evaluate
  - audit and legal-hold shell endpoints with truthful zero-state behavior
- Next.js frontend shell for founder security and AI policy views

## Truthful runtime behavior

This repo does **not** fabricate cross-tenant audit evidence.

- feature flags are stored locally for standalone testing
- audit and replay endpoints return explicit standalone-shell empty state when no upstream evidence source is connected

## Run locally

### Backend

From `backend/`:

- install dependencies from `pyproject.toml`
- run `uvicorn core_app.main:app --reload --port 8012`

### Frontend

From `frontend/`:

- `npm install`
- `npm run dev`

Set `NEXT_PUBLIC_ADMIN_API_BASE` if the backend is not running at `http://127.0.0.1:8012`.# adaptix-admin

Bootstrapped target repository for the Adaptix polyrepo migration.
