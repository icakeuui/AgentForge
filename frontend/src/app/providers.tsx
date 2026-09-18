import type { PropsWithChildren } from 'react'
import { useEffect } from 'react'
import { Toaster } from 'sonner'

import { useAuthStore } from '../features/auth/auth.store'
import { getRecentAgentIdFromStorage, useAgentStore } from '../features/agent/agent.store'
import { executionAdapter } from '../features/execution/execution.adapter'
import { useExecutionStore } from '../features/execution/execution.store'
import { useExecutionPolling } from '../features/execution/useExecutionPolling'
import { applyTheme, useThemeStore } from '../features/theme/theme.store'

export function AppProviders({ children }: PropsWithChildren) {
  const currentExecutionId = useExecutionStore((state) => state.current_execution_id)
  const authStatus = useAuthStore((state) => state.status)
  const authUserId = useAuthStore((state) => state.user?.user_id ?? null)
  const initializeAuth = useAuthStore((state) => state.initialize)
  const theme = useThemeStore((state) => state.theme)
  useExecutionPolling(currentExecutionId)

  useEffect(() => {
    executionAdapter.initializeExecutionRuntime()
    void initializeAuth()
  }, [initializeAuth])

  useEffect(() => {
    if (authStatus !== 'authenticated' || authUserId === null) {
      return
    }

    async function initializeAgentRuntimeContext() {
      const store = useAgentStore.getState()
      await store.loadAgentList()

      const postLoad = useAgentStore.getState()
      if (postLoad.agent_context_status === 'ERROR') {
        return
      }

      const restoredAgentId = getRecentAgentIdFromStorage()
      const restoredAgent = restoredAgentId === null ? null : postLoad.agent_list.find((agent) => agent.id === restoredAgentId)
      if (restoredAgent !== null && restoredAgent !== undefined && restoredAgent.is_available) {
        await useAgentStore.getState().selectAgent(restoredAgent.id)
        return
      }

      useAgentStore.getState().resetCurrentAgent()
    }

    void initializeAgentRuntimeContext()
  }, [authStatus, authUserId])

  useEffect(() => {
    applyTheme(theme)
  }, [theme])

  return (
    <>
      {children}
      <Toaster richColors position="top-right" />
    </>
  )
}
