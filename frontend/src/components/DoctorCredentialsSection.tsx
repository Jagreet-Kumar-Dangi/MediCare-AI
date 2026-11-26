import { useEffect, useRef, useState, type FormEvent } from 'react'
import { getApiErrorMessage } from '../api/errors'
import {
  deleteDoctorCredential,
  downloadDoctorCredential,
  getMyDoctorCredentials,
  uploadDoctorCredential,
} from '../api/doctorCredentials'
import {
  doctorCredentialTypes,
  type DoctorCredential,
  type DoctorCredentialListResponse,
  type DoctorCredentialType,
} from '../types/api'

const credentialLabels: Record<DoctorCredentialType, string> = {
  MEDICAL_REGISTRATION_CERTIFICATE: 'Medical registration certificate',
  MEDICAL_DEGREE_CERTIFICATE: 'Medical degree certificate',
  ADDITIONAL_QUALIFICATION_CERTIFICATE:
    'Additional professional qualification certificate',
}

const mimeTypesByExtension: Record<string, string> = {
  '.pdf': 'application/pdf',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.png': 'image/png',
}

function formatFileSize(fileSize: number): string {
  return fileSize < 1024 * 1024
    ? `${Math.max(1, Math.round(fileSize / 1024))} KB`
    : `${(fileSize / (1024 * 1024)).toFixed(1)} MB`
}

function triggerDownload(blob: Blob, filename: string): void {
  const objectUrl = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = objectUrl
  link.download = filename
  link.click()
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000)
}

interface DoctorCredentialsSectionProps {
  maxUploadSizeMb: number
}

export function DoctorCredentialsSection({
  maxUploadSizeMb,
}: DoctorCredentialsSectionProps) {
  const [data, setData] = useState<DoctorCredentialListResponse | null>(null)
  const [documentType, setDocumentType] = useState<DoctorCredentialType>(
    'MEDICAL_REGISTRATION_CERTIFICATE',
  )
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const fileInput = useRef<HTMLInputElement>(null)

  async function refreshCredentials() {
    try {
      setData(await getMyDoctorCredentials())
      setError(null)
    } catch (requestError) {
      setError(getApiErrorMessage(requestError))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let active = true
    void getMyDoctorCredentials()
      .then((response) => {
        if (active) setData(response)
      })
      .catch((requestError: unknown) => {
        if (active) setError(getApiErrorMessage(requestError))
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [])

  function hasCurrentCredential(type: DoctorCredentialType): boolean {
    if (type === 'ADDITIONAL_QUALIFICATION_CERTIFICATE') return false
    return Boolean(
      data?.credentials.some(
        (credential) =>
          credential.document_type === type &&
          ['PENDING', 'APPROVED'].includes(credential.verification_status),
      ),
    )
  }

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setNotice(null)
    if (!file) {
      setError('Choose a credential file to upload.')
      return
    }
    if (file.size > maxUploadSizeMb * 1024 * 1024) {
      setError(`The file must be no larger than ${maxUploadSizeMb} MiB.`)
      return
    }
    const extension = file.name.slice(file.name.lastIndexOf('.')).toLowerCase()
    if (
      !mimeTypesByExtension[extension] ||
      file.type !== mimeTypesByExtension[extension]
    ) {
      setError('Choose a PDF, JPG, JPEG, or PNG file with a matching file type.')
      return
    }

    setUploading(true)
    setProgress(0)
    try {
      await uploadDoctorCredential(documentType, file, setProgress)
      setNotice('Credential submitted for administrator review.')
      setFile(null)
      if (fileInput.current) fileInput.current.value = ''
      await refreshCredentials()
    } catch (requestError) {
      setError(getApiErrorMessage(requestError))
    } finally {
      setUploading(false)
    }
  }

  async function handleDownload(credential: DoctorCredential) {
    setError(null)
    try {
      const blob = await downloadDoctorCredential(credential.id)
      triggerDownload(blob, credential.original_filename)
    } catch (requestError) {
      setError(getApiErrorMessage(requestError))
    }
  }

  async function handleDelete(credential: DoctorCredential) {
    if (!window.confirm('Delete this pending credential submission?')) return
    setError(null)
    setNotice(null)
    try {
      await deleteDoctorCredential(credential.id)
      setNotice('Pending credential deleted.')
      await refreshCredentials()
    } catch (requestError) {
      setError(getApiErrorMessage(requestError))
    }
  }

  return (
    <section className="space-y-5 rounded-3xl border border-line bg-white p-5 shadow-panel sm:p-7">
      <header>
        <p className="text-xs font-bold uppercase tracking-[0.16em] text-brand-700">
          Credential documents
        </p>
        <h2 className="mt-2 text-xl font-semibold text-ink-950">
          Submit credentials for review
        </h2>
        <p className="mt-2 text-sm leading-6 text-ink-600">
          Upload the required documents to become eligible for public doctor
          discovery. Files remain private and are shared only with authorized
          administrators.
        </p>
      </header>

      {error && (
        <p
          aria-live="polite"
          className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800"
          role="alert"
        >
          {error}
        </p>
      )}
      {notice && (
        <p
          aria-live="polite"
          className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900"
          role="status"
        >
          {notice}
        </p>
      )}

      <form
        className="grid gap-4 rounded-2xl bg-sky-50 p-4 sm:grid-cols-2"
        onSubmit={(event) => void handleUpload(event)}
      >
        <label className="space-y-2 text-sm font-semibold text-ink-800">
          Document type
          <select
            className="min-h-11 w-full rounded-xl border border-line bg-white px-3 text-sm font-normal"
            onChange={(event) => {
              const nextType = doctorCredentialTypes.find(
                (type) => type === event.target.value,
              )
              if (nextType) setDocumentType(nextType)
            }}
            value={documentType}
          >
            {doctorCredentialTypes.map((type) => (
              <option
                disabled={hasCurrentCredential(type)}
                key={type}
                value={type}
              >
                {credentialLabels[type]}
                {data?.required_document_types.includes(type)
                  ? ' (required)'
                  : ''}
                {hasCurrentCredential(type) ? ' (already submitted)' : ''}
              </option>
            ))}
          </select>
        </label>
        <label className="space-y-2 text-sm font-semibold text-ink-800">
          Credential file
          <input
            accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png"
            className="block min-h-11 w-full rounded-xl border border-line bg-white px-3 py-2 text-sm font-normal file:mr-3 file:rounded-lg file:border-0 file:bg-brand-100 file:px-3 file:py-1 file:font-semibold file:text-brand-800"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            ref={fileInput}
            required
            type="file"
          />
        </label>
        <div className="flex flex-wrap items-center justify-between gap-3 sm:col-span-2">
          <p className="text-xs text-ink-600">
            PDF, JPG, JPEG, or PNG · Maximum {maxUploadSizeMb} MiB
          </p>
          <button
            className="min-h-10 rounded-xl bg-brand-700 px-4 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
            disabled={uploading || loading || !file}
            type="submit"
          >
            {uploading ? `Uploading ${progress}%…` : 'Upload credential'}
          </button>
        </div>
        {uploading && (
          <progress
            aria-label="Credential upload progress"
            className="h-2 w-full accent-brand-700 sm:col-span-2"
            max={100}
            value={progress}
          />
        )}
      </form>

      {loading ? (
        <p className="rounded-2xl border border-line p-4 text-sm text-ink-600">
          Loading your credentials…
        </p>
      ) : !data || data.credentials.length === 0 ? (
        <p className="rounded-2xl border border-dashed border-line p-5 text-sm text-ink-600">
          No credential documents have been submitted yet.
        </p>
      ) : (
        <div className="space-y-3">
          <div
            className={`rounded-2xl p-4 text-sm font-semibold ${
              data.directory_eligible
                ? 'bg-emerald-50 text-emerald-900'
                : 'bg-amber-50 text-amber-900'
            }`}
            role="status"
          >
            {data.directory_eligible
              ? 'Your profile is eligible for doctor discovery.'
              : data.required_document_types.length > 0
                ? 'Your profile is not yet eligible for doctor discovery. Required credentials and doctor profile approval are both needed.'
                : 'Your profile is not yet eligible for doctor discovery. Doctor profile approval is required.'}
          </div>
          <ul className="divide-y divide-line rounded-2xl border border-line">
            {data.credentials.map((credential) => (
              <li
                className="flex flex-wrap items-center justify-between gap-4 p-4"
                key={credential.id}
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-ink-950">
                    {credentialLabels[credential.document_type]}
                  </p>
                  <p className="mt-1 truncate text-xs text-ink-600">
                    {credential.original_filename} ·{' '}
                    {formatFileSize(credential.file_size)} · Submitted{' '}
                    {new Date(credential.submitted_at).toLocaleDateString()}
                  </p>
                  <p
                    className={`mt-2 inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${
                      credential.verification_status === 'APPROVED'
                        ? 'bg-emerald-50 text-emerald-900'
                        : credential.verification_status === 'REJECTED'
                          ? 'bg-rose-50 text-rose-900'
                          : 'bg-amber-50 text-amber-900'
                    }`}
                  >
                    {credential.verification_status}
                  </p>
                  {credential.rejection_reason && (
                    <p className="mt-2 max-w-2xl text-sm text-rose-800">
                      Review reason: {credential.rejection_reason}
                    </p>
                  )}
                  {credential.reviewed_at && (
                    <p className="mt-1 text-xs text-ink-600">
                      Reviewed{' '}
                      {new Date(credential.reviewed_at).toLocaleString()}
                    </p>
                  )}
                </div>
                <div className="flex gap-2">
                  <button
                    className="min-h-9 rounded-lg border border-line px-3 text-xs font-semibold text-ink-800 hover:bg-sky-50"
                    onClick={() => void handleDownload(credential)}
                    type="button"
                  >
                    Download
                  </button>
                  {credential.verification_status === 'PENDING' && (
                    <button
                      className="min-h-9 rounded-lg border border-rose-200 px-3 text-xs font-semibold text-rose-800 hover:bg-rose-50"
                      onClick={() => void handleDelete(credential)}
                      type="button"
                    >
                      Delete
                    </button>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  )
}
