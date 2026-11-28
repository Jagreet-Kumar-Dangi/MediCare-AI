# MediCare AI Project Context

## Current phase

Backend foundations, authentication, patient profiles, Phase 4 private local
medical-record management, Phase 5A doctor verification/discovery, Phase 5B
private doctor credential submission/review, and Phase 5C appointment
scheduling are implemented. Phase 6 adds appointment notifications,
preferences, reminders, an SMTP outbox worker, and admin job monitoring.
Revisions `20261126_0005` and `20261126_0006` are applied and Alembic-checked
on the configured local PostgreSQL database. The Phase 6 worker-claim
concurrency path was exercised there with synthetic data. SMTP was mocked;
no live provider was used. Repeat migration and worker-concurrency validation
against each deployment database; local verification is not a production
readiness or compliance assessment.

Phase 7 adds admin-only SQL aggregate analytics, `Asia/Kolkata` reporting
windows, paginated doctor operations data, and aggregate-only CSV exports.
Its additive analytics-index migration is `20261127_0007`, applied and
Alembic-checked on the configured local PostgreSQL database. Aggregate
endpoints were smoke-tested against PostgreSQL using temporary records rolled
back after the checks. The browser workflow was exercised with isolated
SQLite test data; at validation time the configured PostgreSQL database had
no administrator accounts, so authenticated PostgreSQL browser verification
remains outstanding. Analytics do not expose patient medical records,
credential files, or notification contents.

Phase 8C adds mandatory email OTP verification for public patient and doctor
registration. Revision `20261128_0008` adds verification state, hashed OTP
challenges, and hashed email/IP rate-limit events; it is applied to the
configured PostgreSQL database and passes `alembic check`. Upgrade,
downgrade, and re-upgrade were exercised; the four existing accounts remained
intact and the new challenge/rate-limit tables were empty after the check.
Backend tests passed (77); React typecheck, lint, build, and five tests passed.
Live disposable patient and doctor flows delivered OTPs to the controlled
Gmail inbox and updated PostgreSQL verification state. Patient login and
`/auth/me` succeeded, unverified login was rejected, an incorrect OTP was
rejected, React resend/verification succeeded, and the doctor remained
professionally `PENDING`. Disposable records were removed afterward.
Flutter analysis is clean, six tests pass, and the debug APK builds. After the
user reported installing the current APK, the Pixel 7 login screen was still
observed without the verification-recovery control present in source. Live
Flutter registration, OTP, login, and protected `/me` verification have not
been completed; the latest emulator capture is the Android launcher setup
screen rather than the app. Phase 8C live Flutter verification remains
outstanding.

## Workspace facts

- Backend: `backend/`, Python 3.13.3, FastAPI, Pydantic Settings, SQLAlchemy 2,
  Alembic, PostgreSQL, PyJWT, and Argon2.
- Tests use isolated SQLite databases; they do not depend on a
  PostgreSQL service.
- Alembic revision `20261126_0003` adds doctor profiles and verification audit
  events. Revision `20261126_0004` adds private doctor credentials and review
  events. Revision `20261126_0005` adds availability, appointments, audit
  events, and the PostgreSQL GiST overlap constraint. Revision
  `20261126_0006` adds notifications, user preferences, and the email/reminder
  job outbox. Revision `20261127_0007` adds timestamp indexes for reporting
  aggregations. Revision `20261128_0008` adds email-verification state and OTP
  challenges. Do not rewrite earlier migration files.
- Frontend: `frontend/`, React + TypeScript + Vite, Tailwind CSS, React Router,
  Axios, Lucide, and Recharts.
- `mobile/` contains the Flutter patient/doctor application. Phase 8B adds
  patient profile editing, eligible-doctor discovery, and patient appointment
  flows. Phase 8C adds email verification; its unit/widget and APK checks pass,
  but live Pixel 7 authentication verification remains outstanding.
  Medical-record and admin mobile features are not in scope. `ml/`,
  `infrastructure/`, and `docs/` remain reserved for future work.
- Local environment values belong in `backend/.env`, which is ignored by Git.
  Frontend API configuration belongs in the ignored `frontend/.env`. Keep real
  database credentials and JWT signing keys out of tracked files.

## Backend structure

- `backend/app/core/` — settings and password/JWT security helpers.
- `backend/app/db/` — SQLAlchemy declarative base, engine, and session
  dependency.
- `backend/app/models/` — user, patient profile, medical record, revoked
  token, doctor profile, doctor credential, availability, appointment, and
  review/audit entities, notifications, preferences, and outbox jobs.
- `backend/app/schemas/` — validated request and public response models.
- `backend/app/api/v1/endpoints/` — health, authentication, patient,
  medical-record, doctor-discovery, doctor-credential, admin review, and
  administrator analytics routes.
- `backend/app/services/` — authentication, appointment slot calculations,
  and shared private-file storage validation with separate medical-record
  and doctor-credential directories; notification rendering, scheduling, and
  worker processing.
- `backend/migrations/` — Alembic environment and versioned schema migrations.
- `backend/tests/` — API and security tests.
- `frontend/src/api/` — typed API client and endpoint functions.
- `frontend/src/auth/` — authentication context and role-aware protected
  routes for patient, doctor, and admin accounts.
- `frontend/src/components/` — shared portal, form, and navigation components.
- `frontend/src/pages/` — landing, patient and doctor registration, login,
  patient profile, records and appointments, doctor directory/status and
  scheduling, admin verification and appointment inspection, and not-found
  pages. `/admin/analytics` is the protected administrator analytics workspace.

Run commands from `backend/` unless otherwise specified:

- Apply migrations: `python -m alembic upgrade head`
- Start development server: `python -m uvicorn app.main:app --reload`
- Run tests: `python -m pytest`

Run frontend commands from `frontend/`:

- Start Vite: `npm run dev`
- Type-check: `npm run typecheck`
- Lint: `npm run lint`
- Build: `npm run build`

The Flutter app in `mobile/` uses Riverpod, GoRouter, Dio, and Flutter Secure
Storage. It supports login, patient/doctor registration, role-specific
dashboards, patient profile editing, eligible-doctor discovery, and patient
appointment workflows. From `mobile/`:

- Resolve packages: `flutter pub get`
- Analyze: `flutter analyze`
- Test: `flutter test`
- Build Android debug APK: `flutter build apk --debug`

The Android emulator API base URL defaults to `http://10.0.2.2:8000/api/v1`;
`MEDICARE_API_URL` can override it at build/run time. Verify live mobile
workflows against the configured PostgreSQL backend and Pixel 7 emulator.
Appointment booking lifecycle verification requires at least one approved,
active, credential-eligible doctor with future availability; do not bypass the
backend's eligibility or scheduling rules to create a test fixture.
The current debug APK builds successfully, but after a reported installation,
the Pixel 7 login screen was still observed without the Phase 8C
verification-recovery control. Do not treat source-level tests or the APK
build as live Flutter verification; confirm the current app version and
reopen it from the Android launcher, then complete disposable patient and
doctor registration/login flows first.

The backend README contains a manual PostgreSQL plus private-upload backup and
restore procedure. It has not been validated as a production disaster-recovery
plan; conduct and document a restore drill before deployment.

## Authentication and authorization invariants

- Roles are `PATIENT`, `DOCTOR`, and `ADMIN`; account role assignment is
  server-controlled.
- Public registration exists only for patients and doctors. Never add public
  administrator registration. Admin accounts require trusted operational
  provisioning.
- Patient and doctor registration creates inactive, pending accounts and
  requires a six-digit email OTP before login. OTPs expire after five minutes,
  allow five incorrect attempts, and can be resent after sixty seconds;
  database-backed HMAC hashes and email/IP rate limits are used. Existing
  patient/doctor accounts require verification on their next login. Admin CLI
  provisioning and login remain unchanged.
- Verifying a doctor's email never approves professional credentials or the
  doctor profile; administrator approval and required credential review remain
  independent gates.
- Password hashes use Argon2id. Never serialize or log password hashes,
  passwords, signing keys, or bearer tokens.
- JWT access tokens are signed using a private environment-provided key, have
  required expiry and token identifiers, and use the fixed HS256 algorithm.
- Logout persists the token identifier in `revoked_tokens`; authenticated
  requests reject revoked tokens.
- Mobile access tokens are stored in Flutter Secure Storage, are not logged,
  and are cleared on logout and API `401` responses. Session-restoration
  network errors preserve the stored token.
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
- Appointment lifecycle changes write in-app notifications and durable
  notification jobs in the same database transaction. Users manage their
  notification and reminder preferences at `/api/v1/notifications`; admins
  inspect masked delivery job metadata at `/api/v1/admin/notifications/jobs`.
  The worker runs separately with
  `python -m app.services.notification_worker` from `backend/`.
- Reminder email requires `SMTP_HOST`, `SMTP_FROM_EMAIL`, and, if used, a
  matching SMTP username/password pair. TLS and SSL modes are mutually
  exclusive. Jobs are polled from PostgreSQL with leases, bounded retries, and
  idempotency keys; SMTP delivery is at-least-once if a worker crashes after
  the remote server accepts a message but before the database commit. Messages
  omit visit reasons, notes, medical records, and credential files. Events
  created before SMTP is configured are retained as skipped jobs and are not
  replayed automatically.
- Registration verification uses Gmail STARTTLS on port 587 and requires
  `SMTP_HOST=smtp.gmail.com`, `SMTP_USERNAME`, `SMTP_PASSWORD` (Google App
  Password), `SMTP_FROM_EMAIL`, and `SMTP_USE_TLS=true`. Credentials remain
  backend-only in the ignored `backend/.env`; never place them in client
  configuration. Live Gmail delivery and PostgreSQL verification succeeded for
  disposable patient and doctor accounts through backend/React flows; the
  Flutter app-device flow remains unverified.
- Active booking overlaps are rejected transactionally by the PostgreSQL
  exclusion constraint in revision `20261126_0005` (requires `btree_gist`).
  SQLite API tests cover sequential conflicts, not PostgreSQL concurrency.
- By default, public directory eligibility requires an APPROVED doctor
  profile, an active user, and approved medical registration and degree
  certificates. `REQUIRED_DOCTOR_CREDENTIAL_TYPES` can configure the required
  credential set. Public doctor responses never include credential metadata.
- Analytics reporting periods are evaluated in `Asia/Kolkata`; API date ranges
  are inclusive local dates converted into half-open UTC database bounds.
  Percent changes compare the immediately preceding equivalent period and are
  unavailable when its count is zero. Appointment booking trends use
  appointment creation time; cancellation and completion trends use audited
  event time. Performance appointment totals use booking creation time, while
  upcoming counts include all currently booked or confirmed future appointments.
  CSV files contain date/status/count aggregates and escape formula-like cells.
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
- `POST /api/v1/auth/verify-email/send`
- `POST /api/v1/auth/verify-email/confirm`
- `POST /api/v1/auth/verify-email/resend`
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
- `GET /api/v1/notifications`
- `GET /api/v1/notifications/unread-count`
- `PATCH /api/v1/notifications/{notification_id}/read`
- `PATCH /api/v1/notifications/read-all`
- `DELETE /api/v1/notifications/{notification_id}`
- `GET /api/v1/notifications/preferences`
- `PUT /api/v1/notifications/preferences`
- `GET /api/v1/admin/notifications/jobs`

## Known follow-up work

Run a concurrent worker-claim check with independent sessions against each
target PostgreSQL database. Remaining work includes expired-revocation
cleanup, deployment secret management, a tested backup/restore plan, live
Flutter verification on Pixel 7 using the current APK, and an independent
operational security review. Backend/React live verification succeeded, but
local SQLite tests and development PostgreSQL checks do not provide
production or regulatory assurance.
