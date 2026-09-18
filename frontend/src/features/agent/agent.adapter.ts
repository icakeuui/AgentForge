import { apiClient } from '../../lib/api/client'
import { ApiError } from '../../lib/api/error'

export interface AgentRuntimeConfig {
  temperature: number
  max_tokens: number | null
  context_window?: number | null
  reserved_completion_tokens?: number | null
}

export interface AgentCapabilityFlags {
  supports_tools: boolean
}

export interface AgentEmbeddingConfig {
  provider: string
  base_url: string
  model: string
  has_api_key: boolean
}

export interface AgentDetail {
  id: string
  name: string
  description: string
  opening_statement: string
  avatar_url: string | null
  llm_provider_url: string
  llm_model_name: string
  runtime_config: AgentRuntimeConfig
  capability_flags: AgentCapabilityFlags
  tools: string[]
  constraints: Record<string, unknown>
  has_api_key: boolean
  archived: boolean
  is_available: boolean
  availability_reason: string | null
  embedding: AgentEmbeddingConfig | null
}

export interface CreateAgentPayload {
  name: string
  description: string
  opening_statement: string
  avatar_url: string | null
  llm_provider_url: string
  llm_api_key: string
  llm_model_name: string
  embedding?: {
    provider: string
    base_url?: string
    model: string
    api_key?: string
  }
  runtime_config: AgentRuntimeConfig
  capability_flags: AgentCapabilityFlags
  tools: string[]
  constraints: Record<string, unknown>
}

export interface UpdateAgentPayload {
  name?: string
  description?: string
  opening_statement?: string
  avatar_url?: string | null
  llm_provider_url?: string
  llm_api_key?: string
  llm_model_name?: string
  embedding?: {
    provider: string
    base_url?: string
    model: string
    api_key?: string
  }
  runtime_config?: AgentRuntimeConfig
  capability_flags?: AgentCapabilityFlags
  tools?: string[]
  constraints?: Record<string, unknown>
  archived?: boolean
}

interface CreateAgentResponse {
  id: string
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function asString(value: unknown, field: string): string {
  if (typeof value !== 'string') {
    throw new ApiError({
      code: 'INVALID_RESPONSE_FORMAT',
      message: `智能体字段无效：${field}`,
      raw: value,
    })
  }
  return value
}

function asNumber(value: unknown, field: string): number {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    throw new ApiError({
      code: 'INVALID_RESPONSE_FORMAT',
      message: `智能体字段无效：${field}`,
      raw: value,
    })
  }
  return value
}

function asStringArray(value: unknown, field: string): string[] {
  if (!Array.isArray(value) || value.some((item) => typeof item !== 'string')) {
    throw new ApiError({
      code: 'INVALID_RESPONSE_FORMAT',
      message: `智能体字段无效：${field}`,
      raw: value,
    })
  }
  return value
}

function mapAgentRuntimeConfig(raw: unknown): AgentRuntimeConfig {
  const config = isRecord(raw) ? raw : {}
  const temperature = typeof config.temperature === 'number' && !Number.isNaN(config.temperature) ? config.temperature : 0.7
  const maxTokensRaw = config.max_tokens
  const contextWindowRaw = config.context_window
  const reservedCompletionTokensRaw = config.reserved_completion_tokens
  return {
    temperature,
    max_tokens: maxTokensRaw === null || maxTokensRaw === undefined ? null : asNumber(maxTokensRaw, 'runtime_config.max_tokens'),
    context_window:
      contextWindowRaw === null || contextWindowRaw === undefined
        ? null
        : asNumber(contextWindowRaw, 'runtime_config.context_window'),
    reserved_completion_tokens:
      reservedCompletionTokensRaw === null || reservedCompletionTokensRaw === undefined
        ? null
        : asNumber(reservedCompletionTokensRaw, 'runtime_config.reserved_completion_tokens'),
  }
}

function mapAgentCapabilityFlags(raw: unknown): AgentCapabilityFlags {
  const flags = isRecord(raw) ? raw : {}
  return {
    supports_tools: typeof flags.supports_tools === 'boolean' ? flags.supports_tools : true,
  }
}

function mapAgentDetail(raw: unknown): AgentDetail {
  if (!isRecord(raw)) {
    throw new ApiError({
      code: 'INVALID_RESPONSE_FORMAT',
      message: '智能体详情响应无效',
      raw,
    })
  }

  const legacyConfig = isRecord(raw.config) ? raw.config : {}

  return {
    id: asString(raw.id, 'id'),
    name: asString((raw.name ?? legacyConfig.name ?? '未命名智能体') as unknown, 'name'),
    description: asString((raw.description ?? legacyConfig.description ?? '') as unknown, 'description'),
    opening_statement: asString(
      (raw.opening_statement ?? legacyConfig.opening_statement ?? '你好，我是你的智能体。你可以直接告诉我想测试的问题或任务。') as unknown,
      'opening_statement',
    ),
    avatar_url:
      raw.avatar_url === null || raw.avatar_url === undefined
        ? legacyConfig.avatar_url === null || legacyConfig.avatar_url === undefined
          ? null
          : asString(legacyConfig.avatar_url, 'avatar_url')
        : asString(raw.avatar_url, 'avatar_url'),
    llm_provider_url: asString((raw.llm_provider_url ?? legacyConfig.llm_provider_url ?? '') as unknown, 'llm_provider_url'),
    llm_model_name: asString((raw.llm_model_name ?? legacyConfig.llm_model_name ?? '') as unknown, 'llm_model_name'),
    runtime_config: mapAgentRuntimeConfig(raw.runtime_config ?? legacyConfig.runtime_config),
    capability_flags: mapAgentCapabilityFlags(raw.capability_flags ?? legacyConfig.capability_flags),
    tools: asStringArray((raw.tools ?? legacyConfig.tools ?? []) as unknown, 'tools'),
    constraints: isRecord(raw.constraints) ? raw.constraints : isRecord(legacyConfig.constraints) ? legacyConfig.constraints : {},
    has_api_key: Boolean(raw.has_api_key ?? legacyConfig.has_api_key ?? legacyConfig.llm_api_key_encrypted),
    archived: Boolean(raw.archived ?? legacyConfig.archived ?? false),
    is_available: typeof raw.is_available === 'boolean' ? raw.is_available : true,
    availability_reason:
      raw.availability_reason === null || raw.availability_reason === undefined
        ? null
        : asString(raw.availability_reason, 'availability_reason'),
    embedding:
      raw.embedding === null || raw.embedding === undefined
        ? null
        : {
            provider: isRecord(raw.embedding) && typeof raw.embedding.provider === 'string' ? raw.embedding.provider : 'openai_compatible',
            base_url: isRecord(raw.embedding) && typeof raw.embedding.base_url === 'string' ? raw.embedding.base_url : '',
            model: isRecord(raw.embedding) && typeof raw.embedding.model === 'string' ? raw.embedding.model : '',
            has_api_key: isRecord(raw.embedding) && raw.embedding.has_api_key === true,
          },
  }
}

function mapAgentList(raw: unknown): AgentDetail[] {
  if (!Array.isArray(raw)) {
    throw new ApiError({
      code: 'INVALID_RESPONSE_FORMAT',
      message: '智能体列表响应无效',
      raw,
    })
  }

  return raw.map((item) => mapAgentDetail(item))
}

function mapCreateAgentResponse(raw: unknown): CreateAgentResponse {
  if (!isRecord(raw)) {
    throw new ApiError({
      code: 'INVALID_RESPONSE_FORMAT',
      message: '创建智能体响应无效',
      raw,
    })
  }
  return {
    id: asString(raw.id, 'id'),
  }
}

export const agentAdapter = {
  async fetchAgentList(): Promise<AgentDetail[]> {
    const result = await apiClient.request<unknown>('/agents', {
      method: 'GET',
      authMode: 'required',
    })
    return mapAgentList(result.data)
  },

  async fetchAgentDetail(agent_id: string): Promise<AgentDetail> {
    const result = await apiClient.request<unknown>(`/agents/${agent_id}`, {
      method: 'GET',
      authMode: 'required',
    })
    return mapAgentDetail(result.data)
  },

  async createAgent(payload: CreateAgentPayload): Promise<AgentDetail> {
    const result = await apiClient.request<unknown>('/agents', {
      method: 'POST',
      body: payload,
      authMode: 'required',
    })
    const created = mapCreateAgentResponse(result.data)
    return await this.fetchAgentDetail(created.id)
  },

  async updateAgent(agent_id: string, payload: UpdateAgentPayload): Promise<AgentDetail> {
    await apiClient.request<unknown>(`/agents/${agent_id}`, {
      method: 'PATCH',
      body: payload,
      authMode: 'required',
    })
    return await this.fetchAgentDetail(agent_id)
  },

  async deleteAgent(agent_id: string): Promise<AgentDetail> {
    const result = await apiClient.request<unknown>(`/agents/${agent_id}`, {
      method: 'DELETE',
      authMode: 'required',
    })
    return mapAgentDetail(result.data)
  },
}
