# MediCare AI Project Context

## Current phase

Backend foundations, authentication, patient profiles, Phase 4 private local
medical-record management, Phase 5A doctor verification/discovery, and Phase
5B private doctor credential submission/review are implemented. Phase 5C
appointment availability, booking, and role-based management are implemented;
PostgreSQL migration/concurrency verification is tracked separately and must
pass before claiming production-ready scheduling.

## Workspace facts

- Backend: `backend/`, Python 3.13.3, FastAPI, Pydantic Settings, SQLAlchemy 2,
  Alembic, PostgreSQL, PyJWT, and Argon2.
- Tests use isolated in-memory SQLite databases; they do not depend on a
  PostgreSQL service.
- Alembic revision `20261126_0003` adds doctor profiles and verification audit
  events. Revision `20261126_0004` adds private doctor credentials and review
  events. Revision `20261126_0005` adds availability, appointments, audit
  events, and the PostgreSQL GiST overlap constraint. Do not rewrite earlier
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
  token, doctor profile, doctor credential, availability, appointment, and
  review/audit entities.
- `backend/app/schemas/` — validated request and public response models.
- `backend/app/api/v1/endpoints/` — health, authentication, patient,
  medical-record, doctor-discovery, doctor-credential, and admin review routes.
- `backend/app/services/` — authentication, appointment slot calculations,
  and shared private-file storage validation with separate medical-record
  and doctor-credential directories.
- `backend/migrations/` — Alembic environment and versioned schema migrations.
- `backend/tests/` — API and security tests.
- `frontend/src/api/` — typed API client and endpoint functions.
- `frontend/src/auth/` — authentication context and role-aware protected
  routes for patient, doctor, and admin accounts.
- `frontend/src/components/` — shared portal, form, and navigation components.
- `frontend/src/pages/` — landing, patient and doctor registration, login,
  patient profile, records and appointments, doctor directory/status and
  scheduling, admin verification and appointment inspection, and not-found
  pages.

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
- Admin doctor-verification and doctor-credential routes require ADMIN
  server-side. Only PENDING
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
- Doctor credential documents are separate from patient medical records.
  Supported types are medical registration certificate, medical degree
  certificate, and additional professional qualification certificate.
  `DOCTOR_CREDENTIALS_STORAGE_DIR` defaults to `backend/storage/doctor-credentials`;
  `DOCTOR_CREDENTIALS_MAX_UPLOAD_SIZE_MB` defaults to 10. Credential files use
  the same signature/content validation as medical records and independent
  randomized keys. Only the owning doctor and admins can access a stored file.
  Rejected required documents may be resubmitted as new records; review
  history is retained, and only pending submissions may be deleted.
- Appointment routes require participant roles server-side and scope patient
  and doctor access to their own records. Patient-supplied statuses are never
  accepted. Appointment notes are returned only to the patient/assigned doctor
  or an administrator through the explicitly authorized read-only admin APIs.
- Doctors may publish availability only while active, profile-approved, and
  meeting all required credential eligibility conditions. Weekly windows
  cannot overlap, may include a break, and generate slots in
  `APPOINTMENT_TIMEZONE` (default `UTC`). Date exceptions block all or part of
  a clinic-local day. Discovery of slots is limited to 90 days ahead.
- Appointment timestamps are stored as timezone-aware UTC instants. Patient
  cancellation and rescheduling default to a 24-hour cutoff, configurable via
  `PATIENT_APPOINTMENT_CANCELLATION_CUTOFF_HOURS` and
  `PATIENT_APPOINTMENT_RESCHEDULING_CUTOFF_HOURS`. A rescheduled confirmed
  booking returns to `BOOKED` and requires doctor confirmation.
- Active booking overlaps are rejected transactionally by the PostgreSQL
  exclusion constraint in revision `20261126_0005` (requires `btree_gist`).
  SQLite API tests cover sequential conflicts, not PostgreSQL concurrency.
- By default, public directory eligibility requires an APPROVED doctor
  profile, an active user, and approved medical registration and degree
  certificates. `REQUIRED_DOCTOR_CREDENTIAL_TYPES` can configure the required
  credential set. Public doctor responses never include credential metadata.
- This local-storage phase has no antivirus scanning, application-level
  encryption at rest, production backup strategy, or compliance assessment.
  Do not claim HIPAA, GDPR, or other certification.
- Credential files are stored locally without antivirus scanning or
  application-level encryption at rest. Reviewers must verify the submitted
  documents through an appropriate trusted process; no automated external
  credential verification is implemented.
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
- `POST /api/v1/doctor-credentials`
- `GET /api/v1/doctor-credentials/me`
- `GET /api/v1/doctor-credentials/{credential_id}`
- `GET /api/v1/doctor-credentials/{credential_id}/download`
- `DELETE /api/v1/doctor-credentials/{credential_id}` (pending only)
- `GET /api/v1/admin/doctor-credentials`
- `GET /api/v1/admin/doctor-credentials/{credential_id}`
- `GET /api/v1/admin/doctor-credentials/{credential_id}/download`
- `POST /api/v1/admin/doctor-credentials/{credential_id}/approve`
- `POST /api/v1/admin/doctor-credentials/{credential_id}/reject`
- `GET /api/v1/doctor/availability`
- `POST /api/v1/doctor/availability`
- `PUT /api/v1/doctor/availability/{availability_id}`
- `DELETE /api/v1/doctor/availability/{availability_id}`
- `GET /api/v1/doctor/availability/exceptions`
- `POST /api/v1/doctor/availability/exceptions`
- `DELETE /api/v1/doctor/availability/exceptions/{exception_id}`
- `GET /api/v1/appointments/available-slots`
- `POST /api/v1/appointments`
- `GET /api/v1/appointments/me`
- `GET /api/v1/appointments/{appointment_id}`
- `PUT /api/v1/appointments/{appointment_id}/reschedule`
- `POST /api/v1/appointments/{appointment_id}/cancel`
- `GET /api/v1/doctor/appointments`
- `GET /api/v1/doctor/appointments/{appointment_id}`
- `POST /api/v1/doctor/appointments/{appointment_id}/confirm`
- `POST /api/v1/doctor/appointments/{appointment_id}/reject`
- `POST /api/v1/doctor/appointments/{appointment_id}/cancel`
- `POST /api/v1/doctor/appointments/{appointment_id}/complete`
- `POST /api/v1/doctor/appointments/{appointment_id}/no-show`
- `PUT /api/v1/doctor/appointments/{appointment_id}/notes`
- `GET /api/v1/admin/appointments`
- `GET /api/v1/admin/appointments/{appointment_id}`

## Known follow-up work

Before production, apply and verify migration `20261126_0005` on PostgreSQL,
run the concurrent booking check with independent database sessions, add rate
limiting, account verification and recovery workflows, expired-revocation
cleanup, deployment secret management, and an operational security review.
These follow-ups are not represented as completed by local SQLite tests.
