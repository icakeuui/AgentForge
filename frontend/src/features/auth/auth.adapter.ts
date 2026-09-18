import { apiClient } from '../../lib/api/client'

export interface AuthUserProfile {
  user_id: string
  search_id: number
  email: string
  email_verified: boolean
  display_name: string
  avatar_url: string | null
  status: string
  team_id: string | null
  role: string | null
}

export interface TokenPairResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in_seconds: number
  user: AuthUserProfile
}

export interface RegisterStartPayload {
  email: string
}

export interface RegisterStartResponse {
  email: string
  expires_in_seconds: number
  retry_after_seconds: number
  dev_code: string | null
}

export interface AvatarUploadResponse {
  avatar_url: string
}

export interface RegisterVerifyPayload {
  email: string
  code: string
}

export interface RegisterVerifyResponse {
  email: string
  registration_token: string
  expires_in_seconds: number
}

export interface RegisterCompletePayload {
  email: string
  registration_token: string
  password: string
  confirm_password: string
  display_name: string
  avatar_url: string | null
}

export interface LoginPayload {
  email: string
  password: string
}

export interface PasswordResetPayload {
  email: string
  code: string
  new_password: string
}

export async function registerStart(payload: RegisterStartPayload): Promise<RegisterStartResponse> {
  const response = await apiClient.request<RegisterStartResponse>('/auth/register/start', {
    method: 'POST',
    body: payload,
    authMode: 'none',
  })
  return response.data
}

export async function registerVerify(payload: RegisterVerifyPayload): Promise<RegisterVerifyResponse> {
  const response = await apiClient.request<RegisterVerifyResponse>('/auth/register/verify', {
    method: 'POST',
    body: payload,
    authMode: 'none',
  })
  return response.data
}

export async function registerComplete(payload: RegisterCompletePayload): Promise<TokenPairResponse> {
  const response = await apiClient.request<TokenPairResponse>('/auth/register/complete', {
    method: 'POST',
    body: payload,
    authMode: 'none',
  })
  return response.data
}

export async function login(payload: LoginPayload): Promise<TokenPairResponse> {
  const response = await apiClient.request<TokenPairResponse>('/auth/login', {
    method: 'POST',
    body: payload,
    authMode: 'none',
  })
  return response.data
}

export async function refresh(refresh_token: string): Promise<TokenPairResponse> {
  const response = await apiClient.request<TokenPairResponse>('/auth/refresh', {
    method: 'POST',
    body: { refresh_token },
    authMode: 'none',
  })
  return response.data
}

export async function logout(refresh_token: string): Promise<void> {
  await apiClient.request('/auth/logout', {
    method: 'POST',
    body: { refresh_token },
    authMode: 'none',
  })
}

export async function uploadAvatar(file: File): Promise<AvatarUploadResponse> {
  const formData = new FormData()
  formData.append('file', file)
  const response = await apiClient.request<AvatarUploadResponse>('/auth/avatar/upload', {
    method: 'POST',
    body: formData,
    authMode: 'none',
  })
  return response.data
}

export async function getSession(): Promise<AuthUserProfile> {
  const response = await apiClient.request<AuthUserProfile>('/auth/session', {
    method: 'GET',
    authMode: 'required',
  })
  return response.data
}

export async function requestPasswordReset(email: string): Promise<RegisterStartResponse> {
  const response = await apiClient.request<RegisterStartResponse>('/auth/password/forgot', {
    method: 'POST',
    body: { email },
    authMode: 'none',
  })
  return response.data
}

export async function resetPassword(payload: PasswordResetPayload): Promise<void> {
  await apiClient.request('/auth/password/reset', {
    method: 'POST',
    body: payload,
    authMode: 'none',
  })
}
