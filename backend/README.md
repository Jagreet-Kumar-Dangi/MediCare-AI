# MediCare AI Backend

The backend provides the Phase 1 FastAPI foundation and Phase 2 authentication,
PostgreSQL persistence, and patient profile APIs. It does not include AI
predictions, chatbot features, or medical report analysis.

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
| POST | `/api/v1/auth/register/doctor` | Register a doctor |
| POST | `/api/v1/auth/login` | Issue a short-lived JWT access token |
| GET | `/api/v1/auth/me` | Return the authenticated user's public details |
| POST | `/api/v1/auth/logout` | Revoke the current access token |
| GET | `/api/v1/patients/me` | Read the authenticated patient's profile |
| PUT | `/api/v1/patients/me` | Replace the authenticated patient's profile |

Patient and doctor registration assign their roles on the server. There is no
public administrator registration endpoint; administrator accounts must be
provisioned through a trusted operational process. Protected routes use
`Authorization: Bearer <access_token>`.

## Tests

Run from the `backend` directory:

```powershell
python -m pytest
```

Tests use a fresh in-memory SQLite database and do not require a running
PostgreSQL server.

## Security notes

- Passwords are hashed with Argon2id and never returned by API responses.
- JWTs are signed with HS256, expire after the configured interval, and are
  checked against persisted revocations on each authenticated request.
- Patient profile routes require the PATIENT role and expose only the current
  user's profile.
- Use HTTPS, a private high-entropy signing key, least-privilege database
  credentials, and managed secret storage outside local development.
