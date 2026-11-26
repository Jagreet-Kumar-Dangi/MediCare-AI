import axios from 'axios'

const TOKEN_STORAGE_KEY = 'medicare_ai_access_token'
const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim()

export const apiClient = axios.create({
  baseURL:
    configuredBaseUrl?.replace(/\/+$/, '') ||
    'http://127.0.0.1:8000/api/v1',
  timeout: 12_000,
  headers: {
    'Content-Type': 'application/json',
  },
})

export function getAccessToken(): string | null {
  return window.sessionStorage.getItem(TOKEN_STORAGE_KEY)
}

export function setAccessToken(token: string): void {
  window.sessionStorage.setItem(TOKEN_STORAGE_KEY, token)
}

export function clearAccessToken(): void {
  window.sessionStorage.removeItem(TOKEN_STORAGE_KEY)
}

let unauthorizedHandler: (() => void) | undefined

export function setUnauthorizedHandler(
  handler: (() => void) | undefined,
): void {
  unauthorizedHandler = handler
}

apiClient.interceptors.request.use((config) => {
  const token = getAccessToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    if (
      axios.isAxiosError(error) &&
      error.response?.status === 401 &&
      getAccessToken() &&
      !error.config?.url?.includes('/auth/login')
    ) {
      clearAccessToken()
      unauthorizedHandler?.()
    }
    return Promise.reject(error)
  },
)
