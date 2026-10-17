import { useEffect, useRef } from 'react'

import { normalizeApiError } from '../../lib/api/error'
import { notify } from '../notifications/notify'
import { useAgentStore } from '../agent/agent.store'
import { executionAdapter } from './execution.adapter'
import { useExecutionStore } from './execution.store'

const POLLING_INTERVAL_MS = 250
const NOTIFY_AFTER_CONSECUTIVE_FAILURES = 10

export function useExecutionPolling(execution_id: string | null) {
  const currentAgentId = useAgentStore((state) => state.current_agent_id)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const consecutiveFailureRef = useRef(0)
  const pollingExecutionIdRef = useRef<string | null>(null)
  const pollingAgentIdRef = useRef<string | null>(null)
  const pollInFlightRef = useRef(false)
  const networkFailureNotifiedRef = useRef(false)

  useEffect(() => {
    if (execution_id === null) {
      return
    }

    const initialAgentId = useAgentStore.getState().current_agent_id
    if (initialAgentId === null) {
      return
    }

    pollingExecutionIdRef.current = execution_id
    pollingAgentIdRef.current = initialAgentId
    consecutiveFailureRef.current = 0
    networkFailureNotifiedRef.current = false

    const stopPolling = (finalize = false) => {
      if (intervalRef.current !== null) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
      if (finalize) {
        useExecutionStore.getState().finishExecution()
      }
    }

    const poll = async () => {
      if (pollInFlightRef.current) return
      const latestExecutionStore = useExecutionStore.getState()
      const latestAgentStore = useAgentStore.getState()

      if (latestExecutionStore.termination_reason === 'USER_STOPPED') {
        stopPolling(true)
        return
      }

      if (latestExecutionStore.current_execution_id !== execution_id) {
        stopPolling()
        return
      }

      if (
        latestAgentStore.current_agent_id === null ||
        latestAgentStore.current_agent_id !== pollingAgentIdRef.current
      ) {
        stopPolling()
        latestExecutionStore.resetExecution()
        return
      }

      pollInFlightRef.current = true
      try {
        const snapshot = await executionAdapter.fetchExecution(execution_id)
        const currentExecutionId = useExecutionStore.getState().current_execution_id
        if (currentExecutionId !== snapshot.execution_id) {
          return
        }

        executionAdapter.applyExecutionSnapshot(snapshot)
        consecutiveFailureRef.current = 0
        networkFailureNotifiedRef.current = false

        if (
          snapshot.status === 'SUCCEEDED' ||
          snapshot.status === 'FAILED' ||
          snapshot.status === 'TERMINATED'
        ) {
          stopPolling(true)
        }
      } catch (error) {
        consecutiveFailureRef.current += 1
        if (
          consecutiveFailureRef.current >= NOTIFY_AFTER_CONSECUTIVE_FAILURES &&
          !networkFailureNotifiedRef.current
        ) {
          networkFailureNotifiedRef.current = true
          notify.error(`暂时无法获取任务进度，正在继续重试；后端任务状态未被更改。${normalizeApiError(error).message}`)
        }
      } finally {
        pollInFlightRef.current = false
      }
    }

    intervalRef.current = setInterval(() => {
      void poll()
    }, POLLING_INTERVAL_MS)

    void poll()

    return () => {
      if (intervalRef.current !== null) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
    }
  }, [execution_id, currentAgentId])
}
