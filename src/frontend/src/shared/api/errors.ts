export type ErrorDetails = Record<string, unknown>

export class ApiError extends Error {
  readonly code: string
  readonly status: number
  readonly details: ErrorDetails

  constructor(params: { code: string; message: string; status: number; details?: ErrorDetails }) {
    super(params.message)
    this.name = 'ApiError'
    this.code = params.code
    this.status = params.status
    this.details = params.details ?? {}
  }
}
