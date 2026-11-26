# MediCare AI Project Context

## Current phase

Backend foundations, authentication, patient profiles, Phase 4 private local
medical-record management, and the Phase 5A doctor-verification/discovery
slice are implemented. Appointment management and doctor credential-document
handling remain unimplemented; do not treat them as complete.

## Workspace facts

- Backend: `backend/`, Python 3.13.3, FastAPI, Pydantic Settings, SQLAlchemy 2,
  Alembic, PostgreSQL, PyJWT, and Argon2.
- Tests use isolated in-memory SQLite databases; they do not depend on a
  PostgreSQL service.
- Alembic revision `20261126_0003` adds doctor profiles and verification audit
  events after the existing medical-record revision; do not rewrite earlier
  migration files.
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
- `backend/app/models/` — user, patient profile, medical record, revoked
  token, doctor profile, and verification audit entities.
- `backend/app/schemas/` — validated request and public response models.
- `backend/app/api/v1/endpoints/` — health, authentication, patient,
  medical-record, doctor-discovery, and admin doctor-verification routes.
- `backend/app/services/` — authentication and private medical-file storage.
- `backend/migrations/` — Alembic environment and versioned schema migrations.
- `backend/tests/` — API and security tests.
- `frontend/src/api/` — typed API client and endpoint functions.
- `frontend/src/auth/` — authentication context and role-aware protected
  routes for patient, doctor, and admin accounts.
- `frontend/src/components/` — shared portal, form, and navigation components.
- `frontend/src/pages/` — landing, patient and doctor registration, login,
  patient profile and records, doctor directory/status, admin verification,
  and not-found pages.

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
- Doctor registration assigns DOCTOR server-side, creates a doctor profile,
  and always starts at PENDING; clients cannot choose roles or verification
  status. Medical registration numbers are normalized and unique.
- Admin doctor-verification routes require ADMIN server-side. Only PENDING
  applications can be approved/rejected, and only APPROVED doctors can be
  suspended. Decisions record the acting admin in an audit table; rejection
  and suspension require reasons. Public discovery only includes APPROVED
  doctors with active user accounts and omits registration and verification
  data.
- Provision administrator accounts from a trusted backend host using
  `python -m app.cli create-admin`. There is no public admin registration
  endpoint. Protect access to the configured database and the host.
- Medical-record endpoints require the PATIENT role and scope every list,
  detail, download, and delete query to the authenticated user. Never accept a
  client-supplied patient ID as authority.
- Medical files are stored outside the frontend in the configurable
  `MEDICAL_RECORDS_STORAGE_DIR` (default `backend/storage/medical-records`),
  excluded from Git, and named using random server-generated keys. Supported
  extensions/MIME types are PDF, JPG, JPEG, and PNG; the default maximum is
  10 MiB (`MEDICAL_RECORDS_MAX_UPLOAD_SIZE_MB`). API schemas omit storage keys
  and filesystem paths.
- This local-storage phase has no antivirus scanning, application-level
  encryption at rest, production backup strategy, or compliance assessment.
  Do not claim HIPAA, GDPR, or other certification.
- Doctor credential documents are not collected or stored in Phase 5A; verify
  credentials through a trusted manual process before approval. Add private,
  authorized document storage and rate limiting before public deployment.
- Email addresses are normalized to lowercase and protected by a database
  uniqueness constraint. Responses use explicit public schemas, not ORM
  serialization.
- Frontend tokens are stored in `sessionStorage` only. There is no refresh
  token flow; a 401 clears the local token and auth state.
- Frontend request/response types match the FastAPI schemas. Patient profile
  requests use the authenticated `/patients/me` endpoints. The profile page
  supports viewing and editing names, date of birth, and phone number; it
  displays account email, patient ID (the profile's `user_id`), and active
  status from `/auth/me` as read-only information, and refreshes the profile
  after a successful update. Gender and address are not in the current backend
  schema and are not shown.
- Dashboard visualizations are explicitly illustrative placeholders; do not
  present them as real patient readings or activity.
- Medical report files are private user uploads only; they are not submitted
  to an external AI provider and are not analyzed.

## Current API

- `GET /api/v1/health`
- `POST /api/v1/auth/register/patient`
- `POST /api/v1/auth/register/doctor`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/logout`
- `GET /api/v1/patients/me`
- `PUT /api/v1/patients/me`
- `POST /api/v1/medical-records/upload`
- `GET /api/v1/medical-records`
- `GET /api/v1/medical-records/{record_id}`
- `GET /api/v1/medical-records/{record_id}/download`
- `DELETE /api/v1/medical-records/{record_id}`
- `GET /api/v1/doctors/me`
- `GET /api/v1/doctors`
- `GET /api/v1/doctors/{doctor_id}`
- `GET /api/v1/admin/doctors/pending`
- `GET /api/v1/admin/doctors/{doctor_id}`
- `POST /api/v1/admin/doctors/{doctor_id}/approve`
- `POST /api/v1/admin/doctors/{doctor_id}/reject`
- `POST /api/v1/admin/doctors/{doctor_id}/suspend`
- `GET /api/v1/admin/doctors/approved`
- `GET /api/v1/admin/doctors/suspended`

## Known follow-up work

Next Phase 5 subphases should implement private doctor credential-document
upload/review and appointment availability/booking with concurrency-safe
conflict prevention. Before production, add rate limiting, account
verification and recovery workflows, expired-revocation cleanup, deployment
secret management, and an operational security review. These are not
implemented in the current subphase.
