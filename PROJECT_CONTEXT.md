# MediCare AI Project Context

## Current phase

Phase 1 and Phase 2 backend foundations and the Phase 3 React patient portal
are implemented. Keep future changes within the feature explicitly requested;
do not introduce AI prediction, chatbot, medical-report, appointment, or
reminder functionality as part of foundation work.

## Workspace facts

- Backend: `backend/`, Python 3.13.3, FastAPI, Pydantic Settings, SQLAlchemy 2,
  Alembic, PostgreSQL, PyJWT, and Argon2.
- Tests use isolated in-memory SQLite databases; they do not depend on a
  PostgreSQL service.
- Frontend: `frontend/`, React + TypeScript + Vite, Tailwind CSS, React Router,
  Axios, Lucide, and Recharts.
- `mobile/`, `ml/`, `infrastructure/`, and `docs/` remain reserved for future
  work.
- Local environment values belong in `backend/.env`, which is ignored by Git.
  Frontend API configuration belongs in the ignored `frontend/.env`. Keep real
  database credentials and JWT signing keys out of tracked files.

## Backend structure

- `backend/app/core/` — settings and password/JWT security helpers.
- `backend/app/db/` — SQLAlchemy declarative base, engine, and session
  dependency.
- `backend/app/models/` — user, patient profile, and revoked token entities.
- `backend/app/schemas/` — validated request and public response models.
- `backend/app/api/v1/endpoints/` — health, authentication, and patient routes.
- `backend/app/services/` — account registration and authentication logic.
- `backend/migrations/` — Alembic environment and versioned schema migrations.
- `backend/tests/` — API and security tests.
- `frontend/src/api/` — typed API client and endpoint functions.
- `frontend/src/auth/` — authentication context and protected route.
- `frontend/src/components/` — shared portal, form, and navigation components.
- `frontend/src/pages/` — landing, registration, login, dashboard, profile, and
  not-found pages.

Run commands from `backend/` unless otherwise specified:

- Apply migrations: `python -m alembic upgrade head`
- Start development server: `python -m uvicorn app.main:app --reload`
- Run tests: `python -m pytest`

Run frontend commands from `frontend/`:

- Start Vite: `npm run dev`
- Type-check: `npm run typecheck`
- Build: `npm run build`

## Authentication and authorization invariants

- Roles are `PATIENT`, `DOCTOR`, and `ADMIN`; account role assignment is
  server-controlled.
- Public registration exists only for patients and doctors. Never add public
  administrator registration. Admin accounts require trusted operational
  provisioning.
- Password hashes use Argon2id. Never serialize or log password hashes,
  passwords, signing keys, or bearer tokens.
- JWT access tokens are signed using a private environment-provided key, have
  required expiry and token identifiers, and use the fixed HS256 algorithm.
- Logout persists the token identifier in `revoked_tokens`; authenticated
  requests reject revoked tokens.
- Patient endpoints require the PATIENT role and query/update only the
  authenticated user's own profile.
- Email addresses are normalized to lowercase and protected by a database
  uniqueness constraint. Responses use explicit public schemas, not ORM
  serialization.
- Frontend tokens are stored in `sessionStorage` only. There is no refresh
  token flow; a 401 clears the local token and auth state.
- Frontend request/response types match the FastAPI schemas. Patient profile
  PUT requests send all required fields, including nullable birth date and
  phone values.
- Dashboard visualizations are explicitly illustrative placeholders; do not
  present them as real patient readings or activity.

## Current API

- `GET /api/v1/health`
- `POST /api/v1/auth/register/patient`
- `POST /api/v1/auth/register/doctor`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/logout`
- `GET /api/v1/patients/me`
- `PUT /api/v1/patients/me`

## Known follow-up work

Before production, add rate limiting, account verification and recovery
workflows, doctor credential review, expired-revocation cleanup, deployment
secret management, and operational administrator provisioning. These are not
implemented in the current phase.
