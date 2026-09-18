export class ApiError extends Error {
  code: number | string
  raw: unknown

  constructor(params: { code: number | string; message: string; raw?: unknown }) {
    super(params.message)
    this.name = 'ApiError'
    this.code = params.code
    this.raw = params.raw ?? null
  }
}

export function normalizeApiError(error: unknown): ApiError {
  if (error instanceof ApiError) {
    return error
  }

  if (error instanceof Error) {
    return new ApiError({
      code: 'NETWORK_OR_RUNTIME_ERROR',
      message: error.message,
      raw: error,
    })
  }

  return new ApiError({
    code: 'UNKNOWN_ERROR',
    message: '未知错误',
    raw: error,
  })
}
