/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string
  readonly VITE_MEDICAL_RECORDS_MAX_UPLOAD_SIZE_MB?: string
  readonly VITE_DOCTOR_CREDENTIALS_MAX_UPLOAD_SIZE_MB?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
