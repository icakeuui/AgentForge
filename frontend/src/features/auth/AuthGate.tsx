import type { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'

import { AppShell } from '../../app/routes/lazyRoutes'
import { useAuthStore } from './auth.store'

function LoadingShell() {
  return (
    <div className="flex h-screen items-center justify-center bg-bg text-sm text-text-muted">
      正在验证登录状态...
    </div>
  )
}

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const status = useAuthStore((state) => state.status)

  if (status === 'loading') {
    return <LoadingShell />
  }

  if (status === 'guest') {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}

export function ProtectedLayout() {
  return (
    <ProtectedRoute>
      <AppShell />
    </ProtectedRoute>
  )
}
