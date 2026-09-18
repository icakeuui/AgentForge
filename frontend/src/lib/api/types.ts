export interface RawApiEnvelope<T> {
  code: number
  message: string
  data: T
}

export interface ApiSuccess<T> {
  data: T
}

export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'

export interface ApiRequestOptions {
  method?: HttpMethod
  headers?: Record<string, string>
  body?: unknown | FormData
  signal?: AbortSignal
  authMode?: 'auto' | 'required' | 'none'
  responseMode?: 'envelope' | 'raw'
}
