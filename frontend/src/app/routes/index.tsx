import { Suspense, type ReactNode } from 'react'
import { Navigate, createBrowserRouter } from 'react-router-dom'

import {
  AgentsPage,
  AgentSquarePage,
  ForgotPasswordPage,
  HomePage,
  LoginPage,
  LogsPage,
  MarketplacePage,
  NotFoundPage,
  ProfilePage,
  PublicAgentPage,
  RegisterPage,
  ResetPasswordPage,
  RunsPage,
} from './lazyRoutes'
import { ProtectedLayout, ProtectedRoute } from '../../features/auth/AuthGate'

function routeElement(element: ReactNode) {
  return (
    <Suspense fallback={<div className="flex h-screen items-center justify-center bg-surface text-sm text-text-muted">加载中...</div>}>
      {element}
    </Suspense>
  )
}

export const router = createBrowserRouter([
  {
    path: '/login',
    element: routeElement(<LoginPage />),
  },
  {
    path: '/register',
    element: routeElement(<RegisterPage />),
  },
  {
    path: '/forgot-password',
    element: routeElement(<ForgotPasswordPage />),
  },
  {
    path: '/reset-password',
    element: routeElement(<ResetPasswordPage />),
  },
  {
    path: '/p/:slug',
    element: routeElement(<PublicAgentPage />),
  },
  {
    path: '/square',
    element: routeElement(<AgentSquarePage />),
  },
  {
    path: '/',
    element: routeElement(<HomePage />),
  },
  {
    path: '/agents',
    element: <Navigate to="/develop/agents" replace />,
  },
  {
    path: '/runs',
    element: <Navigate to="/develop/runs" replace />,
  },
  {
    path: '/marketplace',
    element: <Navigate to="/develop/marketplace" replace />,
  },
  {
    path: '/logs',
    element: <Navigate to="/develop/logs" replace />,
  },
  {
    path: '/develop',
    element: routeElement(<ProtectedLayout />),
    children: [
      { index: true, element: <Navigate to="/develop/agents" replace /> },
      { path: 'agents', element: routeElement(<AgentsPage />) },
      { path: 'runs', element: routeElement(<RunsPage />) },
      { path: 'marketplace', element: routeElement(<MarketplacePage />) },
      { path: 'logs', element: routeElement(<LogsPage />) },
      { path: 'profile', element: routeElement(<ProfilePage />) },
      { path: 'settings', element: <Navigate to="/develop/profile" replace /> },
      { path: '*', element: routeElement(<NotFoundPage />) },
    ],
  },
  {
    path: '/profile',
    element: routeElement(
      <ProtectedRoute>
        <ProfilePage />
      </ProtectedRoute>,
    ),
  },
])
