import { ApiError } from './errors'

export { ApiError }

const defaultBaseUrl = 'http://127.0.0.1:8000'

export function apiBaseUrl(): string {
  return import.meta.env.VITE_CALLIOPE_API_BASE_URL ?? defaultBaseUrl
}

export async function requestJson<TResponse>(
  path: string,
  init: RequestInit = {},
): Promise<TResponse> {
  const response = await fetch(`${apiBaseUrl()}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init.headers ?? {}),
    },
    ...init,
  })

  if (!response.ok) {
    let parsed: unknown
    try {
      parsed = await response.json()
    } catch {
      parsed = undefined
    }
    const error = parseErrorEnvelope(parsed, response.status)
    throw error
  }

  if (response.status === 204) {
    return undefined as TResponse
  }

  return (await response.json()) as TResponse
}

function parseErrorEnvelope(payload: unknown, status: number): ApiError {
  if (isBackendError(payload)) {
    return new ApiError({
      code: payload.error.code,
      message: payload.error.message,
      status,
      details: payload.error.details,
    })
  }

  return new ApiError({
    code: 'http_error',
    message: `Request failed with HTTP ${status}.`,
    status,
  })
}

function isBackendError(payload: unknown): payload is {
  error: { code: string; message: string; details: Record<string, unknown> }
} {
  return (
    typeof payload === 'object' &&
    payload !== null &&
    'error' in payload &&
    typeof (payload as { error?: unknown }).error === 'object' &&
    (payload as { error: { code?: unknown; message?: unknown } }).error !== null &&
    typeof (payload as { error: { code?: unknown } }).error.code === 'string' &&
    typeof (payload as { error: { message?: unknown } }).error.message === 'string'
  )
}
