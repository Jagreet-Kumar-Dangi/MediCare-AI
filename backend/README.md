# MediCare AI Backend

The backend provides the FastAPI foundation, authentication, PostgreSQL
persistence, patient profiles, private local medical-record management, doctor
verification and discovery, and private doctor credential submission/review.
The backend also provides appointment scheduling and management,
transactionally persisted appointment notifications, reminders, optional SMTP
delivery, and admin job monitoring. AI features are not implemented.

## Requirements

- Python 3.13.3
- PostgreSQL for local API development
- Dependencies from `requirements.txt`

## Setup (Windows PowerShell)

From the `backend` directory:

```powershell
py -3.13 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `DATABASE_URL` to a PostgreSQL connection URL. Generate a private JWT
signing key and place it in `.env`:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

The `.env` file is ignored by Git. Never commit signing keys or database
credentials.

## Database migrations

Create the PostgreSQL database configured by `DATABASE_URL`, then apply
migrations from the `backend` directory:

```powershell
python -m alembic upgrade head
```

Medical records are added by revision `20261126_0002`; doctor profiles and the
verification audit trail are added by `20261126_0003`; doctor credential
documents and review history are added by `20261126_0004`; doctor availability
and appointments are added by `20261126_0005`. PostgreSQL migrations enable
`btree_gist` for the appointment overlap exclusion constraint when necessary.
Revision `20261126_0006` adds notifications, user preferences, and durable
email/reminder jobs.
Revision `20261127_0007` adds timestamp indexes used by analytics date-range
aggregates; it does not add tables or alter existing data. The analytics
service uses the existing transactional tables rather than a separate
warehouse. To revert only these indexes, downgrade to
`20261126_0006`; upgrading to `head` recreates them.
Revision `20261128_0008` adds nullable email verification timestamps,
pending-registration state, persistent hashed OTP challenges, and hashed
email/IP rate-limit events. Existing patient and doctor accounts are not
silently marked verified; they must complete email verification before their
next login. Admin CLI accounts remain exempt. The migration is additive and
does not modify doctor approval or credential status.
The extension is intentionally retained on downgrade. To roll back only the
notification revision while retaining appointments:

```powershell
python -m alembic downgrade 20261126_0005
```

This removes notification tables and their data. Rolling back further to
`20261126_0004` also removes availability and appointment tables and their
records; back up required data before downgrading. Earlier migrations are
additive and must not be rewritten.

To create a migration after changing models:

```powershell
python -m alembic revision --autogenerate -m "describe the schema change"
```

## Manual backup and restore

The application has no automated backup service. For local recovery, back up
the PostgreSQL database and both private upload directories together. Pause
application writes while taking the database and file copies so their contents
remain consistent. The dump and copied files contain sensitive account and
health-related data: store them outside this repository, restrict access, and
protect the backup destination with appropriate encryption and retention.

The following Windows PowerShell example uses the default local database and
storage paths. Configure `PGHOST`, `PGPORT`, `PGDATABASE`, and `PGUSER` for the
database in `DATABASE_URL`; allow `pg_dump` to prompt for the password or use a
protected PostgreSQL password file. Do not put database passwords in commands
or commit backup files.

```powershell
$backup = Join-Path $env:USERPROFILE ("medicare-ai-backup-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
New-Item -ItemType Directory -Path $backup | Out-Null
$env:PGHOST = "localhost"
$env:PGPORT = "5432"
$env:PGDATABASE = "medicare_ai"
$env:PGUSER = "medicare_ai"
pg_dump --format=custom --file (Join-Path $backup "medicare_ai.dump")
$medicalRecordsPath = ".\storage\medical-records"
$doctorCredentialsPath = ".\storage\doctor-credentials"
New-Item -ItemType Directory -Force -Path $medicalRecordsPath, $doctorCredentialsPath | Out-Null
robocopy $medicalRecordsPath (Join-Path $backup "medical-records") /E /R:2 /W:2
if ($LASTEXITCODE -ge 8) { throw "Medical-record storage backup failed." }
robocopy $doctorCredentialsPath (Join-Path $backup "doctor-credentials") /E /R:2 /W:2
if ($LASTEXITCODE -ge 8) { throw "Doctor-credential storage backup failed." }
```

Replace the storage source paths if `MEDICAL_RECORDS_STORAGE_DIR` or
`DOCTOR_CREDENTIALS_STORAGE_DIR` points elsewhere. Restore into a new, empty
database and the configured private storage directories; do not use
`pg_restore --clean` against a database containing data you need to preserve.
The example restores files into new staging directories so they do not merge
with or overwrite existing uploads. After configuring the `PG*` variables
above:

```powershell
createdb --maintenance-db=postgres medicare_ai_restore
pg_restore --no-owner --dbname=medicare_ai_restore (Join-Path $backup "medicare_ai.dump")
$restoreStorage = Join-Path $env:USERPROFILE ("medicare-ai-restored-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
$medicalRecordsRestore = Join-Path $restoreStorage "medical-records"
$doctorCredentialsRestore = Join-Path $restoreStorage "doctor-credentials"
New-Item -ItemType Directory -Force -Path $medicalRecordsRestore, $doctorCredentialsRestore | Out-Null
robocopy (Join-Path $backup "medical-records") $medicalRecordsRestore /E /R:2 /W:2
if ($LASTEXITCODE -ge 8) { throw "Medical-record storage restore failed." }
robocopy (Join-Path $backup "doctor-credentials") $doctorCredentialsRestore /E /R:2 /W:2
if ($LASTEXITCODE -ge 8) { throw "Doctor-credential storage restore failed." }
```

Set `DATABASE_URL`, `MEDICAL_RECORDS_STORAGE_DIR`, and
`DOCTOR_CREDENTIALS_STORAGE_DIR` to the restored database and staging
directories before starting the API. If the restored schema is behind the
application revision, review and apply
`python -m alembic upgrade head` before serving traffic. This procedure is
documentation only; a restore drill, production backup automation, off-site
retention, and recovery objectives have not been independently validated.

## Run the API

```powershell
python -m uvicorn app.main:app --reload
```

- Health check: <http://127.0.0.1:8000/api/v1/health>
- Swagger UI: <http://127.0.0.1:8000/docs>
- OpenAPI schema: <http://127.0.0.1:8000/openapi.json>

## Authentication endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/v1/auth/register/patient` | Register a patient and create a profile |
| POST | `/api/v1/auth/register/doctor` | Register a doctor and submit a pending profile |
| POST | `/api/v1/auth/verify-email/send` | Send a verification code when eligible |
| POST | `/api/v1/auth/verify-email/confirm` | Confirm a six-digit email code |
| POST | `/api/v1/auth/verify-email/resend` | Resend a code after cooldown |
| POST | `/api/v1/auth/login` | Issue a short-lived JWT access token |
| GET | `/api/v1/auth/me` | Return the authenticated user's public details |
| POST | `/api/v1/auth/logout` | Revoke the current access token |
| GET | `/api/v1/doctors/me` | Read the authenticated doctor's verification profile |
| GET | `/api/v1/doctors` | Discover approved, active doctors |
| GET | `/api/v1/doctors/{doctor_id}` | Read an approved public doctor profile |
| GET | `/api/v1/admin/doctors/pending` | List applications awaiting admin review |
| GET | `/api/v1/admin/doctors/{doctor_id}` | Read a doctor application (admin only) |
| POST | `/api/v1/admin/doctors/{doctor_id}/approve` | Approve a pending application |
| POST | `/api/v1/admin/doctors/{doctor_id}/reject` | Reject a pending application with a reason |
| POST | `/api/v1/admin/doctors/{doctor_id}/suspend` | Suspend an approved doctor with a reason |
| GET | `/api/v1/admin/doctors/approved` | List approved doctors (admin only) |
| GET | `/api/v1/admin/doctors/suspended` | List suspended doctors (admin only) |
| GET | `/api/v1/patients/me` | Read the authenticated patient's profile |
| PUT | `/api/v1/patients/me` | Replace the authenticated patient's profile |
| POST | `/api/v1/medical-records/upload` | Upload a private patient report |
| GET | `/api/v1/medical-records` | List the authenticated patient's reports |
| GET | `/api/v1/medical-records/{record_id}` | Read owned report metadata |
| GET | `/api/v1/medical-records/{record_id}/download` | Download an owned report |
| DELETE | `/api/v1/medical-records/{record_id}` | Delete owned metadata and file |
| POST | `/api/v1/doctor-credentials` | Submit a private credential document |
| GET | `/api/v1/doctor-credentials/me` | List own documents and eligibility state |
| GET | `/api/v1/doctor-credentials/{credential_id}` | Read owned credential metadata |
| GET | `/api/v1/doctor-credentials/{credential_id}/download` | Download an owned credential |
| DELETE | `/api/v1/doctor-credentials/{credential_id}` | Delete an owned pending submission |
| GET | `/api/v1/admin/doctor-credentials` | List credentials (admin only; filter by status) |
| GET | `/api/v1/admin/doctor-credentials/{credential_id}` | Read credential and review history |
| GET | `/api/v1/admin/doctor-credentials/{credential_id}/download` | Secure admin download |
| POST | `/api/v1/admin/doctor-credentials/{credential_id}/approve` | Approve a pending credential |
| POST | `/api/v1/admin/doctor-credentials/{credential_id}/reject` | Reject a pending credential with a reason |
| GET | `/api/v1/doctor/availability` | List the authenticated doctor's weekly availability |
| POST | `/api/v1/doctor/availability` | Add a weekly availability window |
| PUT | `/api/v1/doctor/availability/{availability_id}` | Update an owned availability window |
| DELETE | `/api/v1/doctor/availability/{availability_id}` | Remove an owned availability window |
| GET | `/api/v1/doctor/availability/exceptions` | List the authenticated doctor's blocked dates/times |
| POST | `/api/v1/doctor/availability/exceptions` | Block an unavailable date or time range |
| DELETE | `/api/v1/doctor/availability/exceptions/{exception_id}` | Remove an owned availability exception |
| GET | `/api/v1/appointments/available-slots` | List available slots for an eligible doctor and date |
| POST | `/api/v1/appointments` | Book a slot (patient only) |
| GET | `/api/v1/appointments/me` | List the authenticated patient's appointments |
| GET | `/api/v1/appointments/{appointment_id}` | Read an owned patient appointment |
| PUT | `/api/v1/appointments/{appointment_id}/reschedule` | Reschedule an owned patient appointment |
| POST | `/api/v1/appointments/{appointment_id}/cancel` | Cancel an owned patient appointment |
| GET | `/api/v1/doctor/appointments` | List appointments assigned to the authenticated doctor |
| GET | `/api/v1/doctor/appointments/{appointment_id}` | Read an appointment assigned to the doctor |
| POST | `/api/v1/doctor/appointments/{appointment_id}/confirm` | Confirm a booked appointment |
| POST | `/api/v1/doctor/appointments/{appointment_id}/reject` | Reject a booked appointment with a reason |
| POST | `/api/v1/doctor/appointments/{appointment_id}/cancel` | Cancel an assigned appointment with a reason |
| POST | `/api/v1/doctor/appointments/{appointment_id}/complete` | Complete an ended, confirmed appointment |
| POST | `/api/v1/doctor/appointments/{appointment_id}/no-show` | Mark an ended appointment as no-show |
| PUT | `/api/v1/doctor/appointments/{appointment_id}/notes` | Save private doctor notes |
| GET | `/api/v1/admin/appointments` | Inspect appointments (admin only, read-only) |
| GET | `/api/v1/admin/appointments/{appointment_id}` | Inspect appointment detail and audit events (admin only) |
| GET | `/api/v1/admin/analytics/overview` | Aggregate KPI counts and prior-period comparisons (admin only) |
| GET | `/api/v1/admin/analytics/patients` | Patient registration totals and trends (admin only) |
| GET | `/api/v1/admin/analytics/doctors` | Doctor/credential status counts and trends (admin only) |
| GET | `/api/v1/admin/analytics/appointments` | Appointment status and lifecycle trends (admin only) |
| GET | `/api/v1/admin/analytics/notifications` | Notification job, retry, and email delivery aggregates (admin only) |
| GET | `/api/v1/admin/analytics/doctor-performance` | Paginated per-doctor operational counts (admin only) |
| GET | `/api/v1/admin/analytics/export` | Download aggregate-only CSV reports (admin only) |

Patient and doctor registration assign their roles on the server. Doctor
registration requires a professional profile and medical registration number;
verification status is always assigned as `PENDING` by the server. There is no
public administrator registration endpoint. Provision administrators only
from a trusted host with the intended database configured in `backend/.env`:

```powershell
python -m app.cli create-admin
```

The command prompts for an email and password, hashes the password with the
existing Argon2 utility, and creates an `ADMIN` user without exposing a
credential in shell history. Protect host access and database credentials;
never expose this operational command as a public API. Protected endpoints use
`Authorization: Bearer <access_token>`.

New patient and doctor accounts remain inactive until their email is verified.
The backend sends a six-digit code that expires in five minutes; each code
allows five incorrect attempts, and resending has a sixty-second cooldown.
Only a keyed hash is stored. The send/resend responses do not disclose whether
an address is registered, and requests are limited to five per email and
twenty per source IP per hour. A successfully verified doctor remains pending
the existing administrator approval and credential checks.

Configure verification email in the private `backend/.env` only:

```text
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=
SMTP_FROM_NAME=MediCare AI
SMTP_USE_TLS=true
```

Set `SMTP_USERNAME` and `SMTP_FROM_EMAIL` to the controlled Gmail sender and
use a Google App Password for `SMTP_PASSWORD`. Keep the credentials out of
React/Flutter configuration and logs. A missing or failed SMTP setup returns
a safe delivery error and leaves a new account pending and inactive.

## Admin analytics (Phase 7)

The analytics API and `/admin/analytics` frontend route require the
`ADMIN` role. Patients and doctors receive `403 Forbidden`; no public
administrator registration exists. Supported periods are `today`,
`last_7_days`, `last_30_days`, `last_90_days`, `this_month`,
`previous_month`, and `custom`. Custom requests require inclusive
`start_date=YYYY-MM-DD` and `end_date=YYYY-MM-DD`. Trends accept
`granularity=day|week|month`; appointment reports additionally accept
`status` and positive `doctor_id`, and doctor reports accept
`verification_status`.

Clinic reporting uses `Asia/Kolkata`. Local date boundaries are converted to
UTC and queried as half-open ranges (`timestamp >= start AND timestamp < end`),
so the selected `date_to` includes its complete local day. Appointment
timestamps remain stored as UTC and appointment scheduling timezone behavior
is unchanged.

Definitions:

- Overview user/patient/doctor/appointment totals are current database totals.
  Upcoming overview appointments are BOOKED or CONFIRMED with a future
  scheduled start. New-user, new-patient, new-doctor, and appointment-creation
  comparisons count records created in the selected window versus the
  immediately preceding window of the same duration. A percentage is omitted
  when the previous count is zero.
- Patient totals and active/inactive counts use `users.is_active`; registration
  trends count PATIENT users by `users.created_at`.
- Doctor status counts use the current profile status. Credential counts use
  credential submission dates and statuses, not files or reviewer details.
  Doctor approval trends count APPROVED events by audit timestamp.
- Appointment volume/status counts use appointment creation time and current
  status. Cancellation/completion trends use their audit event timestamps.
  The appointment upcoming count is limited to future scheduled starts inside
  the selected local date window. Doctor performance appointment/completed/
  cancelled counts use booking creation time; its upcoming count includes all
  currently booked or confirmed future appointments, independent of the
  selected booking period. Operational volume is not a measure of clinical
  quality.
- Notification job counts and trends use job creation time. Total retries are
  the sum of `attempt_count - 1` for jobs attempted more than once.
  Email-success rate is SENT email jobs divided by SENT plus FAILED email jobs;
  it is unavailable when that denominator is zero.
- CSV datasets are patient registration aggregates, doctor registration/status
  aggregates, appointment creation/status aggregates, and notification
  channel/status/retry aggregates. Filters and reporting timezone are
  preserved. CSV cells beginning with spreadsheet formula characters after
  whitespace are prefixed with an apostrophe. Exports do not contain patient
  names, emails, medical records, credential documents, notification
  recipients, or message bodies.

Analytics are calculated with SQL aggregate queries and time-range indexes;
doctor-performance lists are paginated. Empty ranges return zero-filled trend
buckets and status counts, not fabricated sample data. No analytics data
warehouse or external service is used.

## Doctor verification and discovery

Doctor profiles are one-to-one with `users`. Self-registration accepts profile
details but not a role, status, approver, or verification timestamp. Medical
registration numbers are uppercased and unique. The verification states are
`PENDING`, `APPROVED`, `REJECTED`, and `SUSPENDED`; allowed transitions are
`PENDING` to `APPROVED` or `REJECTED`, and `APPROVED` to `SUSPENDED`.
Invalid/repeated transitions return `409 Conflict`. Rejection and suspension
require a reason. Every administrator decision records the admin user ID,
action, timestamp, and reason in `doctor_verification_events`.

All `/admin/doctors` routes require the existing `ADMIN` role dependency.
Public discovery returns only `APPROVED` doctors whose user account is active;
it supports specialization, experience, fee, and name filters. Public response
models omit registration numbers and administrative verification fields.

The doctor profile and credential workflows are reviewed separately. A doctor
profile must be approved and every configured required credential must also
be approved before appearing in public discovery. Credential review stores
decision history; reviewers must still verify authenticity through a trusted
process.

## Doctor credential documents

Doctors upload a document with multipart fields `document_type` and `file`.
Document types are:

- `MEDICAL_REGISTRATION_CERTIFICATE`
- `MEDICAL_DEGREE_CERTIFICATE`
- `ADDITIONAL_QUALIFICATION_CERTIFICATE`

PDF, JPG, JPEG, and PNG files are accepted up to 10 MiB by default.
`DOCTOR_CREDENTIALS_STORAGE_DIR` configures the separate private directory
(default `storage/doctor-credentials`, relative to `backend/` unless absolute);
`DOCTOR_CREDENTIALS_MAX_UPLOAD_SIZE_MB` sets the positive size limit.
Credential metadata and audit events are stored in the database, while files
use randomized server-generated names. No API response includes a storage key
or filesystem path, and the directory is not exposed as static content.

Only the owning doctor can list, read, download, or delete their own pending
documents. Only admins can list/review/download any doctor's credentials.
Pending credentials can be deleted; approved or rejected submissions remain
for review history. A rejected required credential can be resubmitted as a new
submission. Registration and degree certificates are required by default;
set `REQUIRED_DOCTOR_CREDENTIAL_TYPES` to a JSON list in `.env` to configure
the required set. Public directory results require an approved doctor profile,
an active user account, and every configured credential type approved.

Local development storage does not provide antivirus scanning,
application-level encryption at rest, automated credential authenticity
checks, or a compliance assessment. Reviewers must use a trusted verification
process. Do not claim HIPAA, GDPR, or other certification.

## Appointment scheduling

Only active doctors whose profile and all configured required credentials are
approved can publish availability or receive new bookings. Doctors configure
non-overlapping weekly working windows, optional in-window breaks, and
appointment durations from 5 to 240 minutes. Date-specific exceptions can block
a full day or a local-time interval. Public slot queries are limited to today
through 90 days ahead; past slots are never offered.

`APPOINTMENT_TIMEZONE` sets the IANA clinic timezone for weekly availability
and defaults to `UTC`. Appointment instants are stored and returned as
timezone-aware UTC timestamps. The configured
`PATIENT_APPOINTMENT_CANCELLATION_CUTOFF_HOURS` and
`PATIENT_APPOINTMENT_RESCHEDULING_CUTOFF_HOURS` settings default to 24 hours
and accept values from 0 to 720. Patient changes inside the configured cutoff
are rejected. Rescheduling a confirmed appointment returns it to `BOOKED` so
the doctor must confirm the new time.

Appointment states are `BOOKED`, `CONFIRMED`, `REJECTED`, `COMPLETED`,
`CANCELLED`, and `NO_SHOW`. Doctors can confirm/reject booked requests, cancel
active assignments, and complete or mark no-show only after the scheduled end.
Patients can only manage their own appointments; doctors can only manage
appointments assigned to their profile. Admin appointment endpoints are
explicitly read-only. Lifecycle actions and schedule changes are written to
`appointment_audit_events`.

The database overlap exclusion constraint is the final protection against
concurrent overlapping bookings on PostgreSQL. `btree_gist` is installed by
the additive `20261126_0005` migration. SQLite tests exercise API validation
and sequential conflicts, but do not validate PostgreSQL locking or concurrent
transaction behavior; run those checks against the configured PostgreSQL
database before production. This development system does not apply
distributed rate limits; add rate limiting and abuse monitoring before public
deployment.

## Notifications and email worker

Appointment booking, confirmation, cancellation, rescheduling, and completion
create in-app notifications and durable email outbox jobs in the appointment
transaction. New bookings and reschedules also schedule 24-hour and 1-hour
reminders for both participants, subject to their preferences and the
appointment being far enough in the future. Reminder jobs are cancelled or
revalidated when an appointment changes, and preference changes cancel
reminders that are no longer enabled.

Authenticated users can list, mark, and delete their own in-app notifications
and manage preferences:

- `GET /api/v1/notifications`
- `GET /api/v1/notifications/unread-count`
- `PATCH /api/v1/notifications/{notification_id}/read`
- `PATCH /api/v1/notifications/read-all`
- `DELETE /api/v1/notifications/{notification_id}`
- `GET /api/v1/notifications/preferences`
- `PUT /api/v1/notifications/preferences`

Admins can inspect delivery state without seeing message bodies or full email
addresses through `GET /api/v1/admin/notifications/jobs`. Frontend pages are
available at `/notifications` for patients, `/doctor/notifications` for
doctors, `/admin/notifications` for admins, and `/admin/notification-jobs` for
admin monitoring. The API independently enforces authentication and role
checks.

Run the worker in a separate process from `backend/`:

```powershell
python -m app.services.notification_worker
```

It polls every `NOTIFICATION_WORKER_POLL_SECONDS` (default 5), claims due jobs
with a lease, and retries SMTP transport failures with bounded exponential
backoff (`NOTIFICATION_MAX_ATTEMPTS`, `NOTIFICATION_RETRY_BASE_SECONDS`, and
`NOTIFICATION_RETRY_MAX_SECONDS`). Use
`python -m app.services.notification_worker --once` to process one due-job
batch. Configure `SMTP_HOST`, `SMTP_FROM_EMAIL`, `SMTP_PORT`, and TLS/SSL
options in the private backend `.env`; credentials are optional but must be
configured together. `FRONTEND_BASE_URL` is optional and must be an HTTP(S)
URL. SMTP is disabled by default. Email jobs created before SMTP is configured
are recorded as skipped and are not automatically replayed after SMTP is
enabled.

Appointment times remain UTC instants; reminder email display uses
`APPOINTMENT_TIMEZONE` (default `UTC`). Email messages contain appointment
status, date/time, and the other participant's name only; they omit visit
reasons, patient/doctor notes, medical records, and credential documents.
SMTP delivery is at-least-once in the narrow failure case where the remote
server accepts a message but the worker exits before committing the job.
No live SMTP service is included or claimed as tested. Deploy the worker with
the same database settings as the API and monitor failed jobs through the
admin page. Notification processing does not currently have distributed
rate-limiting or an external queue dependency.

## Medical-record storage

Uploads use multipart form data with a title, one of the categories
`Blood Test`, `Prescription`, `Radiology`, `MRI / CT Scan`, `X-Ray`,
`Discharge Summary`, `Laboratory Report`, or `Other`, and a PDF, JPG, JPEG, or
PNG file. The default maximum is 10 MiB per file.

Configure storage with:

- `MEDICAL_RECORDS_STORAGE_DIR` — default `storage/medical-records`, resolved
  relative to `backend/` unless an absolute path is supplied. Keep this
  directory outside the publicly served frontend tree.
- `MEDICAL_RECORDS_MAX_UPLOAD_SIZE_MB` — default `10`, must be a positive
  integer.

The API validates extension, declared MIME type, and file signatures/content,
then stores the file under a random server-generated name. The original
filename is metadata only. API responses never include storage keys or
filesystem paths, and medical files are not served through `StaticFiles`.
`backend/storage/` is excluded from Git.

## Tests

Run from the `backend` directory:

```powershell
python -m pytest
```

Tests use a fresh isolated SQLite database and do not require a running
PostgreSQL server. They cover authentication, patient records, doctor
registration, verification permissions/transitions, private credential
upload/review, appointment availability, booking, ownership, lifecycle
transitions, notification ownership/preferences, SMTP retry handling, and
sequential overlap prevention. Validate migration
upgrade/downgrade/re-upgrade, Alembic metadata parity, concurrent booking, and
worker claiming against PostgreSQL before deployment.

## Security notes

- Passwords are hashed with Argon2id and never returned by API responses.
- JWTs are signed with HS256, expire after the configured interval, and are
  checked against persisted revocations on each authenticated request.
- Patient profile and medical-record routes require the PATIENT role and
  operate only on the identity from the authenticated token. Other patients'
  record IDs return not found.
- Admin verification routes enforce the ADMIN role on the server. Every
  decision is audited; application transition queries use row locking on
  databases that support it. Public discovery filters out unapproved,
  suspended, and inactive doctors.
- Appointment routes enforce PATIENT, DOCTOR, or ADMIN authorization on the
  server and scope all participant queries to the authenticated identity.
  Patient and doctor notes are returned only to authorized participants and
  admins; patient-supplied status and ownership IDs are not accepted.
- PostgreSQL prevents overlapping active appointments with an exclusion
  constraint; booking and rescheduling return `409 Conflict` for races or
  occupied slots. SQLite does not provide the production concurrency guarantee.
- Stored files remain on the local filesystem; this phase does not implement
  antivirus scanning, application-level encryption at rest, production
  backups, or a compliance assessment. No HIPAA, GDPR, or other certification
  is claimed. Do not treat this development configuration as production
  healthcare storage.
- Use HTTPS, a private high-entropy signing key, least-privilege database
  credentials, and managed secret storage outside local development.
- Email verification uses database-backed email/IP throttling and PostgreSQL
  advisory locks for concurrent requests. Rate limits are per application
  database and do not replace edge-level abuse controls or monitoring.
