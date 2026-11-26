import {
  AlertCircle,
  ArrowDownToLine,
  CalendarDays,
  Check,
  FileHeart,
  FileText,
  LoaderCircle,
  Plus,
  RotateCcw,
  Search,
  Trash2,
  Upload,
  X,
} from 'lucide-react'
import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type ChangeEvent,
  type DragEvent,
  type FormEvent,
} from 'react'
import { getApiErrorMessage } from '../api/errors'
import {
  deleteMedicalRecord,
  downloadMedicalRecord,
  getMedicalRecord,
  getMedicalRecords,
  uploadMedicalRecord,
} from '../api/medicalRecords'
import { FormField } from '../components/FormField'
import {
  medicalRecordCategories,
  type MedicalRecord,
  type MedicalRecordCategory,
} from '../types/api'

const MIME_TYPES_BY_EXTENSION: Record<string, string> = {
  '.pdf': 'application/pdf',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.png': 'image/png',
}

const DEFAULT_MAX_UPLOAD_SIZE_MB = 10
const configuredMaxUploadSize = import.meta.env
  .VITE_MEDICAL_RECORDS_MAX_UPLOAD_SIZE_MB
const parsedMaxUploadSize = configuredMaxUploadSize
  ? Number(configuredMaxUploadSize)
  : DEFAULT_MAX_UPLOAD_SIZE_MB
const hasValidMaxUploadSize =
  Number.isInteger(parsedMaxUploadSize) && parsedMaxUploadSize > 0
const maxUploadSizeMb = hasValidMaxUploadSize
  ? parsedMaxUploadSize
  : DEFAULT_MAX_UPLOAD_SIZE_MB
const maxUploadSizeBytes = maxUploadSizeMb * 1024 * 1024

function getFileValidationError(file: File): string | null {
  const extension = file.name.slice(file.name.lastIndexOf('.')).toLowerCase()
  const expectedMimeType = MIME_TYPES_BY_EXTENSION[extension]
  if (!expectedMimeType) {
    return 'Choose a PDF, JPG, JPEG, or PNG file.'
  }
  if (file.type !== expectedMimeType) {
    return 'The selected file type does not match its extension.'
  }
  if (file.size === 0) {
    return 'The selected file is empty.'
  }
  if (!hasValidMaxUploadSize) {
    return 'The upload size limit is not configured correctly. Contact support.'
  }
  if (file.size > maxUploadSizeBytes) {
    return `Choose a file smaller than ${maxUploadSizeMb} MB.`
  }
  return null
}

function formatFileSize(fileSize: number): string {
  if (fileSize < 1024) return `${fileSize} bytes`
  if (fileSize < 1024 * 1024) {
    return `${(fileSize / 1024).toFixed(1)} KB`
  }
  return `${(fileSize / (1024 * 1024)).toFixed(2)} MB`
}

function formatDate(value: string | null): string {
  if (!value) return 'Date not provided'
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(
    new Date(`${value}T00:00:00`),
  )
}

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

export function MedicalRecordsPage() {
  const [records, setRecords] = useState<MedicalRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [reloadKey, setReloadKey] = useState(0)
  const [uploadOpen, setUploadOpen] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [title, setTitle] = useState('')
  const [category, setCategory] = useState<MedicalRecordCategory>('Other')
  const [description, setDescription] = useState('')
  const [reportDate, setReportDate] = useState('')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [search, setSearch] = useState('')
  const [categoryFilter, setCategoryFilter] = useState<
    MedicalRecordCategory | 'All'
  >('All')
  const [detailsRecord, setDetailsRecord] = useState<MedicalRecord | null>(null)
  const [detailsLoading, setDetailsLoading] = useState(false)
  const [detailsError, setDetailsError] = useState<string | null>(null)
  const [recordToDelete, setRecordToDelete] = useState<MedicalRecord | null>(
    null,
  )
  const [deleting, setDeleting] = useState(false)
  const [downloadingId, setDownloadingId] = useState<number | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    let active = true
    void getMedicalRecords()
      .then((result) => {
        if (active) setRecords(result)
      })
      .catch((error: unknown) => {
        if (active) setLoadError(getApiErrorMessage(error))
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [reloadKey])

  const filteredRecords = useMemo(() => {
    const normalizedSearch = search.trim().toLocaleLowerCase()
    return records.filter((record) => {
      const matchesCategory =
        categoryFilter === 'All' || record.category === categoryFilter
      const matchesSearch = record.title
        .toLocaleLowerCase()
        .includes(normalizedSearch)
      return matchesCategory && matchesSearch
    })
  }, [categoryFilter, records, search])

  function retryLoading() {
    setLoadError(null)
    setLoading(true)
    setReloadKey((value) => value + 1)
  }

  function resetUploadForm() {
    setTitle('')
    setCategory('Other')
    setDescription('')
    setReportDate('')
    setSelectedFile(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  function selectFile(file: File | undefined) {
    if (!file) return
    const validationError = getFileValidationError(file)
    if (validationError) {
      setSelectedFile(null)
      setUploadError(validationError)
      if (fileInputRef.current) fileInputRef.current.value = ''
      return
    }
    setUploadError(null)
    setSelectedFile(file)
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    selectFile(event.target.files?.[0])
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault()
    setIsDragging(false)
    selectFile(event.dataTransfer.files[0])
  }

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setUploadError(null)
    setActionError(null)
    setSuccess(null)

    if (!hasValidMaxUploadSize) {
      setUploadError(
        'The upload size limit is not configured correctly. Contact support.',
      )
      return
    }
    if (!title.trim()) {
      setUploadError('Enter a title for this report.')
      return
    }
    if (!selectedFile) {
      setUploadError('Choose a report file to upload.')
      return
    }
    const fileError = getFileValidationError(selectedFile)
    if (fileError) {
      setUploadError(fileError)
      return
    }

    setUploading(true)
    setUploadProgress(0)
    try {
      const uploadedRecord = await uploadMedicalRecord(
        {
          title: title.trim(),
          category,
          description: description.trim() || undefined,
          report_date: reportDate || undefined,
          file: selectedFile,
        },
        setUploadProgress,
      )
      setRecords((current) => [
        uploadedRecord,
        ...current.filter((record) => record.id !== uploadedRecord.id),
      ])
      resetUploadForm()
      setUploadOpen(false)
      setSuccess('Your medical record was uploaded.')
      try {
        setRecords(await getMedicalRecords())
      } catch (refreshError) {
        setActionError(
          `The upload succeeded, but the record list could not be refreshed. ${getApiErrorMessage(refreshError)}`,
        )
      }
    } catch (error) {
      setUploadError(getApiErrorMessage(error))
    } finally {
      setUploading(false)
    }
  }

  async function showDetails(record: MedicalRecord) {
    setDetailsRecord(record)
    setDetailsLoading(true)
    setDetailsError(null)
    try {
      setDetailsRecord(await getMedicalRecord(record.id))
    } catch (error) {
      setDetailsError(getApiErrorMessage(error))
    } finally {
      setDetailsLoading(false)
    }
  }

  async function handleDownload(record: MedicalRecord) {
    setDownloadingId(record.id)
    setActionError(null)
    try {
      const file = await downloadMedicalRecord(record.id)
      const url = URL.createObjectURL(file)
      const link = document.createElement('a')
      link.href = url
      link.download = record.original_filename
      link.hidden = true
      document.body.append(link)
      link.click()
      link.remove()
      window.setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch (error) {
      setActionError(getApiErrorMessage(error))
    } finally {
      setDownloadingId(null)
    }
  }

  async function confirmDelete() {
    if (!recordToDelete) return
    setDeleting(true)
    setActionError(null)
    try {
      await deleteMedicalRecord(recordToDelete.id)
      setRecords((current) =>
        current.filter((record) => record.id !== recordToDelete.id),
      )
      if (detailsRecord?.id === recordToDelete.id) setDetailsRecord(null)
      setSuccess('The medical record and its stored file were deleted.')
      setRecordToDelete(null)
    } catch (error) {
      setActionError(getApiErrorMessage(error))
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className="page-enter mx-auto max-w-[1100px] space-y-6">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-brand-700">
            Your private files
          </p>
          <h2 className="mt-2 text-3xl font-semibold tracking-[-0.045em] text-ink-950">
            Medical records
          </h2>
          <p className="mt-2 max-w-[650px] text-sm leading-6 text-ink-600">
            Upload and manage reports in your patient account. Files are not
            sent to an AI service or shared with other patients.
          </p>
        </div>
        <button
          className="inline-flex min-h-11 shrink-0 items-center justify-center gap-2 rounded-xl bg-brand-700 px-5 text-sm font-bold text-white transition hover:bg-brand-600"
          onClick={() => {
            setUploadOpen((open) => !open)
            setUploadError(null)
          }}
          type="button"
        >
          {uploadOpen ? <X aria-hidden="true" size={17} /> : <Plus aria-hidden="true" size={17} />}
          {uploadOpen ? 'Close upload form' : 'Upload report'}
        </button>
      </header>

      {success && (
        <div
          aria-live="polite"
          className="flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-800"
          role="status"
        >
          <Check aria-hidden="true" size={16} />
          {success}
        </div>
      )}
      {actionError && (
        <div
          aria-live="polite"
          className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800"
          role="alert"
        >
          {actionError}
        </div>
      )}

      {uploadOpen && (
        <section
          aria-labelledby="upload-report-heading"
          className="overflow-hidden rounded-[24px] border border-line bg-white shadow-sm"
        >
          <div className="border-b border-line bg-sky-50/75 px-5 py-5 sm:px-7">
            <div className="flex items-center gap-3">
              <span className="grid size-11 place-items-center rounded-2xl bg-white text-brand-700 shadow-sm">
                <Upload aria-hidden="true" size={19} />
              </span>
              <div>
                <h3
                  className="text-sm font-bold text-ink-950"
                  id="upload-report-heading"
                >
                  Add a medical record
                </h3>
                <p className="mt-0.5 text-xs text-ink-600">
                  PDF, JPG, JPEG, or PNG · up to {maxUploadSizeMb} MB
                </p>
              </div>
            </div>
          </div>

          <form
            className="space-y-5 p-5 sm:p-7"
            onSubmit={(event) => void handleUpload(event)}
          >
            {uploadError && (
              <div
                aria-live="polite"
                className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800"
                role="alert"
              >
                {uploadError}
              </div>
            )}

            <div className="grid gap-5 sm:grid-cols-2">
              <FormField
                id="medical-record-title"
                label="Report title"
                maxLength={200}
                onChange={(event) => setTitle(event.target.value)}
                placeholder="For example, annual blood work"
                required
                value={title}
              />
              <div className="space-y-2">
                <label
                  className="block text-sm font-semibold text-ink-800"
                  htmlFor="medical-record-category"
                >
                  Category
                </label>
                <select
                  className="min-h-12 w-full rounded-xl border border-line bg-white px-4 py-3 text-[15px] text-ink-950 outline-none transition focus:border-brand-600 focus:ring-4 focus:ring-brand-100"
                  id="medical-record-category"
                  onChange={(event) =>
                    setCategory(event.target.value as MedicalRecordCategory)
                  }
                  value={category}
                >
                  {medicalRecordCategories.map((recordCategory) => (
                    <option key={recordCategory} value={recordCategory}>
                      {recordCategory}
                    </option>
                  ))}
                </select>
              </div>
              <FormField
                id="medical-record-date"
                label="Report date (optional)"
                onChange={(event) => setReportDate(event.target.value)}
                type="date"
                value={reportDate}
              />
              <div className="space-y-2 sm:col-span-2">
                <label
                  className="block text-sm font-semibold text-ink-800"
                  htmlFor="medical-record-description"
                >
                  Description (optional)
                </label>
                <textarea
                  className="min-h-24 w-full resize-y rounded-xl border border-line bg-white px-4 py-3 text-[15px] text-ink-950 outline-none transition placeholder:text-ink-600/55 focus:border-brand-600 focus:ring-4 focus:ring-brand-100"
                  id="medical-record-description"
                  maxLength={2000}
                  onChange={(event) => setDescription(event.target.value)}
                  placeholder="Add a short note to help you identify this report."
                  value={description}
                />
              </div>
            </div>

            <div
              aria-label="Drop a medical report file here"
              className={`rounded-2xl border-2 border-dashed p-5 text-center transition sm:p-7 ${
                isDragging
                  ? 'border-brand-600 bg-brand-100/70'
                  : 'border-line bg-sky-50/50 hover:border-brand-600/50'
              }`}
              onDragEnter={(event) => {
                event.preventDefault()
                setIsDragging(true)
              }}
              onDragLeave={(event) => {
                event.preventDefault()
                setIsDragging(false)
              }}
              onDragOver={(event) => event.preventDefault()}
              onDrop={handleDrop}
              role="region"
            >
              <input
                accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png"
                className="sr-only"
                id="medical-record-file"
                onChange={handleFileChange}
                ref={fileInputRef}
                type="file"
              />
              <span className="mx-auto grid size-12 place-items-center rounded-2xl bg-white text-brand-700 shadow-sm">
                <FileText aria-hidden="true" size={21} />
              </span>
              <p className="mt-3 text-sm font-semibold text-ink-950">
                Drag a report here, or choose a file
              </p>
              <p className="mt-1 text-xs text-ink-600">
                Supported files up to {maxUploadSizeMb} MB
              </p>
              <label
                className="mt-4 inline-flex min-h-10 cursor-pointer items-center justify-center rounded-xl border border-line bg-white px-4 text-sm font-semibold text-ink-800 transition hover:bg-sky-50"
                htmlFor="medical-record-file"
              >
                Choose file
              </label>
              {selectedFile && (
                <div className="mx-auto mt-4 flex max-w-xl items-center justify-between gap-3 rounded-xl border border-line bg-white px-4 py-3 text-left">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-ink-950">
                      {selectedFile.name}
                    </p>
                    <p className="text-xs text-ink-600">
                      {formatFileSize(selectedFile.size)}
                    </p>
                  </div>
                  <button
                    aria-label="Remove selected file"
                    className="grid size-9 shrink-0 place-items-center rounded-lg text-ink-600 hover:bg-sky-50 hover:text-ink-950"
                    disabled={uploading}
                    onClick={() => {
                      setSelectedFile(null)
                      if (fileInputRef.current) fileInputRef.current.value = ''
                    }}
                    type="button"
                  >
                    <X aria-hidden="true" size={16} />
                  </button>
                </div>
              )}
            </div>

            {uploading && (
              <div className="space-y-2" role="status">
                <div className="flex items-center justify-between text-xs font-medium text-ink-600">
                  <span>Uploading securely…</span>
                  <span>{uploadProgress}%</span>
                </div>
                <div
                  aria-label="Upload progress"
                  aria-valuemax={100}
                  aria-valuemin={0}
                  aria-valuenow={uploadProgress}
                  className="h-2 overflow-hidden rounded-full bg-sky-100"
                  role="progressbar"
                >
                  <div
                    className="h-full rounded-full bg-brand-600 transition-[width]"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
              </div>
            )}

            <div className="flex flex-col-reverse gap-3 border-t border-line pt-5 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-xs leading-5 text-ink-600">
                Files are stored privately for your account. No antivirus
                scanning or compliance certification is claimed.
              </p>
              <button
                className="inline-flex min-h-11 shrink-0 items-center justify-center gap-2 rounded-xl bg-brand-700 px-5 text-sm font-bold text-white transition hover:bg-brand-600 disabled:cursor-not-allowed disabled:opacity-60"
                disabled={uploading}
                type="submit"
              >
                {uploading ? (
                  <>
                    <LoaderCircle
                      aria-hidden="true"
                      className="animate-spin"
                      size={16}
                    />
                    Uploading…
                  </>
                ) : (
                  <>
                    <Upload aria-hidden="true" size={16} />
                    Upload report
                  </>
                )}
              </button>
            </div>
          </form>
        </section>
      )}

      <section
        aria-labelledby="records-list-heading"
        className="overflow-hidden rounded-[24px] border border-line bg-white shadow-sm"
      >
        <div className="border-b border-line px-5 py-5 sm:px-7">
          <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.15em] text-brand-700">
                Your documents
              </p>
              <h3
                className="mt-1 text-xl font-bold tracking-[-0.035em] text-ink-950"
                id="records-list-heading"
              >
                Saved reports
              </h3>
              <p className="mt-1 text-sm text-ink-600">
                {records.length} {records.length === 1 ? 'report' : 'reports'} in
                your account
              </p>
            </div>
            <div className="grid gap-3 sm:grid-cols-[minmax(200px,1fr)_minmax(190px,0.8fr)] xl:w-[520px]">
              <label className="relative block">
                <span className="sr-only">Search report titles</span>
                <Search
                  aria-hidden="true"
                  className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-600"
                  size={17}
                />
                <input
                  className="min-h-11 w-full rounded-xl border border-line bg-white pl-10 pr-3 text-sm text-ink-950 outline-none transition placeholder:text-ink-600/60 focus:border-brand-600 focus:ring-4 focus:ring-brand-100"
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Search reports"
                  type="search"
                  value={search}
                />
              </label>
              <label className="space-y-1">
                <span className="text-xs font-semibold text-ink-600">
                  Filter by category
                </span>
                <select
                  className="min-h-11 w-full rounded-xl border border-line bg-white px-3 text-sm text-ink-950 outline-none focus:border-brand-600 focus:ring-4 focus:ring-brand-100"
                  onChange={(event) =>
                    setCategoryFilter(
                      event.target.value as MedicalRecordCategory | 'All',
                    )
                  }
                  value={categoryFilter}
                >
                  <option value="All">All categories</option>
                  {medicalRecordCategories.map((recordCategory) => (
                    <option key={recordCategory} value={recordCategory}>
                      {recordCategory}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          </div>
        </div>

        <div className="p-5 sm:p-7">
          {loading ? (
            <div
              aria-busy="true"
              className="flex min-h-44 items-center justify-center gap-3 text-sm text-ink-600"
              role="status"
            >
              <LoaderCircle
                aria-hidden="true"
                className="animate-spin text-brand-700"
                size={18}
              />
              Loading your medical records…
            </div>
          ) : loadError ? (
            <div className="rounded-2xl border border-rose-200 bg-rose-50 p-5">
              <p className="text-sm font-semibold text-rose-800" role="alert">
                {loadError}
              </p>
              <button
                className="mt-4 inline-flex min-h-10 items-center gap-2 text-sm font-bold text-brand-700 hover:text-brand-600"
                onClick={retryLoading}
                type="button"
              >
                <RotateCcw aria-hidden="true" size={15} />
                Try loading again
              </button>
            </div>
          ) : records.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-line bg-sky-50/60 px-5 py-10 text-center">
              <span className="mx-auto grid size-12 place-items-center rounded-2xl bg-white text-brand-700 shadow-sm">
                <FileHeart aria-hidden="true" size={21} />
              </span>
              <h4 className="mt-4 text-sm font-bold text-ink-950">
                No medical records yet
              </h4>
              <p className="mx-auto mt-1 max-w-md text-xs leading-5 text-ink-600">
                Reports you upload will be listed here and visible only to your
                authenticated patient account.
              </p>
              <button
                className="mt-5 inline-flex min-h-10 items-center gap-2 rounded-xl bg-brand-700 px-4 text-sm font-bold text-white hover:bg-brand-600"
                onClick={() => setUploadOpen(true)}
                type="button"
              >
                <Plus aria-hidden="true" size={16} />
                Upload your first report
              </button>
            </div>
          ) : filteredRecords.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-line bg-sky-50/60 px-5 py-10 text-center">
              <Search
                aria-hidden="true"
                className="mx-auto text-brand-700"
                size={22}
              />
              <h4 className="mt-3 text-sm font-bold text-ink-950">
                No matching reports
              </h4>
              <p className="mt-1 text-xs leading-5 text-ink-600">
                Try another title or category filter.
              </p>
            </div>
          ) : (
            <div className="grid gap-4 lg:grid-cols-2">
              {filteredRecords.map((record) => (
                <article
                  className="rounded-2xl border border-line bg-white p-4 transition hover:border-brand-600/30 hover:shadow-sm sm:p-5"
                  key={record.id}
                >
                  <div className="flex items-start gap-3">
                    <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-brand-100 text-brand-700">
                      <FileText aria-hidden="true" size={20} />
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="rounded-full bg-sky-50 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide text-ink-600">
                          {record.category}
                        </span>
                        <span className="text-xs text-ink-600">
                          {formatFileSize(record.file_size)}
                        </span>
                      </div>
                      <h4 className="mt-2 break-words text-base font-bold text-ink-950">
                        {record.title}
                      </h4>
                      <p className="mt-1 truncate text-xs text-ink-600">
                        {record.original_filename}
                      </p>
                      <p className="mt-2 flex items-center gap-1.5 text-xs text-ink-600">
                        <CalendarDays aria-hidden="true" size={14} />
                        {formatDate(record.report_date)}
                      </p>
                      {record.description && (
                        <p className="mt-3 line-clamp-2 text-xs leading-5 text-ink-600">
                          {record.description}
                        </p>
                      )}
                    </div>
                  </div>

                  <div className="mt-4 flex flex-wrap gap-2 border-t border-line pt-4">
                    <button
                      className="inline-flex min-h-9 items-center gap-1.5 rounded-lg border border-line px-3 text-xs font-semibold text-ink-800 transition hover:bg-sky-50"
                      onClick={() => void showDetails(record)}
                      type="button"
                    >
                      Details
                    </button>
                    <button
                      aria-label={`Download ${record.title}`}
                      className="inline-flex min-h-9 items-center gap-1.5 rounded-lg border border-line px-3 text-xs font-semibold text-ink-800 transition hover:bg-sky-50 disabled:opacity-60"
                      disabled={downloadingId === record.id}
                      onClick={() => void handleDownload(record)}
                      type="button"
                    >
                      {downloadingId === record.id ? (
                        <LoaderCircle
                          aria-hidden="true"
                          className="animate-spin"
                          size={14}
                        />
                      ) : (
                        <ArrowDownToLine aria-hidden="true" size={14} />
                      )}
                      Download
                    </button>
                    <button
                      aria-label={`Delete ${record.title}`}
                      className="inline-flex min-h-9 items-center gap-1.5 rounded-lg border border-rose-200 px-3 text-xs font-semibold text-rose-700 transition hover:bg-rose-50"
                      onClick={() => {
                        setActionError(null)
                        setRecordToDelete(record)
                      }}
                      type="button"
                    >
                      <Trash2 aria-hidden="true" size={14} />
                      Delete
                    </button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </div>
      </section>

      {detailsRecord && (
        <div className="fixed inset-0 z-50 grid place-items-center bg-ink-950/45 p-4">
          <section
            aria-labelledby="record-details-heading"
            aria-modal="true"
            className="max-h-[90vh] w-full max-w-xl overflow-y-auto rounded-[24px] bg-white p-5 shadow-panel sm:p-7"
            role="dialog"
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.15em] text-brand-700">
                  Report details
                </p>
                <h3
                  className="mt-1 break-words text-xl font-bold text-ink-950"
                  id="record-details-heading"
                >
                  {detailsRecord.title}
                </h3>
              </div>
              <button
                aria-label="Close report details"
                className="grid size-10 shrink-0 place-items-center rounded-xl border border-line text-ink-600 hover:bg-sky-50"
                onClick={() => setDetailsRecord(null)}
                type="button"
              >
                <X aria-hidden="true" size={17} />
              </button>
            </div>
            {detailsLoading ? (
              <div className="flex min-h-32 items-center justify-center gap-3 text-sm text-ink-600">
                <LoaderCircle
                  aria-hidden="true"
                  className="animate-spin text-brand-700"
                  size={18}
                />
                Loading report details…
              </div>
            ) : detailsError ? (
              <p className="mt-5 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800" role="alert">
                {detailsError}
              </p>
            ) : (
              <dl className="mt-5 grid gap-3 sm:grid-cols-2">
                <RecordDetail label="Category" value={detailsRecord.category} />
                <RecordDetail
                  label="Report date"
                  value={formatDate(detailsRecord.report_date)}
                />
                <RecordDetail
                  label="File name"
                  value={detailsRecord.original_filename}
                />
                <RecordDetail
                  label="File size"
                  value={formatFileSize(detailsRecord.file_size)}
                />
                <RecordDetail
                  label="Uploaded"
                  value={formatDateTime(detailsRecord.created_at)}
                />
                <RecordDetail
                  label="Last updated"
                  value={formatDateTime(detailsRecord.updated_at)}
                />
                <div className="rounded-xl bg-sky-50/70 px-4 py-3 sm:col-span-2">
                  <dt className="text-xs font-medium text-ink-600">
                    Description
                  </dt>
                  <dd className="mt-1 whitespace-pre-wrap break-words text-sm text-ink-950">
                    {detailsRecord.description || 'No description provided.'}
                  </dd>
                </div>
              </dl>
            )}
          </section>
        </div>
      )}

      {recordToDelete && (
        <div className="fixed inset-0 z-[60] grid place-items-center bg-ink-950/45 p-4">
          <section
            aria-labelledby="delete-record-heading"
            aria-modal="true"
            className="w-full max-w-md rounded-[24px] bg-white p-5 shadow-panel sm:p-7"
            role="alertdialog"
          >
            <span className="grid size-11 place-items-center rounded-2xl bg-rose-50 text-rose-700">
              <AlertCircle aria-hidden="true" size={21} />
            </span>
            <h3
              className="mt-4 text-lg font-bold text-ink-950"
              id="delete-record-heading"
            >
              Delete this report?
            </h3>
            <p className="mt-2 break-words text-sm leading-6 text-ink-600">
              “{recordToDelete.title}” and its stored file will be permanently
              removed from your account.
            </p>
            {actionError && (
              <p className="mt-4 rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800" role="alert">
                {actionError}
              </p>
            )}
            <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
              <button
                className="inline-flex min-h-10 items-center justify-center rounded-xl border border-line px-4 text-sm font-semibold text-ink-800 hover:bg-sky-50 disabled:opacity-60"
                disabled={deleting}
                onClick={() => setRecordToDelete(null)}
                type="button"
              >
                Cancel
              </button>
              <button
                className="inline-flex min-h-10 items-center justify-center gap-2 rounded-xl bg-rose-700 px-4 text-sm font-bold text-white hover:bg-rose-800 disabled:opacity-60"
                disabled={deleting}
                onClick={() => void confirmDelete()}
                type="button"
              >
                {deleting && (
                  <LoaderCircle
                    aria-hidden="true"
                    className="animate-spin"
                    size={15}
                  />
                )}
                Delete report
              </button>
            </div>
          </section>
        </div>
      )}
    </div>
  )
}

interface RecordDetailProps {
  label: string
  value: string
}

function RecordDetail({ label, value }: RecordDetailProps) {
  return (
    <div className="min-w-0 rounded-xl bg-sky-50/70 px-4 py-3">
      <dt className="text-xs font-medium text-ink-600">{label}</dt>
      <dd className="mt-1 break-words text-sm font-semibold text-ink-950">
        {value}
      </dd>
    </div>
  )
}
