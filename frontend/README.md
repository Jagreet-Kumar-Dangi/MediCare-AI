# MediCare AI Frontend

Responsive React + TypeScript healthcare portal built with Vite, Tailwind CSS,
React Router, Axios, Lucide, and Recharts. The current frontend includes
patient profile and medical-record pages, doctor registration/status,
credential submission, approved-doctor discovery, and administrator doctor
and credential verification workspaces. It also provides patient booking and
appointment history, doctor availability and appointment management, and a
read-only administrator appointment overview, appointment notifications and
preferences, and an administrator notification-job monitor.

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
`VITE_DOCTOR_CREDENTIALS_MAX_UPLOAD_SIZE_MB` controls the doctor credential
upload validation limit and defaults to `10`; keep it aligned with the
backend's `DOCTOR_CREDENTIALS_MAX_UPLOAD_SIZE_MB`.

## Validation

```powershell
npm run typecheck
npm run lint
npm test
npm run build
```

Patient and doctor registration routes to a six-digit email verification
screen. The code remains only in component memory; it is not persisted to
browser storage. Verified users must sign in before protected routes are
available. Existing patient/doctor accounts are prompted to verify on login;
doctor verification does not replace administrator approval or credential
review. SMTP credentials remain backend-only.

The app stores access tokens in `sessionStorage` only. It does not implement
refresh tokens or persist credentials. Route guards use the authenticated
role, while all authorization is enforced again by the backend. Doctor
applications default to pending, and discovery lists only approved active
doctors with all configured required credentials approved. Doctors can upload
and track private credentials in their workspace; admins review and download
credentials from their protected workspace. Patients can request appointments
from eligible doctors, cancel or reschedule outside the configured cutoff,
and view appointment history. Doctors manage weekly availability, breaks,
unavailable dates, and assigned appointment requests. Administrators can
inspect appointment details and audit history but cannot alter bookings.
All authorization is also enforced by the backend. Authenticated users can
review and manage their own in-app notifications and delivery preferences.
The administrator notification monitor shows masked recipient and job status
metadata only. Email delivery requires the separately configured backend
worker and SMTP service. The patient dashboard marks
illustrative chart data clearly and does not display fabricated medical
readings or history. Medical report files are uploaded to the authenticated
backend and are not stored in frontend assets or browser storage.

Administrators can open the protected `/admin/analytics` workspace for live
aggregate metrics, patient and doctor registration trends, appointment status
and lifecycle charts, notification job/retry counts, per-doctor operational
counts, and CSV downloads. Date filters use the backend's `Asia/Kolkata`
reporting calendar. The dashboard does not display patient medical records,
private credential files, notification recipients, or message contents. Trend
charts use Recharts and show an explicit empty state when the selected range
has no records.
