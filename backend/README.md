# MediCare AI Backend

The backend provides the FastAPI foundation, authentication, PostgreSQL
persistence, patient profiles, private local medical-record management, and
doctor verification and discovery. Appointment scheduling and AI features are
not implemented in this subphase.

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
verification audit trail are added by `20261126_0003`. To roll back the latest
doctor-verification revision:

```powershell
python -m alembic downgrade 20261126_0002
```

Rolling back revision `20261126_0003` removes its doctor and audit tables; do
not downgrade a database containing doctor accounts unless that data loss is
intended and backed up.

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

The current review workflow collects profile data and the registration number
only. Private credential-document upload/download and automated verification
are not implemented yet; use an approved, trusted manual verification process
before approving an application. No appointment, availability, rate-limiting,
or document-scanning APIs are part of this subphase.

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

Tests use a fresh in-memory SQLite database and do not require a running
PostgreSQL server. They cover authentication, patient records, doctor
registration, verification permissions/transitions, audit records, and
approved-doctor discovery. Migration upgrade/downgrade/re-upgrade and
Alembic metadata parity should be checked on a disposable database before
deployment.

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
- Stored files remain on the local filesystem; this phase does not implement
  antivirus scanning, application-level encryption at rest, production
  backups, or a compliance assessment. No HIPAA, GDPR, or other certification
  is claimed. Do not treat this development configuration as production
  healthcare storage.
- Use HTTPS, a private high-entropy signing key, least-privilege database
  credentials, and managed secret storage outside local development.
- Authentication and doctor registration currently have no rate limiting.
  Add distributed rate limits and abuse monitoring before public deployment.
