import { create } from 'zustand'

import { normalizeApiError } from '../../lib/api/error'
import * as authAdapter from './auth.adapter'

const ACCESS_TOKEN_KEY = 'auth_token'
const REFRESH_TOKEN_KEY = 'auth_refresh_token'
let sessionRevision = 0

function readToken(key: string): string | null {
  if (typeof window === 'undefined') {
    return null
  }
  const value = window.localStorage.getItem(key)
  return value && value.trim().length > 0 ? value : null
}

function writeToken(key: string, token: string | null): void {
  if (typeof window === 'undefined') {
    return
  }
  if (token === null) {
    window.localStorage.removeItem(key)
    return
  }
  window.localStorage.setItem(key, token)
}

export type AuthStatus = 'loading' | 'guest' | 'authenticated'

interface AuthStoreState {
  status: AuthStatus
  user: authAdapter.AuthUserProfile | null
  initialize: () => Promise<void>
  login: (email: string, password: string) => Promise<void>
  registerComplete: (payload: authAdapter.RegisterCompletePayload) => Promise<void>
  logout: () => Promise<void>
  updateProfile: (payload: authAdapter.UpdateProfilePayload) => Promise<void>
  refresh: () => Promise<boolean>
  setTokens: (pair: authAdapter.TokenPairResponse) => void
  clearSession: () => void
}

function setSessionTokens(pair: authAdapter.TokenPairResponse): void {
  writeToken(ACCESS_TOKEN_KEY, pair.access_token)
  writeToken(REFRESH_TOKEN_KEY, pair.refresh_token)
}

function clearSessionTokens(): void {
  writeToken(ACCESS_TOKEN_KEY, null)
  writeToken(REFRESH_TOKEN_KEY, null)
}

export const useAuthStore = create<AuthStoreState>((set) => ({
  status: 'loading',
  user: null,

  initialize: async () => {
    const revision = ++sessionRevision
    const accessToken = readToken(ACCESS_TOKEN_KEY)
    const refreshToken = readToken(REFRESH_TOKEN_KEY)

    if (!accessToken && !refreshToken) {
      if (revision === sessionRevision) set(() => ({ status: 'guest', user: null }))
      return
    }

    try {
      const user = await authAdapter.getSession()
      if (revision === sessionRevision) set(() => ({ status: 'authenticated', user }))
      return
    } catch {
      if (refreshToken) {
        try {
          const refreshed = await authAdapter.refresh(refreshToken)
          if (revision !== sessionRevision) return
          setSessionTokens(refreshed)
          set(() => ({ status: 'authenticated', user: refreshed.user }))
          return
        } catch (refreshError) {
          const apiError = normalizeApiError(refreshError)
          if (typeof window !== 'undefined') {
            window.console.debug('auth refresh failed', apiError.message)
          }
        }
      }

      if (revision === sessionRevision) {
        clearSessionTokens()
        set(() => ({ status: 'guest', user: null }))
      }
    }
  },

  login: async (email: string, password: string) => {
    const revision = ++sessionRevision
    const pair = await authAdapter.login({ email, password })
    if (revision !== sessionRevision) return
    setSessionTokens(pair)
    set(() => ({ status: 'authenticated', user: pair.user }))
  },

  registerComplete: async (payload: authAdapter.RegisterCompletePayload) => {
    const revision = ++sessionRevision
    const pair = await authAdapter.registerComplete(payload)
    if (revision !== sessionRevision) return
    setSessionTokens(pair)
    set(() => ({ status: 'authenticated', user: pair.user }))
  },

  logout: async () => {
    ++sessionRevision
    const refreshToken = readToken(REFRESH_TOKEN_KEY)
    clearSessionTokens()
    set(() => ({ status: 'guest', user: null }))
    if (refreshToken) {
      try {
        await authAdapter.logout(refreshToken)
      } catch {
        // Best effort revoke.
      }
    }
  },

  updateProfile: async (payload) => {
    const revision = ++sessionRevision
    const user = await authAdapter.updateProfile(payload)
    if (revision === sessionRevision) set(() => ({ status: 'authenticated', user }))
  },

  refresh: async () => {
    const revision = ++sessionRevision
    const refreshToken = readToken(REFRESH_TOKEN_KEY)
    if (!refreshToken) {
      return false
    }
    try {
      const pair = await authAdapter.refresh(refreshToken)
      if (revision !== sessionRevision) return false
      setSessionTokens(pair)
      set(() => ({ status: 'authenticated', user: pair.user }))
      return true
    } catch {
      if (revision !== sessionRevision) return false
      clearSessionTokens()
      set(() => ({ status: 'guest', user: null }))
      return false
    }
  },

  setTokens: (pair) => {
    ++sessionRevision
    setSessionTokens(pair)
    set(() => ({ status: 'authenticated', user: pair.user }))
  },

  clearSession: () => {
    ++sessionRevision
    clearSessionTokens()
    set(() => ({ status: 'guest', user: null }))
  },
}))

export { ACCESS_TOKEN_KEY, REFRESH_TOKEN_KEY }
