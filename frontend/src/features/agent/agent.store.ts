import { create } from 'zustand'

import { notify } from '../notifications/notify'
import { normalizeApiError } from '../../lib/api/error'
import { useExecutionStore } from '../execution/execution.store'
import { agentAdapter, type AgentDetail, type CreateAgentPayload, type UpdateAgentPayload } from './agent.adapter'

export const AGENT_RECENT_STORAGE_KEY = 'AGENTFORGE_RECENT_AGENT_ID'

type AgentContextStatus = 'EMPTY' | 'LIST_LOADING' | 'DETAIL_LOADING' | 'READY' | 'ERROR'

interface AgentStoreState {
  agent_list: AgentDetail[]
  current_agent_id: string | null
  current_agent_detail: AgentDetail | null
  is_agent_list_loading: boolean
  is_agent_detail_loading: boolean
  agent_context_status: AgentContextStatus
  loadAgentList: () => Promise<void>
  selectAgent: (agent_id: string) => Promise<void>
  createAgent: (payload: CreateAgentPayload) => Promise<void>
  updateAgent: (agent_id: string, payload: UpdateAgentPayload) => Promise<void>
  deleteAgent: (agent_id: string) => Promise<void>
  refreshCurrentAgent: () => Promise<void>
  resetCurrentAgent: () => void
}

function saveRecentAgentId(agentId: string | null): void {
  if (typeof window === 'undefined') {
    return
  }

  if (agentId === null) {
    window.localStorage.removeItem(AGENT_RECENT_STORAGE_KEY)
    return
  }

  window.localStorage.setItem(AGENT_RECENT_STORAGE_KEY, agentId)
}

export function getRecentAgentIdFromStorage(): string | null {
  if (typeof window === 'undefined') {
    return null
  }

  const stored = window.localStorage.getItem(AGENT_RECENT_STORAGE_KEY)
  if (stored === null) {
    return null
  }

  const normalized = stored.trim()
  return normalized.length > 0 ? normalized : null
}

export const useAgentStore = create<AgentStoreState>((set, get) => ({
  agent_list: [],
  current_agent_id: null,
  current_agent_detail: null,
  is_agent_list_loading: false,
  is_agent_detail_loading: false,
  agent_context_status: 'EMPTY',

  resetCurrentAgent: () => {
    useExecutionStore.getState().resetExecution()
    saveRecentAgentId(null)
    set(() => ({
      current_agent_id: null,
      current_agent_detail: null,
      is_agent_detail_loading: false,
      agent_context_status: 'EMPTY',
    }))
  },

  loadAgentList: async () => {
    set(() => ({
      is_agent_list_loading: true,
      agent_context_status: 'LIST_LOADING',
    }))

    try {
      const list = await agentAdapter.fetchAgentList()

      set(() => ({
        agent_list: list,
        is_agent_list_loading: false,
      }))

      const availableAgents = list.filter((agent) => agent.is_available && !agent.archived)
      if (list.length === 0 || availableAgents.length === 0) {
        saveRecentAgentId(null)
        get().resetCurrentAgent()
        set(() => ({
          agent_context_status: 'EMPTY',
        }))
      } else if (get().current_agent_id === null) {
        set(() => ({
          agent_context_status: 'EMPTY',
        }))
      }
    } catch (error) {
      const apiError = normalizeApiError(error)
      set(() => ({
        agent_list: [],
        is_agent_list_loading: false,
        agent_context_status: 'ERROR',
      }))
      notify.error(apiError.message)
    }
  },

  createAgent: async (payload) => {
    const newAgent = await agentAdapter.createAgent(payload)
    if (newAgent.is_available) {
      saveRecentAgentId(newAgent.id)
    } else {
      saveRecentAgentId(null)
    }
    set((state) => {
      const existingIndex = state.agent_list.findIndex((agent) => agent.id === newAgent.id)
      const nextList = [...state.agent_list]

      if (existingIndex >= 0) {
        nextList[existingIndex] = newAgent
      } else {
        nextList.push(newAgent)
      }

      return {
        agent_list: nextList,
        current_agent_id: newAgent.id,
        current_agent_detail: newAgent,
        agent_context_status: newAgent.is_available ? ('READY' as const) : ('ERROR' as const),
        is_agent_detail_loading: false,
      }
    })
    useExecutionStore.getState().setOpeningMessage(newAgent.id, newAgent.opening_statement)
  },

  updateAgent: async (agent_id, payload) => {
    const updated = await agentAdapter.updateAgent(agent_id, payload)
    set((state) => {
      const isCurrent = state.current_agent_id === updated.id
      return {
        agent_list: state.agent_list.map((agent) => (agent.id === updated.id ? updated : agent)),
        current_agent_id: isCurrent ? updated.id : state.current_agent_id,
        current_agent_detail: isCurrent ? updated : state.current_agent_detail,
        agent_context_status: isCurrent ? (updated.is_available ? 'READY' : 'ERROR') : state.agent_context_status,
        is_agent_detail_loading: false,
      }
    })
    if (get().current_agent_id === updated.id) {
      saveRecentAgentId(updated.is_available ? updated.id : null)
      useExecutionStore.getState().setOpeningMessage(updated.id, updated.opening_statement)
    }
  },

  deleteAgent: async (agent_id) => {
    const deleted = await agentAdapter.deleteAgent(agent_id)
    const wasCurrent = get().current_agent_id === deleted.id
    if (wasCurrent) {
      useExecutionStore.getState().resetExecution()
    }
    set((state) => {
      const nextList = state.agent_list.filter((agent) => agent.id !== deleted.id)
      return {
        agent_list: nextList,
        current_agent_id: wasCurrent ? null : state.current_agent_id,
        current_agent_detail: wasCurrent ? null : state.current_agent_detail,
        agent_context_status: wasCurrent ? 'EMPTY' : state.agent_context_status,
        is_agent_detail_loading: false,
      }
    })
    saveRecentAgentId(get().current_agent_id)
  },

  selectAgent: async (agent_id) => {
    const normalizedId = agent_id.trim()
    if (normalizedId.length === 0) {
      return
    }
    const selected = get().agent_list.find((agent) => agent.id === normalizedId)
    if (selected && !selected.is_available) {
      useExecutionStore.getState().resetExecution()
      saveRecentAgentId(null)
      set(() => ({
        current_agent_id: normalizedId,
        current_agent_detail: selected,
        is_agent_detail_loading: false,
        agent_context_status: 'ERROR',
      }))
      notify.warning(
        selected.availability_reason === null
          ? '该智能体当前不可用，请先修复配置'
          : `该智能体当前不可用：${selected.availability_reason}`,
      )
      return
    }

    useExecutionStore.getState().resetExecution()
    saveRecentAgentId(normalizedId)
    set(() => ({
      current_agent_detail: null,
      agent_context_status: 'DETAIL_LOADING',
      current_agent_id: normalizedId,
    }))
    await get().refreshCurrentAgent()
  },

  refreshCurrentAgent: async () => {
    const currentAgentId = get().current_agent_id
    if (currentAgentId === null) {
      return
    }

    set(() => ({
      is_agent_detail_loading: true,
      agent_context_status: 'DETAIL_LOADING',
      current_agent_detail: null,
    }))

    try {
      const detail = await agentAdapter.fetchAgentDetail(currentAgentId)

      if (detail.id !== currentAgentId) {
        get().resetCurrentAgent()
        set(() => ({
          agent_context_status: 'ERROR',
        }))
        notify.error('智能体身份不匹配')
        return
      }
      if (!detail.is_available) {
        saveRecentAgentId(null)
        set(() => ({
          current_agent_detail: detail,
          is_agent_detail_loading: false,
          agent_context_status: 'ERROR',
        }))
        notify.warning(
          detail.availability_reason === null
            ? '当前智能体不可用，请先修复配置'
            : `当前智能体不可用：${detail.availability_reason}`,
        )
        return
      }

      saveRecentAgentId(currentAgentId)
      set(() => ({
        current_agent_detail: detail,
        is_agent_detail_loading: false,
        agent_context_status: 'READY',
      }))
      useExecutionStore.getState().setOpeningMessage(detail.id, detail.opening_statement)
    } catch (error) {
      const apiError = normalizeApiError(error)
      set(() => ({
        is_agent_detail_loading: false,
      }))
      notify.error(apiError.message)
      get().resetCurrentAgent()
    }
  },
}))

export type { AgentContextStatus, AgentStoreState, AgentDetail, CreateAgentPayload }
