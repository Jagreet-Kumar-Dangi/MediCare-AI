# MediCare AI

MediCare AI is a healthcare platform foundation. The backend provides
versioned health checks, account registration and login, JWT authentication,
patient-owned profile and medical-record management, and doctor verification
and discovery, private doctor credentials, and appointment scheduling. The
frontend provides patient, doctor, and administrator workspaces for these
features.

## Project layout

- `backend/` — FastAPI, SQLAlchemy, Alembic migrations, and tests.
- `frontend/` — React + TypeScript patient portal.
- `mobile/`, `ml/`, `infrastructure/`, `docs/` — reserved areas for future
  application and platform work.
- `PROJECT_CONTEXT.md` — current architecture, scope, and implementation
  constraints.

## Backend quick start

See [backend/README.md](backend/README.md) for the full setup. From
`backend/`, configure PostgreSQL and a private `JWT_SECRET_KEY` in `.env`, apply
the migration, then run:

```powershell
python -m alembic upgrade head
python -m uvicorn app.main:app --reload
```

Run the backend tests with:

```powershell
python -m pytest
```

The tests use isolated SQLite databases. The API docs are available at
`http://127.0.0.1:8000/docs`.

## Frontend quick start

See [frontend/README.md](frontend/README.md). With Node.js 22 or later, from
`frontend/`:

```powershell
npm install
Copy-Item .env.example .env
npm run dev
```

The Vite development server uses port 5173, which is allowed by the backend's
development CORS configuration.

## Phase scope

Implemented: backend foundation, PATIENT/DOCTOR/ADMIN role model, patient and
doctor registration, login/logout, current-user authentication, patient
profile and medical-record management, doctor verification, private doctor
credential submission and review, approved-doctor discovery, doctor
availability, and appointment booking and management. Medical and credential
files remain in private local development storage; this is not a compliance
certification.

Doctor credentials support PDF, JPG, JPEG, and PNG uploads up to 10 MiB by
default. Registration and degree certificates are required for directory
eligibility by default; configure `REQUIRED_DOCTOR_CREDENTIAL_TYPES` in
`backend/.env` to change the required set. Admin-only review actions are
audited. See [backend/README.md](backend/README.md) for routes and storage
configuration.

There is no public administrator registration; trusted operators provision
admins with `python -m app.cli create-admin` from `backend/`. AI predictions,
chatbot, medical-report analysis, and reminders are not implemented.
Appointments are stored in UTC; `APPOINTMENT_TIMEZONE` configures the clinic
timezone used for weekly availability and display. Patient cancellation and
rescheduling are restricted inside a configurable 24-hour cutoff by default.
See [backend/README.md](backend/README.md) for scheduling APIs and rules.
Medical-record uploads are not sent to an AI service.
