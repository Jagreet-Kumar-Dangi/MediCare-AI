# MediCare AI Backend

The backend provides the FastAPI foundation, authentication, PostgreSQL
persistence, patient profiles, private local medical-record management, doctor
verification and discovery, and private doctor credential submission/review.
The backend also provides appointment scheduling and management. AI features
are not implemented.

## Requirements

- Python 3.13.3
- PostgreSQL for local API development
- Dependencies from `requirements.txt`

## Setup (Windows PowerShell)

From the `backend` directory:

```powershell
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
The extension is intentionally retained on downgrade. To roll back only the
appointment revision:

```powershell
python -m alembic downgrade 20261126_0004
```

Rolling back revision `20261126_0005` removes availability and appointment
tables and their records; back up required scheduling data before downgrading.
Earlier migrations are additive and must not be rewritten.

To create a migration after changing models:

```powershell
python -m alembic revision --autogenerate -m "describe the schema change"
```

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

tests use a fresh in-memory SQLite database and do not require a running
PostgreSQL server. They cover authentication, patient records, doctor
registration, verification permissions/transitions, private credential
upload/review, appointment availability, booking, ownership, lifecycle
transitions, and sequential overlap prevention. Validate migration
upgrade/downgrade/re-upgrade, Alembic metadata parity, and concurrent booking
against PostgreSQL before deployment.

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
- Authentication and doctor registration currently have no rate limiting.
  Add distributed rate limits and abuse monitoring before public deployment.
