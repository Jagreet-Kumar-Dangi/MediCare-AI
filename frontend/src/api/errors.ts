import axios from 'axios'

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

export function getApiErrorMessage(error: unknown): string {
  if (!axios.isAxiosError(error)) {
    return error instanceof Error
      ? error.message
      : 'Something went wrong. Please try again.'
  }

  if (!error.response) {
    return 'The care portal could not reach the server. Check your connection and try again.'
  }

  const responseData: unknown = error.response.data
  if (!isRecord(responseData)) {
    return 'The request could not be completed. Please try again.'
  }

  const detail = responseData.detail
  if (typeof detail === 'string') {
    return detail
  }

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => (isRecord(item) && typeof item.msg === 'string' ? item.msg : null))
      .filter((message): message is string => message !== null)
    if (messages.length > 0) {
      return messages.join(' ')
    }
  }

  return 'The request could not be completed. Please try again.'
}
