# MediCare AI

MediCare AI is a healthcare platform foundation. The backend provides
versioned health checks, account registration and login, JWT authentication,
patient-owned profile and medical-record management, and doctor verification
and discovery. The frontend provides patient, doctor, and administrator
workspaces for the implemented features.

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
profile and medical-record management, doctor verification and approved
doctor discovery. Doctor credential documents and appointment management are
not implemented yet. Medical files remain in private local development
storage; this is not a compliance certification.

There is no public administrator registration; trusted operators provision
admins with `python -m app.cli create-admin` from `backend/`. AI predictions,
chatbot, medical-report analysis, appointments, and reminders are not
implemented. Medical-record uploads are not sent to an AI service.
