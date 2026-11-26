# MediCare AI Frontend

Responsive React + TypeScript patient portal built with Vite, Tailwind CSS,
React Router, Axios, Lucide, and Recharts.

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

## Validation

```powershell
npm run typecheck
npm run lint
npm run build
```

The app stores access tokens in `sessionStorage` only. It does not implement
refresh tokens or persist credentials. The patient dashboard marks illustrative
chart data and empty clinical services clearly; it does not display fabricated
medical readings or history.
