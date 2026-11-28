# MediCare AI

MediCare AI is a healthcare platform foundation. The backend provides
versioned health checks, account registration and login, JWT authentication,
patient-owned profile and medical-record management, doctor verification and
discovery, private doctor credentials, appointment scheduling, and appointment
notifications. The frontend provides patient, doctor, and administrator
workspaces for these features.

## Project layout

- `backend/` — FastAPI, SQLAlchemy, Alembic migrations, and tests.
- `frontend/` — React + TypeScript patient portal.
- `mobile/` — Flutter patient/doctor authentication and app foundation.
- `ml/`, `infrastructure/`, `docs/` — reserved areas for future work.
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

The backend README documents the manual local PostgreSQL and private-upload
backup/restore procedure. Automated backups and a production recovery plan are
not provided.

## Frontend quick start

See [frontend/README.md](frontend/README.md). With Node.js 22 or later, from
`frontend/`:

```powershell
npm ci
Copy-Item .env.example .env
npm run dev
```

The Vite development server uses port 5173, which is allowed by the backend's
development CORS configuration.

## Mobile quick start

See [mobile/README.md](mobile/README.md). From `mobile/`, run `flutter pub get`
and `flutter run`. Android emulators use `http://10.0.2.2:8000/api/v1` to reach
the host's development API at port 8000.

## Phase scope

Implemented: backend foundation, PATIENT/DOCTOR/ADMIN role model, patient and
doctor registration, login/logout, current-user authentication, patient
profile and medical-record management, doctor verification, private doctor
credential submission and review, approved-doctor discovery, doctor
availability, appointment booking and management, in-app appointment
notifications, email outbox processing, and configurable appointment reminders
(Phase 6 migration and PostgreSQL schema verification are complete locally).
Medical and credential files remain in private local development storage; this
is not a compliance certification.

Doctor credentials support PDF, JPG, JPEG, and PNG uploads up to 10 MiB by
default. Registration and degree certificates are required for directory
eligibility by default; configure `REQUIRED_DOCTOR_CREDENTIAL_TYPES` in
`backend/.env` to change the required set. Admin-only review actions are
audited. See [backend/README.md](backend/README.md) for routes and storage
configuration.

There is no public administrator registration; trusted operators provision
admins with `python -m app.cli create-admin` from `backend/`. AI predictions,
chatbot, and medical-report analysis are not implemented.
Appointments are stored in UTC; `APPOINTMENT_TIMEZONE` configures the clinic
timezone used for weekly availability and display. Patient cancellation and
rescheduling are restricted inside a configurable 24-hour cutoff by default.
See [backend/README.md](backend/README.md) for scheduling APIs and rules.
Medical-record uploads are not sent to an AI service.

Appointment lifecycle notifications are persisted with their appointment
transactions. In-app notifications and 24-hour/1-hour reminders are available
to authenticated users; email delivery is optional and requires SMTP settings
plus the separately running notification worker. Configure SMTP before
creating events if those emails must be delivered: email jobs created without
SMTP are recorded as skipped and are not automatically replayed later. See
[backend/README.md](backend/README.md) for worker operation and delivery
limitations.

Administrators can use the Phase 7 analytics workspace for database-backed
aggregate user, doctor, appointment, and notification reports. Reporting
periods use the `Asia/Kolkata` clinic timezone with UTC database timestamps;
the dashboard and CSV exports exclude patient medical records, private
credential documents, and notification message contents. Analytics access is
restricted to administrator accounts. See the backend and frontend READMEs for
endpoint definitions, filters, status calculations, and export behavior.

## Phase 8C email verification status

Patient and doctor registration require a six-digit email OTP delivered by
backend Gmail SMTP. The additive PostgreSQL migration is
`20261128_0008`; SMTP credentials belong only in the ignored `backend/.env`.
The backend and React live flows were verified with disposable accounts and a
controlled Gmail inbox: patient login and `/auth/me` worked after verification,
unverified login and an incorrect OTP were rejected, React resend/verification
worked, and the verified doctor's professional approval remained `PENDING`.
Disposable test records were cleaned up.

Backend tests passed (77); React typecheck, lint, build, and five tests passed.
Flutter analysis is clean, six tests pass, and the debug APK builds. Live
Flutter verification is not complete: after a reported installation, the
Pixel 7 login screen was still observed without the source's
verification-recovery link, so no registration, OTP, login, or protected
`/me` flow has yet been confirmed in the app. The latest emulator capture is
the Android launcher setup screen. Reopen the current app and complete those
device flows before declaring Phase 8C complete.
