import { create } from 'zustand'

import {
  IDLE_EXECUTION_STATE,
  type ConversationMessage,
  type ConversationSession,
  type ExecutionRuntimeState,
  type ExecutionSnapshot,
  type ExecutionStepLog,
  type ExecutionStoreState,
} from './execution.types'
import { getBuiltinToolLabel } from '../tools/tools.catalog'

const CONVERSATION_HISTORY_STORAGE_KEY = 'AGENTFORGE_CONVERSATION_HISTORY_V1'
const MAX_CONVERSATION_SESSIONS = 12
const SESSION_TITLE_MAX_LENGTH = 24
const STOPPED_BY_USER_MESSAGE = '已停止：用户主动停止了当前模型行为。'

interface PersistedConversationHistory {
  active_by_agent: Record<string, string | null>
  sessions_by_agent: Record<string, ConversationSession[]>
}

function assistantContentFromSnapshot(data: ExecutionSnapshot): string | null {
  if (data.final_answer !== null && data.final_answer.trim().length > 0) {
    return data.final_answer
  }
  if (data.status === 'FAILED' || data.status === 'TERMINATED') {
    return data.error_message ?? data.termination_reason ?? '本次执行未能完成，请查看运行日志。'
  }
  return null
}

function runtimeFromState(state: ExecutionRuntimeState): ExecutionRuntimeState {
  return {
    current_execution_id: state.current_execution_id,
    is_execution_starting: state.is_execution_starting,
    status: state.status,
    final_answer: state.final_answer,
    error_code: state.error_code,
    error_source: state.error_source,
    error_details: state.error_details,
    error_message: state.error_message,
    react_steps: state.react_steps,
    step_logs: state.step_logs,
    artifacts: state.artifacts,
    termination_reason: state.termination_reason,
    total_token_usage: state.total_token_usage,
    preview_phase: state.preview_phase,
    preview_url: state.preview_url,
    deployment_status: state.deployment_status,
    deployed_url: state.deployed_url,
    last_user_input: state.last_user_input,
    conversation_messages: state.conversation_messages,
    conversation_messages_hidden: state.conversation_messages_hidden,
    conversation_cleared_execution_id: state.conversation_cleared_execution_id,
  }
}

function openingMessages(agent_id: string | null, opening_statement: string | null): ConversationMessage[] {
  if (agent_id === null || opening_statement === null || opening_statement.trim().length === 0) {
    return []
  }

  return [
    {
      id: `opening:${agent_id}`,
      role: 'assistant',
      content: opening_statement.trim(),
      execution_id: null,
      status: 'IDLE',
      source: 'opening',
    },
  ]
}

function withOpeningMessage(messages: ConversationMessage[], agent_id: string | null, opening_statement: string | null): ConversationMessage[] {
  const nextOpeningMessages = openingMessages(agent_id, opening_statement)
  const nonOpeningMessages = messages.filter((message) => message.source !== 'opening')
  const hasChatMessages = nonOpeningMessages.some((message) => message.source !== 'activity')

  if (nextOpeningMessages.length === 0) {
    return nonOpeningMessages
  }

  return hasChatMessages ? [...nextOpeningMessages, ...nonOpeningMessages] : nextOpeningMessages
}

function normalizeTitleCandidate(value: string | null | undefined): string | null {
  if (typeof value !== 'string') {
    return null
  }
  const normalized = value.replace(/\s+/g, ' ').trim()
  if (normalized.length === 0) {
    return null
  }
  if (normalized.length <= SESSION_TITLE_MAX_LENGTH) {
    return normalized
  }
  return `${normalized.slice(0, SESSION_TITLE_MAX_LENGTH).trim()}...`
}

function deriveSessionTitle(messages: ConversationMessage[], lastUserInput: string | null, fallback = '新对话'): string {
  const preferredTitle = normalizeTitleCandidate(lastUserInput)
  if (preferredTitle !== null) {
    return preferredTitle
  }

  for (const message of messages) {
    if (message.role === 'user') {
      const candidate = normalizeTitleCandidate(message.content)
      if (candidate !== null) {
        return candidate
      }
    }
  }

  return fallback
}

function createConversationSessionRecord(agent_id: string | null, opening_statement: string | null): ConversationSession {
  const timestamp = Date.now()
  const messages = openingMessages(agent_id, opening_statement)
  return {
    id: `session:${timestamp}:${Math.random().toString(36).slice(2, 8)}`,
    agent_id,
    title: deriveSessionTitle(messages, null),
    created_at: timestamp,
    updated_at: timestamp,
    ...IDLE_EXECUTION_STATE,
    conversation_messages: messages,
  }
}

function createDraftConversationRuntime(agent_id: string | null, opening_statement: string | null): ExecutionRuntimeState {
  return {
    ...IDLE_EXECUTION_STATE,
    conversation_messages: openingMessages(agent_id, opening_statement),
    conversation_messages_hidden: false,
    conversation_cleared_execution_id: null,
  }
}

function sortConversationSessions(sessions: ConversationSession[]): ConversationSession[] {
  return sessions
    .slice()
    .sort((left, right) => right.updated_at - left.updated_at || right.created_at - left.created_at)
    .slice(0, MAX_CONVERSATION_SESSIONS)
}

function applySession(state: ExecutionStoreState, session: ConversationSession, sessions: ConversationSession[]): ExecutionStoreState {
  return {
    ...state,
    ...runtimeFromState(session),
    conversation_agent_id: session.agent_id,
    conversation_sessions: sessions,
    active_conversation_id: session.id,
  }
}

function applyDraftConversation(
  state: ExecutionStoreState,
  agent_id: string | null,
  opening_statement: string | null,
  sessions: ConversationSession[],
): ExecutionStoreState {
  return {
    ...state,
    ...createDraftConversationRuntime(agent_id, opening_statement),
    conversation_agent_id: agent_id,
    conversation_sessions: sessions,
    active_conversation_id: null,
  }
}

function updateActiveSessionList(
  state: ExecutionStoreState,
  runtime: ExecutionRuntimeState,
  overrides?: Partial<ConversationSession>,
): ConversationSession[] {
  if (state.active_conversation_id === null) {
    return state.conversation_sessions
  }

  const nextSessions = state.conversation_sessions.map((session) => {
    if (session.id !== state.active_conversation_id) {
      return session
    }

    return {
      ...session,
      ...runtime,
      agent_id: state.conversation_agent_id,
      title: deriveSessionTitle(runtime.conversation_messages, runtime.last_user_input, session.title),
      updated_at: Date.now(),
      ...overrides,
    }
  })

  return sortConversationSessions(nextSessions)
}

function readPersistedConversationHistory(): PersistedConversationHistory {
  if (typeof window === 'undefined') {
    return {
      active_by_agent: {},
      sessions_by_agent: {},
    }
  }

  const raw = window.localStorage.getItem(CONVERSATION_HISTORY_STORAGE_KEY)
  if (raw === null) {
    return {
      active_by_agent: {},
      sessions_by_agent: {},
    }
  }

  try {
    const parsed = JSON.parse(raw) as Partial<PersistedConversationHistory>
    return {
      active_by_agent: typeof parsed.active_by_agent === 'object' && parsed.active_by_agent !== null ? parsed.active_by_agent : {},
      sessions_by_agent:
        typeof parsed.sessions_by_agent === 'object' && parsed.sessions_by_agent !== null ? parsed.sessions_by_agent : {},
    }
  } catch {
    return {
      active_by_agent: {},
      sessions_by_agent: {},
    }
  }
}

function writePersistedConversationHistory(payload: PersistedConversationHistory): void {
  if (typeof window === 'undefined') {
    return
  }

  window.localStorage.setItem(CONVERSATION_HISTORY_STORAGE_KEY, JSON.stringify(payload))
}

function persistConversationSessions(agent_id: string | null, sessions: ConversationSession[], activeConversationId: string | null): void {
  if (agent_id === null) {
    return
  }

  const persisted = readPersistedConversationHistory()
  persisted.sessions_by_agent[agent_id] = sortConversationSessions(
    sessions.map((session) => ({
      ...session,
      agent_id,
    })),
  )
  persisted.active_by_agent[agent_id] = activeConversationId
  writePersistedConversationHistory(persisted)
}

function readConversationSessions(agent_id: string, opening_statement: string | null): { sessions: ConversationSession[]; activeConversationId: string | null } {
  const persisted = readPersistedConversationHistory()
  const rawSessions = Array.isArray(persisted.sessions_by_agent[agent_id]) ? persisted.sessions_by_agent[agent_id] : []
  const sessions = sortConversationSessions(
    rawSessions.map((session) => {
      const nextMessages = withOpeningMessage(session.conversation_messages ?? [], agent_id, opening_statement)
      return {
        ...createConversationSessionRecord(agent_id, opening_statement),
        ...session,
        agent_id,
        title: deriveSessionTitle(nextMessages, session.last_user_input ?? null, session.title ?? '新对话'),
        conversation_messages: nextMessages,
      }
    }),
  )

  if (sessions.length === 0) {
    return {
      sessions: [],
      activeConversationId: null,
    }
  }

  const preferredActiveId = persisted.active_by_agent[agent_id]
  const activeConversationId = sessions.some((session) => session.id === preferredActiveId) ? preferredActiveId : sessions[0].id
  return { sessions, activeConversationId }
}

function readString(value: unknown): string | null {
  return typeof value === 'string' && value.trim().length > 0 ? value.trim() : null
}

function readNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

function hasKnowledgeHit(log: ExecutionStepLog): boolean {
  const hits = Array.isArray(log.payload.knowledge_hits) ? log.payload.knowledge_hits : []
  const matchedCount = readNumber(log.payload.matched_count) ?? hits.length
  return log.status === 'success' && (log.payload.matched === true || matchedCount > 0 || readString(log.payload.context) !== null)
}

function knowledgeActivityContent(log: ExecutionStepLog): string {
  const hits = Array.isArray(log.payload.knowledge_hits) ? log.payload.knowledge_hits : []
  const matchedCount = readNumber(log.payload.matched_count) ?? hits.length
  const query = readString(log.payload.query)
  const queryText = query === null ? '' : `：${query}`
  const titles = hits
    .map((item) => (typeof item === 'object' && item !== null ? readString((item as Record<string, unknown>).title) : null))
    .filter((title): title is string => title !== null)
    .slice(0, 3)
  const titleText = titles.length > 0 ? `，相关资料：${titles.join('、')}` : ''
  return `我正在检索知识库${queryText}，已找到 ${matchedCount} 条相关资料${titleText}。`
}

function toolActivityContent(log: ExecutionStepLog): string {
  const toolId = readString(log.payload.resolved_tool_id) ?? readString(log.tool_id) ?? readString(log.payload.provider_tool_name) ?? '未知工具'
  const toolLabel = getBuiltinToolLabel(toolId)
  if (log.status === 'error') {
    return `工具调用失败：${toolLabel}。我会根据已有上下文继续处理。`
  }
  return `我正在调用工具：${toolLabel}。`
}

function policyActivityContent(log: ExecutionStepLog): string {
  if (log.phase === 'retrieval_policy_gate') {
    if (log.payload.must_return_without_model === true) {
      return '知识库没有命中可直接支撑回答的证据，本轮将停止模型自由回答。'
    }
    return '知识库检索结果已通过策略校验。'
  }
  if (log.phase === 'tool_policy_gate') {
    const decision = readString(log.payload.decision) ?? 'blocked'
    const reason = readString(log.payload.reason_code)
    if (decision === 'blocked' || log.status === 'error') {
      return `工具调用已被策略拦截${reason ? `：${reason}` : ''}。`
    }
    return '工具调用已通过策略校验。'
  }
  if (log.phase === 'final_answer_policy_gate' && log.status === 'error') {
    const reason = readString(log.payload.violation_code)
    return `最终答复已被策略修正${reason ? `：${reason}` : ''}。`
  }
  return '策略校验已完成。'
}

function knowledgeBadgeFromSnapshot(data: ExecutionSnapshot): string | null {
  const retrievalLogs = data.step_logs.filter((log) => log.phase === 'knowledge_retrieval' && log.status === 'success')
  if (retrievalLogs.length === 0) {
    return null
  }
  const latest = retrievalLogs[retrievalLogs.length - 1]
  const hits = Array.isArray(latest.payload.knowledge_hits) ? latest.payload.knowledge_hits : []
  const matchedCountRaw = latest.payload.matched_count
  const matchedCount = typeof matchedCountRaw === 'number' && Number.isFinite(matchedCountRaw) ? matchedCountRaw : hits.length
  if (matchedCount <= 0 && hits.length === 0) {
    return null
  }
  return matchedCount > 0 ? `已检索知识库 · ${matchedCount} 条候选` : '已检索知识库'
}

function activityMessagesFromSnapshot(data: ExecutionSnapshot): ConversationMessage[] {
  return data.step_logs
    .filter(
      (log) =>
        log.phase === 'tool_call' ||
        (log.phase === 'knowledge_retrieval' && hasKnowledgeHit(log)) ||
        ((log.phase === 'retrieval_policy_gate' || log.phase === 'tool_policy_gate' || log.phase === 'final_answer_policy_gate') &&
          log.status === 'error'),
    )
    .map((log, index) => ({
      id: `activity:${data.execution_id}:${log.phase}:${log.step_index}:${log.tool_id ?? 'knowledge'}:${index}`,
      role: 'assistant',
      content: log.phase === 'knowledge_retrieval' ? knowledgeActivityContent(log) : log.phase === 'tool_call' ? toolActivityContent(log) : policyActivityContent(log),
      execution_id: data.execution_id,
      status: data.status,
      source: 'activity',
    }))
}

function syncConversationMessages(messages: ConversationMessage[], data: ExecutionSnapshot): ConversationMessage[] {
  const userInput = data.last_user_input?.trim()
  let nextMessages = messages.map((message) => {
    if (message.role === 'user' && message.execution_id === data.execution_id) {
      return { ...message, status: data.status }
    }
    if (message.role === 'user' && message.execution_id === null && userInput && message.content === userInput) {
      return { ...message, execution_id: data.execution_id, status: data.status }
    }
    return message
  })

  const activityMessages = activityMessagesFromSnapshot(data)
  nextMessages = nextMessages.filter((message) => !(message.source === 'activity' && message.execution_id === data.execution_id))
  if (activityMessages.length > 0) {
    nextMessages = [...nextMessages, ...activityMessages]
  }

  const assistantContent = assistantContentFromSnapshot(data)
  if (assistantContent === null) {
    return nextMessages
  }

  const assistantId = `assistant:${data.execution_id}`
  const assistantMessage: ConversationMessage = {
    id: assistantId,
    role: 'assistant',
    content: assistantContent,
    execution_id: data.execution_id,
    status: data.status,
    source: 'chat',
    knowledge_badge: knowledgeBadgeFromSnapshot(data),
  }
  const existingIndex = nextMessages.findIndex((message) => message.id === assistantId)
  if (existingIndex >= 0) {
    nextMessages = nextMessages.slice()
    nextMessages.splice(existingIndex, 1)
  }
  return [...nextMessages, assistantMessage]
}

function normalizeIdlessState(
  state: ExecutionRuntimeState,
) {
  if (state.current_execution_id === null) {
    return {
      ...IDLE_EXECUTION_STATE,
      current_execution_id: null,
      is_execution_starting: state.is_execution_starting,
      last_user_input: state.last_user_input,
      conversation_messages: state.conversation_messages,
      conversation_messages_hidden: state.conversation_messages_hidden,
      conversation_cleared_execution_id: state.conversation_cleared_execution_id,
    }
  }
  return state
}

export const useExecutionStore = create<ExecutionStoreState>((set, get) => ({
  ...IDLE_EXECUTION_STATE,
  conversation_agent_id: null,
  conversation_sessions: [],
  active_conversation_id: null,

  startExecution: () => {
    set((state) => {
      const runtime = runtimeFromState(IDLE_EXECUTION_STATE)
      const nextSessions = updateActiveSessionList(state, runtime)
      if (state.conversation_agent_id !== null) {
        persistConversationSessions(state.conversation_agent_id, nextSessions, state.active_conversation_id)
      }
      return {
        ...state,
        ...runtime,
        conversation_sessions: nextSessions,
      }
    })
  },

  updateExecution: (data: ExecutionSnapshot) => {
    const currentId = get().current_execution_id
    const hideConversationMessages = get().conversation_messages_hidden
    const clearedExecutionId = get().conversation_cleared_execution_id

    if (currentId !== null && currentId !== data.execution_id) {
      return
    }
    if (get().termination_reason === 'USER_STOPPED') {
      return
    }

    set((state) => {
      const runtime = normalizeIdlessState({
        current_execution_id: data.execution_id,
        is_execution_starting: false,
        status: data.status,
        final_answer: data.final_answer,
        error_code: data.error_code,
        error_source: data.error_source,
        error_details: data.error_details,
        error_message: data.error_message,
        react_steps: data.react_steps,
        step_logs: data.step_logs,
        artifacts: data.artifacts ?? [],
        termination_reason: data.termination_reason,
        total_token_usage: data.total_token_usage,
        preview_phase: data.preview_phase ?? null,
        preview_url: data.preview_url ?? null,
        deployment_status: data.deployment_status ?? 'IDLE',
        deployed_url: data.deployed_url ?? null,
        last_user_input: data.last_user_input ?? get().last_user_input ?? null,
        conversation_messages:
          hideConversationMessages || clearedExecutionId === data.execution_id
            ? get().conversation_messages
            : syncConversationMessages(get().conversation_messages, data),
        conversation_messages_hidden: hideConversationMessages,
        conversation_cleared_execution_id: clearedExecutionId,
      })
      const nextSessions = updateActiveSessionList(state, runtime)
      if (state.conversation_agent_id !== null) {
        persistConversationSessions(state.conversation_agent_id, nextSessions, state.active_conversation_id)
      }
      return {
        ...state,
        ...runtime,
        conversation_sessions: nextSessions,
      }
    })
  },

  markExecutionStoppedByUser: () => {
    set((state) => {
      const executionId = state.current_execution_id
      const stoppedMessages = [
        ...state.conversation_messages,
        {
          id: `assistant:stopped:${executionId ?? Date.now()}`,
          role: 'assistant' as const,
          content: STOPPED_BY_USER_MESSAGE,
          execution_id: executionId,
          status: 'TERMINATED' as const,
          source: 'chat' as const,
        },
      ]
      const runtime = normalizeIdlessState({
        ...runtimeFromState(state),
        is_execution_starting: false,
        status: 'TERMINATED',
        final_answer: STOPPED_BY_USER_MESSAGE,
        error_message: null,
        termination_reason: 'USER_STOPPED',
        preview_phase: state.preview_phase === 'ready' || state.preview_phase === 'deployed' ? state.preview_phase : 'failed',
        deployment_status: state.deployment_status === 'SUCCEEDED' ? state.deployment_status : 'FAILED',
        conversation_messages: stoppedMessages,
      })
      const nextSessions = updateActiveSessionList(state, runtime)
      if (state.conversation_agent_id !== null) {
        persistConversationSessions(state.conversation_agent_id, nextSessions, state.active_conversation_id)
      }
      return {
        ...state,
        ...runtime,
        conversation_sessions: nextSessions,
      }
    })
  },

  finishExecution: () => {
    set((state) => {
      const runtime = normalizeIdlessState({
        current_execution_id: state.current_execution_id,
        is_execution_starting: false,
        status: state.status,
        final_answer: state.final_answer,
        error_code: state.error_code,
        error_source: state.error_source,
        error_details: state.error_details,
        error_message: state.error_message,
        react_steps: state.react_steps,
        step_logs: state.step_logs,
        artifacts: state.artifacts,
        termination_reason: state.termination_reason,
        total_token_usage: state.total_token_usage,
        preview_phase: state.preview_phase,
        preview_url: state.preview_url,
        deployment_status: state.deployment_status,
        deployed_url: state.deployed_url,
        last_user_input: state.last_user_input,
        conversation_messages: state.conversation_messages,
        conversation_messages_hidden: state.conversation_messages_hidden,
        conversation_cleared_execution_id: state.conversation_cleared_execution_id,
      })
      const nextSessions = updateActiveSessionList(state, runtime)
      if (state.conversation_agent_id !== null) {
        persistConversationSessions(state.conversation_agent_id, nextSessions, state.active_conversation_id)
      }
      return {
        ...state,
        ...runtime,
        conversation_sessions: nextSessions,
      }
    })
  },

  resetExecution: () => {
    set(() => ({
      ...IDLE_EXECUTION_STATE,
      conversation_agent_id: null,
      conversation_sessions: [],
      active_conversation_id: null,
    }))
  },

  clearConversationMessages: (agent_id = null, opening_statement = null) => {
    set((state) => {
      const resolvedAgentId = agent_id ?? state.conversation_agent_id
      const currentSessionId = state.active_conversation_id
      const runtime = {
        ...IDLE_EXECUTION_STATE,
        conversation_messages: openingMessages(resolvedAgentId, opening_statement),
        conversation_messages_hidden: false,
        conversation_cleared_execution_id: null,
      }
      const nextSessions = sortConversationSessions(
        state.conversation_sessions.map((session) => {
          if (session.id !== currentSessionId) {
            return session
          }
          return {
            ...session,
            ...runtime,
            agent_id: resolvedAgentId,
            title: '新对话',
            updated_at: Date.now(),
          }
        }),
      )
      if (resolvedAgentId !== null) {
        persistConversationSessions(resolvedAgentId, nextSessions, currentSessionId)
      }
      return {
        ...state,
        ...runtime,
        conversation_agent_id: resolvedAgentId,
        conversation_sessions: nextSessions,
      }
    })
  },

  setOpeningMessage: (agent_id, opening_statement) => {
    if (agent_id === null) {
      set(() => ({
        ...IDLE_EXECUTION_STATE,
        conversation_agent_id: null,
        conversation_sessions: [],
        active_conversation_id: null,
      }))
      return
    }

    const { sessions, activeConversationId } = readConversationSessions(agent_id, opening_statement)
    persistConversationSessions(agent_id, sessions, activeConversationId)
    if (sessions.length === 0 || activeConversationId === null) {
      set((state) => applyDraftConversation(state, agent_id, opening_statement, sessions))
      return
    }
    const activeSession = sessions.find((session) => session.id === activeConversationId) ?? sessions[0]
    set((state) => applySession(state, activeSession, sessions))
  },

  createConversationSession: (agent_id = null, opening_statement = null) => {
    const resolvedAgentId = agent_id ?? get().conversation_agent_id
    const nextSession = createConversationSessionRecord(resolvedAgentId, opening_statement)
    set((state) => {
      const nextSessions = sortConversationSessions([nextSession, ...state.conversation_sessions])
      if (resolvedAgentId !== null) {
        persistConversationSessions(resolvedAgentId, nextSessions, nextSession.id)
      }
      return applySession(
        {
          ...state,
          conversation_agent_id: resolvedAgentId,
        },
        nextSession,
        nextSessions,
      )
    })
    return nextSession.id
  },

  selectConversationSession: (session_id) => {
    set((state) => {
      const targetSession = state.conversation_sessions.find((session) => session.id === session_id)
      if (targetSession === undefined) {
        return state
      }
      if (state.conversation_agent_id !== null) {
        persistConversationSessions(state.conversation_agent_id, state.conversation_sessions, targetSession.id)
      }
      return applySession(state, targetSession, state.conversation_sessions)
    })
  },

  deleteConversationSession: (session_id, agent_id = null, opening_statement = null) => {
    set((state) => {
      const resolvedAgentId = agent_id ?? state.conversation_agent_id
      const remainingSessions = state.conversation_sessions.filter((session) => session.id !== session_id)
      const nextSessions = sortConversationSessions(remainingSessions)
      const preferredActiveId =
        state.active_conversation_id === session_id ? (nextSessions[0]?.id ?? null) : state.active_conversation_id
      const activeSession = nextSessions.find((session) => session.id === preferredActiveId) ?? nextSessions[0]
      if (resolvedAgentId !== null) {
        persistConversationSessions(resolvedAgentId, nextSessions, activeSession?.id ?? null)
      }
      if (activeSession === undefined) {
        return applyDraftConversation(
          {
            ...state,
            conversation_agent_id: resolvedAgentId,
          },
          resolvedAgentId,
          opening_statement,
          nextSessions,
        )
      }
      return applySession(
        {
          ...state,
          conversation_agent_id: resolvedAgentId,
        },
        activeSession,
        nextSessions,
      )
    })
  },

  setPreviewPhase: (phase) => {
    set((state) => {
      const runtime = {
        ...runtimeFromState(state),
        preview_phase: phase,
        status: phase === 'failed' ? 'FAILED' : state.status,
      }
      const nextSessions = updateActiveSessionList(state, runtime)
      if (state.conversation_agent_id !== null) {
        persistConversationSessions(state.conversation_agent_id, nextSessions, state.active_conversation_id)
      }
      return {
        ...state,
        preview_phase: phase,
        status: phase === 'failed' ? 'FAILED' : state.status,
        conversation_sessions: nextSessions,
      }
    })
  },

  setPreviewUrl: (url) => {
    set((state) => {
      const runtime = {
        ...runtimeFromState(state),
        preview_url: url,
      }
      const nextSessions = updateActiveSessionList(state, runtime)
      if (state.conversation_agent_id !== null) {
        persistConversationSessions(state.conversation_agent_id, nextSessions, state.active_conversation_id)
      }
      return {
        ...state,
        preview_url: url,
        conversation_sessions: nextSessions,
      }
    })
  },

  setDeploymentState: (status, deployedUrl = null) => {
    set((state) => {
      const runtime = {
        ...runtimeFromState(state),
        deployment_status: status,
        deployed_url: deployedUrl,
      }
      const nextSessions = updateActiveSessionList(state, runtime)
      if (state.conversation_agent_id !== null) {
        persistConversationSessions(state.conversation_agent_id, nextSessions, state.active_conversation_id)
      }
      return {
        ...state,
        deployment_status: status,
        deployed_url: deployedUrl,
        conversation_sessions: nextSessions,
      }
    })
  },

  setLastUserInput: (input) => {
    set((state) => {
      const runtime = {
        ...runtimeFromState(state),
        last_user_input: input,
      }
      const nextSessions = updateActiveSessionList(state, runtime)
      if (state.conversation_agent_id !== null) {
        persistConversationSessions(state.conversation_agent_id, nextSessions, state.active_conversation_id)
      }
      return {
        ...state,
        last_user_input: input,
        conversation_sessions: nextSessions,
      }
    })
  },
}))
