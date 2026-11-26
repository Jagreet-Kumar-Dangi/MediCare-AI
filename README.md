# MediCare AI

MediCare AI is a healthcare platform foundation. The backend provides
versioned health checks, account registration and login, JWT authentication,
and patient-owned profile management. The frontend provides the initial
patient portal experience.

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
doctor self-registration, login/logout, current-user authentication, and
patient profile access.

Not implemented: public administrator registration, AI predictions, chatbot,
medical report analysis, appointments, or reminders.
