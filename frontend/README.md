# MediCare AI Frontend

Responsive React + TypeScript healthcare portal built with Vite, Tailwind CSS,
React Router, Axios, Lucide, and Recharts. The current frontend includes
patient profile and medical-record pages, doctor registration/status and
discovery, and an administrator doctor-verification workspace.

## Setup

Use Node.js 22 or later. From this directory:

```powershell
npm install
Copy-Item .env.example .env
npm run dev
```

`VITE_API_BASE_URL` in `.env` should point to the FastAPI v1 API. The default
is `http://127.0.0.1:8000/api/v1`. The backend allows both `localhost:5173`
and `127.0.0.1:5173` in its development CORS configuration.
`VITE_MEDICAL_RECORDS_MAX_UPLOAD_SIZE_MB` controls the client-side upload
validation limit and defaults to `10`; keep it aligned with the backend's
`MEDICAL_RECORDS_MAX_UPLOAD_SIZE_MB`.

## Validation

```powershell
npm run typecheck
npm run lint
npm run build
```

The app stores access tokens in `sessionStorage` only. It does not implement
refresh tokens or persist credentials. Route guards use the authenticated
role, while all authorization is enforced again by the backend. Doctor
applications default to pending, and discovery lists only approved active
doctors. Appointment booking, availability, and private credential-document
upload/review are not implemented yet. The patient dashboard marks
illustrative chart data clearly and does not display fabricated medical
readings or history. Medical report files are uploaded to the authenticated
backend and are not stored in frontend assets or browser storage.
