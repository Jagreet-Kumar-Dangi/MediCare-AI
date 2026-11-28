# MediCare AI Mobile

Flutter application for patient and doctor accounts, built with Material 3,
Riverpod, GoRouter, Dio, Flutter Secure Storage, and a feature-based structure.
Patient features include profile editing, eligible-doctor discovery, and
appointment booking and management. Doctor dashboards remain role-aware; doctor
appointment-management features are not included.

## Run locally

Start the FastAPI development server from `backend/`:

```powershell
python -m uvicorn app.main:app --reload
```

From `mobile/`, run the app on the Android emulator:

```powershell
flutter pub get
flutter run
```

The default API base URL is `http://10.0.2.2:8000/api/v1`, which reaches the
host machine's port 8000 from the Android emulator. Override it with
`--dart-define=MEDICARE_API_URL=https://your-api.example/api/v1` when using a
different environment. Android cleartext HTTP is enabled only for debug builds;
use HTTPS for non-development deployments.

## Authentication

- `POST /api/v1/auth/login` sends `{ "email", "password" }` and receives
  `access_token`, `token_type`, and `expires_in`. The access token is stored
  using Flutter Secure Storage and is never logged.
- `GET /api/v1/auth/me` uses the bearer token and reads the backend's public
  user response (`id`, `email`, `role`, `is_active`, `created_at`).
- `POST /api/v1/auth/register/patient` sends `email`, `password`,
  `first_name`, and `last_name`.
- `POST /api/v1/auth/register/doctor` sends the backend's doctor profile
  fields: `email`, `password`, `full_name`, `specialization`, `qualification`,
  `medical_registration_number`, and `years_of_experience`; optional profile
  fields are sent only when entered.
- Both registration endpoints return the backend's public user fields:
  `id`, `email`, `role`, `is_active`, and `created_at`.
- Registration sends the user to the email-verification screen. The screen
  calls `POST /api/v1/auth/verify-email/confirm` with `{ "email", "code" }`;
  resend uses `/api/v1/auth/verify-email/resend`. Codes are entered in
  transient UI state only and are never saved in Flutter Secure Storage.
- `POST /api/v1/auth/verify-email/send` can request a code for an existing
  unverified account. Send/resend responses are intentionally generic.
- `POST /api/v1/auth/logout` revokes the active token. The app clears its local
  token even if the request fails.
- A `401` while restoring or using a saved session clears the saved token and
  returns the user to sign-in. Network/server errors do not discard a token
  during session restoration.

Patient and doctor accounts cannot sign in until email verification succeeds.
Legacy accounts are prompted to request a verification code before their next
login. Doctor email verification does not approve their profile or credentials;
administrator approval remains required. Patient and doctor roles have
separate dashboard routes. Administrator accounts are intentionally
unsupported in the mobile app.

## Patient features and API contracts

- Patient profile reads and updates use `GET /api/v1/patients/me` and
  `PUT /api/v1/patients/me`. The editable request contains `first_name`,
  `last_name`, `date_of_birth`, and `phone_number`; nullable fields are sent
  explicitly as `null` when cleared. Only fields in the current patient
  profile schema are shown.
- Doctor discovery uses `GET /api/v1/doctors`, with backend-supported
  `search`, `specialization`, `min_experience`, `max_experience`, and
  `max_consultation_fee` filters. Details use `GET /api/v1/doctors/{doctor_id}`.
  The backend limits results to approved, active doctors meeting credential
  eligibility. The app does not infer or display verification fields absent
  from the public response.
- Available clinic slots use
  `GET /api/v1/appointments/available-slots?doctor_id=…&date=YYYY-MM-DD`.
  The app displays slots in the returned clinic timezone and sends the selected
  timezone-aware instant when booking.
- Booking uses `POST /api/v1/appointments` with `doctor_id`,
  `scheduled_start`, `reason_for_visit`, and optional `patient_notes`.
- Patient appointment lists use `GET /api/v1/appointments/me` with `view`
  set to `upcoming`, `history`, or `all`; details use
  `GET /api/v1/appointments/{appointment_id}`.
- Rescheduling uses `PUT /api/v1/appointments/{appointment_id}/reschedule`
  with `scheduled_start` and a reason; cancellation uses
  `POST /api/v1/appointments/{appointment_id}/cancel` with a reason.
  The backend enforces appointment status, conflicts, and configurable
  cancellation/rescheduling cutoffs. A rescheduled confirmed booking requires
  doctor confirmation. Conflict and other API errors are shown to the user.

The app does not include admin functionality, medical records, or doctor-side
appointment management. It does not show ineligible doctors as bookable.

## Project structure

- `lib/app/` — app shell, splash screen, and role-aware GoRouter configuration.
- `lib/core/` — API configuration, Dio, secure storage, theme, errors, and
  shared widgets.
- `lib/features/auth/` — authentication models, repository, controller, login,
  and patient/doctor registration.
- `lib/features/dashboard/` and `lib/features/profile/` — role dashboards and
  account profile.
- `lib/features/patient/` — patient profile API and profile model.
- `lib/features/doctor/` — public directory, filters, doctor details, and
  patient booking form.
- `lib/features/appointment/` — slots, appointment lists/details, cancellation,
  rescheduling, and appointment event history.

## Validation

```powershell
flutter analyze
flutter test
flutter build apk --debug
```

Run `flutter build apk --debug` for an Android debug build. Live workflow
verification against PostgreSQL and the target Android emulator is required
before declaring the patient experience validated; an empty eligible-doctor
directory prevents booking lifecycle verification until a suitable doctor and
availability are present in the backend.
