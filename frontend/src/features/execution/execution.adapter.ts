import { notify } from '../notifications/notify'
import { apiClient } from '../../lib/api/client'
import { ApiError, normalizeApiError } from '../../lib/api/error'
import { useAgentStore } from '../agent/agent.store'
import { useExecutionStore } from './execution.store'
import {
  IDLE_EXECUTION_STATE,
  type ConversationMessage,
  type ExecutionRuntimeState,
  type DeploymentStatus,
  type ExecutionSnapshot,
  type ExecutionStepLog,
  type ExecutionStoreState,
  type ExecutionStatus,
  type PreviewPhase,
} from './execution.types'

interface ExecuteRequest {
  input: string
  conversation_history: ConversationHistoryItem[]
  confirmed_tool_actions?: ConfirmedToolAction[]
}

interface ConversationHistoryItem {
  role: 'user' | 'assistant'
  content: string
}

export interface ConfirmedToolAction {
  tool_id: string
  action_summary?: string
  arguments_hash: string
  confirmed_at: string
}

interface ExecuteResponse {
  execution_id: string
}

const STARTABLE_STATUSES: ExecutionStatus[] = ['IDLE', 'SUCCEEDED', 'FAILED', 'TERMINATED']
const SESSION_TITLE_MAX_LENGTH = 24
const STOPPED_BY_USER_MESSAGE = '已停止：用户主动停止了当前模型行为。'
let startExecutionController: AbortController | null = null

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function createUserConversationMessage(input: string): ConversationMessage {
  return {
    id: `user:pending:${Date.now()}`,
    role: 'user',
    content: input,
    execution_id: null,
    status: 'PENDING',
    source: 'chat',
  }
}

function summarizeConversationTitle(input: string | null, messages: ConversationMessage[], fallback = '新对话'): string {
  const candidate =
    (typeof input === 'string' && input.trim().length > 0 ? input : null) ??
    messages.find((message) => message.role === 'user' && message.content.trim().length > 0)?.content ??
    fallback
  const normalized = candidate.replace(/\s+/g, ' ').trim()
  if (normalized.length <= SESSION_TITLE_MAX_LENGTH) {
    return normalized
  }
  return `${normalized.slice(0, SESSION_TITLE_MAX_LENGTH).trim()}...`
}

function syncActiveConversationState(
  state: ExecutionStoreState,
  runtime: Partial<ExecutionRuntimeState>,
): Pick<ExecutionStoreState, 'conversation_sessions'> {
  if (state.active_conversation_id === null) {
    return { conversation_sessions: state.conversation_sessions }
  }

  const nextMessages = runtime.conversation_messages ?? state.conversation_messages
  const nextLastUserInput = runtime.last_user_input ?? state.last_user_input
  return {
    conversation_sessions: state.conversation_sessions.map((session) =>
      session.id === state.active_conversation_id
        ? {
            ...session,
            ...runtime,
            title: summarizeConversationTitle(nextLastUserInput, nextMessages, session.title),
            updated_at: Date.now(),
          }
        : session,
    ),
  }
}

function buildConversationHistory(messages: ConversationMessage[]): ConversationHistoryItem[] {
  return messages
    .filter((message) => {
      if (message.content.trim().length === 0) {
        return false
      }
      if (message.source === 'opening' || message.source === 'activity') {
        return false
      }
      if (message.role === 'user') {
        return message.execution_id !== null && message.status === 'SUCCEEDED'
      }
      return message.status === 'SUCCEEDED'
    })
    .map((message) => ({
      role: message.role,
      content: message.content.trim(),
    }))
    .slice(-20)
}

function asExecutionId(value: unknown): string {
  if (typeof value !== 'string' || value.trim().length === 0) {
    throw new ApiError({
      code: 'INVALID_RESPONSE_FORMAT',
      message: '执行响应字段无效：execution_id',
      raw: value,
    })
  }
  return value
}

function asStatus(value: unknown): ExecutionSnapshot['status'] {
  if (typeof value === 'string') {
    const normalized = value.trim().toUpperCase()
    if (
      normalized === 'PENDING' ||
      normalized === 'RUNNING' ||
      normalized === 'SUCCEEDED' ||
      normalized === 'FAILED' ||
      normalized === 'TERMINATED'
    ) {
      return normalized
    }
  }

  if (
    value !== 'PENDING' &&
    value !== 'RUNNING' &&
    value !== 'SUCCEEDED' &&
    value !== 'FAILED' &&
    value !== 'TERMINATED'
  ) {
    throw new ApiError({
      code: 'INVALID_RESPONSE_FORMAT',
      message: '执行响应字段无效：status',
      raw: value,
    })
  }
  return value
}

function asNullableString(value: unknown, field: string): string | null {
  if (value === null || typeof value === 'string') {
    return value as string | null
  }
  throw new ApiError({
    code: 'INVALID_RESPONSE_FORMAT',
    message: `执行响应字段无效：${field}`,
    raw: value,
  })
}

function asNullablePreviewPhase(value: unknown): PreviewPhase | null {
  if (value === null || value === undefined) {
    return null
  }
  if (
    value === 'empty' ||
    value === 'planning' ||
    value === 'building' ||
    value === 'booting' ||
    value === 'ready' ||
    value === 'failed' ||
    value === 'deployed'
  ) {
    return value
  }
  return null
}

function asNullableDeploymentStatus(value: unknown): DeploymentStatus | null {
  if (value === null || value === undefined) {
    return null
  }
  if (value === 'IDLE' || value === 'PENDING' || value === 'SUCCEEDED' || value === 'FAILED') {
    return value
  }
  return null
}

function asNullableRecord(value: unknown, field: string): Record<string, unknown> | null {
  if (value === null || value === undefined) {
    return null
  }
  if (isRecord(value)) {
    return value
  }
  throw new ApiError({
    code: 'INVALID_RESPONSE_FORMAT',
    message: `执行响应字段无效：${field}`,
    raw: value,
  })
}

function asRecordOrEmpty(value: unknown): Record<string, unknown> {
  return isRecord(value) ? value : {}
}

function asNullableNumber(value: unknown, field: string): number | null {
  if (value === null || (typeof value === 'number' && Number.isFinite(value))) {
    return value as number | null
  }
  throw new ApiError({
    code: 'INVALID_RESPONSE_FORMAT',
    message: `执行响应字段无效：${field}`,
    raw: value,
  })
}

function resolveTotalTokenUsage(data: Record<string, unknown>): number | null {
  if (data.total_token_usage === undefined) {
    const nestedData = data.data
    if (isRecord(nestedData)) {
      const tokenUsage = nestedData.token_usage
      if (isRecord(tokenUsage)) {
        return asNullableNumber(tokenUsage.total_tokens ?? null, 'data.token_usage.total_tokens')
      }
    }
    return null
  }

  return asNullableNumber(data.total_token_usage, 'total_token_usage')
}

function asReactSteps(value: unknown): ExecutionSnapshot['react_steps'] {
  if (Array.isArray(value)) {
    return value.map((item, index) => {
      if (!isRecord(item)) {
        throw new ApiError({
          code: 'INVALID_RESPONSE_FORMAT',
          message: '执行响应字段无效：react_steps[]',
          raw: item,
        })
      }

      const actionRecord = item.action === null || item.action === undefined ? null : asRecordOrEmpty(item.action)
      const observationRecord =
        item.observation === null || item.observation === undefined ? null : asRecordOrEmpty(item.observation)
      const thought =
        typeof item.thought === 'string'
          ? item.thought
          : typeof item.reasoning === 'string'
            ? item.reasoning
            : item.thought === null
              ? null
              : null

      return {
        step_index:
          typeof item.step_index === 'number' && Number.isFinite(item.step_index) ? item.step_index : index + 1,
        thought,
        action:
          actionRecord === null
            ? null
            : {
                tool_id: typeof actionRecord.tool_id === 'string' ? actionRecord.tool_id : '',
                arguments: asRecordOrEmpty(actionRecord.arguments),
              },
        observation:
          observationRecord === null
            ? null
            : {
                ok: typeof observationRecord.ok === 'boolean' ? observationRecord.ok : observationRecord.error === undefined,
                content: observationRecord.content,
                error: asNullableRecord(observationRecord.error ?? null, 'react_steps[].observation.error'),
              },
      }
    })
  }
  throw new ApiError({
    code: 'INVALID_RESPONSE_FORMAT',
    message: '执行响应字段无效：react_steps',
    raw: value,
  })
}

function asStepLogPhase(value: unknown): ExecutionStepLog['phase'] {
  if (
    value === 'intent_classification' ||
    value === 'pre_policy_gate' ||
    value === 'knowledge_retrieval' ||
    value === 'retrieval_policy_gate' ||
    value === 'model_call' ||
    value === 'tool_policy_gate' ||
    value === 'tool_call' ||
    value === 'observation' ||
    value === 'final_answer_policy_gate' ||
    value === 'final_answer'
  ) {
    return value
  }
  throw new ApiError({
    code: 'INVALID_RESPONSE_FORMAT',
    message: '执行响应字段无效：step_logs[].phase',
    raw: value,
  })
}

function asStepLogs(value: unknown): ExecutionSnapshot['step_logs'] {
  if (value === undefined || value === null) {
    return []
  }
  if (!Array.isArray(value)) {
    throw new ApiError({
      code: 'INVALID_RESPONSE_FORMAT',
      message: '执行响应字段无效：step_logs',
      raw: value,
    })
  }

  return value.map((item, index) => {
    if (!isRecord(item)) {
      throw new ApiError({
        code: 'INVALID_RESPONSE_FORMAT',
        message: '执行响应字段无效：step_logs[]',
        raw: item,
      })
    }

    return {
      execution_id: asExecutionId(item.execution_id),
      step_index:
        typeof item.step_index === 'number' && Number.isFinite(item.step_index) && item.step_index > 0 ? item.step_index : index + 1,
      phase: asStepLogPhase(item.phase),
      tool_id: asNullableString(item.tool_id ?? null, 'step_logs[].tool_id'),
      status: item.status === 'error' ? 'error' : 'success',
      payload: asRecordOrEmpty(item.payload),
      timestamp: asNullableString(item.timestamp, 'step_logs[].timestamp') ?? '',
    }
  })
}

function asOptionalArtifacts(value: unknown): unknown[] {
  if (value === undefined || value === null) {
    return []
  }
  if (Array.isArray(value)) {
    return value
  }
  throw new ApiError({
    code: 'INVALID_RESPONSE_FORMAT',
    message: '执行响应字段无效：artifacts',
    raw: value,
  })
}

function mapExecutionResponse(data: unknown): ExecutionSnapshot {
  if (!isRecord(data)) {
    throw new ApiError({
      code: 'INVALID_RESPONSE_FORMAT',
      message: '执行响应内容无效',
      raw: data,
    })
  }

  return {
    execution_id: asExecutionId(data.execution_id),
    status: asStatus(data.status),
    final_answer: asNullableString(data.final_answer, 'final_answer'),
    error_code: asNullableString(data.error_code ?? null, 'error_code'),
    error_source: asNullableString(data.error_source ?? null, 'error_source'),
    error_details: asNullableRecord(data.error_details ?? null, 'error_details'),
    error_message: asNullableString(data.error_message ?? null, 'error_message'),
    react_steps: asReactSteps(data.react_steps),
    step_logs: asStepLogs(data.step_logs),
    artifacts: asOptionalArtifacts(data.artifacts),
    termination_reason: asNullableString(data.termination_reason ?? null, 'termination_reason'),
    total_token_usage: resolveTotalTokenUsage(data),
    preview_phase: asNullablePreviewPhase(data.preview_phase),
    preview_url: asNullableString(data.preview_url ?? null, 'preview_url'),
    deployment_status: asNullableDeploymentStatus(data.deployment_status),
    deployed_url: asNullableString(data.deployed_url ?? null, 'deployed_url'),
    last_user_input: asNullableString(data.last_user_input ?? null, 'last_user_input'),
  }
}

export const executionAdapter = {
  initializeExecutionRuntime() {
    const store = useExecutionStore.getState()
    if (store.current_execution_id === null) {
      store.resetExecution()
    }
  },

  handleAgentSwitch() {
    useExecutionStore.getState().resetExecution()
  },

  handleNewConversation() {
    const agentStore = useAgentStore.getState()
    useExecutionStore.getState().createConversationSession(agentStore.current_agent_id, agentStore.current_agent_detail?.opening_statement ?? null)
  },

  async startExecution(agent_id: string, input: string, confirmedToolActions: ConfirmedToolAction[] = []): Promise<ExecuteResponse | null> {

    const agentStore = useAgentStore.getState()
    const normalizedInput = input.trim()
    let store = useExecutionStore.getState()
    const canStart = STARTABLE_STATUSES.includes(store.status)

    if (
      agentStore.current_agent_id === null ||
      agentStore.current_agent_id !== agent_id ||
      agentStore.agent_context_status !== 'READY'
    ) {
      notify.error('智能体上下文尚未就绪')
      return null
    }

    if (!canStart || store.is_execution_starting) {
      notify.info('模型正在处理当前消息，回复完成后可以继续输入')
      return null
    }

    if (normalizedInput.length === 0) {
      return null
    }

    if (store.active_conversation_id === null) {
      store.createConversationSession(agent_id, agentStore.current_agent_detail?.opening_statement ?? null)
      store = useExecutionStore.getState()
    }

    const conversationHistory = buildConversationHistory(store.conversation_messages)
    const userMessage = createUserConversationMessage(normalizedInput)
    const conversationMessages = [...store.conversation_messages, userMessage]
    useExecutionStore.setState((state) => ({
      ...state,
      ...IDLE_EXECUTION_STATE,
      current_execution_id: null,
      is_execution_starting: true,
      status: 'PENDING',
      last_user_input: normalizedInput,
      conversation_messages: conversationMessages,
      conversation_cleared_execution_id: null,
      ...syncActiveConversationState(state, {
        ...IDLE_EXECUTION_STATE,
        current_execution_id: null,
        is_execution_starting: true,
        status: 'PENDING',
        last_user_input: normalizedInput,
        conversation_messages: conversationMessages,
        conversation_cleared_execution_id: null,
      }),
    }))

    startExecutionController?.abort()
    startExecutionController = new AbortController()

    try {
      const result = await apiClient.request<ExecuteResponse>(`/agents/${agent_id}/execute`, {
        method: 'POST',
        body: {
          input: normalizedInput,
          conversation_history: conversationHistory,
          confirmed_tool_actions: confirmedToolActions,
        } satisfies ExecuteRequest,
        signal: startExecutionController.signal,
        authMode: 'required',
      })
      startExecutionController = null
      const executionId = asExecutionId(result.data.execution_id)
      const messagesWithExecutionId = useExecutionStore.getState().conversation_messages.map((message) =>
        message.id === userMessage.id ? { ...message, execution_id: executionId } : message,
      )

      useExecutionStore.setState((state) => ({
        ...state,
        ...IDLE_EXECUTION_STATE,
        current_execution_id: executionId,
        is_execution_starting: false,
        status: 'PENDING',
        last_user_input: normalizedInput,
        preview_phase: 'planning',
        conversation_messages: messagesWithExecutionId,
        ...syncActiveConversationState(state, {
          ...IDLE_EXECUTION_STATE,
          current_execution_id: executionId,
          is_execution_starting: false,
          status: 'PENDING',
          last_user_input: normalizedInput,
          preview_phase: 'planning',
          conversation_messages: messagesWithExecutionId,
        }),
      }))

      return {
        execution_id: executionId,
      }
    } catch (error) {
      startExecutionController = null
      if (error instanceof DOMException && error.name === 'AbortError') {
        return null
      }
      const apiError = normalizeApiError(error)
      useExecutionStore.setState((state) => {
        const failedConversationMessages = [
          ...conversationMessages,
          {
            id: `assistant:start-failed:${Date.now()}`,
            role: 'assistant' as const,
            content: apiError.message,
            execution_id: null,
            status: 'FAILED' as const,
            source: 'chat' as const,
          },
        ]
        return {
          ...state,
          ...IDLE_EXECUTION_STATE,
          is_execution_starting: false,
          status: 'FAILED',
          error_message: apiError.message,
          termination_reason: apiError.message,
          last_user_input: normalizedInput,
          preview_phase: 'failed',
          deployment_status: 'FAILED',
          conversation_messages: failedConversationMessages,
          ...syncActiveConversationState(state, {
            ...IDLE_EXECUTION_STATE,
            is_execution_starting: false,
            status: 'FAILED',
            error_message: apiError.message,
            termination_reason: apiError.message,
            last_user_input: normalizedInput,
            preview_phase: 'failed',
            deployment_status: 'FAILED',
            conversation_messages: failedConversationMessages,
          }),
        }
      })
      useExecutionStore.getState().finishExecution()
      notify.error(apiError.message)
      return null
    }
  },

  async stopCurrentExecution(): Promise<void> {
    const store = useExecutionStore.getState()
    const executionId = store.current_execution_id

    if (store.is_execution_starting && executionId === null) {
      startExecutionController?.abort()
      startExecutionController = null
      useExecutionStore.getState().markExecutionStoppedByUser()
      notify.info(STOPPED_BY_USER_MESSAGE)
      return
    }

    if (executionId === null || (store.status !== 'PENDING' && store.status !== 'RUNNING')) {
      return
    }

    useExecutionStore.getState().markExecutionStoppedByUser()
    notify.info(STOPPED_BY_USER_MESSAGE)

    try {
      await apiClient.request(`/executions/${executionId}/stop`, {
        method: 'POST',
        authMode: 'required',
      })
    } catch (error) {
      notify.error(normalizeApiError(error).message)
    }
  },

  async fetchExecution(execution_id: string): Promise<ExecutionSnapshot> {
    const result = await apiClient.request<unknown>(`/executions/${execution_id}`, {
      method: 'GET',
      authMode: 'required',
    })
    return mapExecutionResponse(result.data)
  },

  applyExecutionSnapshot(response: unknown) {
    const store = useExecutionStore.getState()
    store.updateExecution(mapExecutionResponse(response))
  },

  handleExecutionFailure(error: unknown) {
    const store = useExecutionStore.getState()
    const apiError = normalizeApiError(error)

    if (store.current_execution_id === null) {
      store.resetExecution()
    } else {
      store.updateExecution({
        execution_id: store.current_execution_id,
        status: 'FAILED',
        final_answer: null,
        error_code: null,
        error_source: null,
        error_details: null,
        error_message: apiError.message,
        react_steps: [],
        step_logs: [],
        artifacts: [],
        termination_reason: apiError.message,
        total_token_usage: null,
        preview_phase: 'failed',
        preview_url: null,
        deployment_status: 'FAILED',
        deployed_url: null,
        last_user_input: store.last_user_input,
      })
      store.finishExecution()
    }

    notify.error(apiError.message)
  },
}
