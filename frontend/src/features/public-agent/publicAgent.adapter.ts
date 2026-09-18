import { ApiError } from '../../lib/api/error'
import { apiClient } from '../../lib/api/client'

export interface PublishedAgent {
  id: string
  agent_id: string
  team_id: string
  slug: string
  title: string
  description: string
  status: 'ACTIVE' | 'DISABLED'
  public_url: string
  created_at: string
  updated_at: string
}

export interface PublishAgentPayload {
  title?: string
  description?: string
  slug?: string
  status?: 'ACTIVE' | 'DISABLED'
}

export interface PublicAgentProfile {
  slug: string
  title: string
  description: string
  opening_statement: string
  avatar_url: string | null
}

export type PublicAgentSquareItem = PublicAgentProfile

export interface PublicConversationMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface PublicExecutionStart {
  execution_id: string
  request_id: string
}

export interface PublicExecutionReplay {
  execution_id: string
  agent_id: string
  status: 'PENDING' | 'RUNNING' | 'SUCCEEDED' | 'FAILED' | 'TERMINATED'
  final_answer: string | null
  error_message: string | null
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function isNotFound(error: unknown): boolean {
  if (!(error instanceof ApiError)) return false
  const raw = isRecord(error.raw) ? error.raw : null
  return error.code === 1002 || (isRecord(raw?.data) && raw.data.code === 1002) || raw?.code === 1002
}

function asString(value: unknown, field: string): string {
  if (typeof value !== 'string') {
    throw new ApiError({ code: 'INVALID_RESPONSE_FORMAT', message: `发布字段无效：${field}`, raw: value })
  }
  return value
}

function asNullableString(value: unknown, field: string): string | null {
  if (value === null || value === undefined) return null
  return asString(value, field)
}

function mapPublishedAgent(raw: unknown): PublishedAgent {
  if (!isRecord(raw)) {
    throw new ApiError({ code: 'INVALID_RESPONSE_FORMAT', message: '发布记录响应无效', raw })
  }
  const status = asString(raw.status, 'status')
  if (status !== 'ACTIVE' && status !== 'DISABLED') {
    throw new ApiError({ code: 'INVALID_RESPONSE_FORMAT', message: '发布状态无效', raw })
  }
  return {
    id: asString(raw.id, 'id'),
    agent_id: asString(raw.agent_id, 'agent_id'),
    team_id: asString(raw.team_id, 'team_id'),
    slug: asString(raw.slug, 'slug'),
    title: asString(raw.title, 'title'),
    description: asString(raw.description, 'description'),
    status,
    public_url: asString(raw.public_url, 'public_url'),
    created_at: asString(raw.created_at, 'created_at'),
    updated_at: asString(raw.updated_at, 'updated_at'),
  }
}

function mapPublicProfile(raw: unknown): PublicAgentProfile {
  if (!isRecord(raw)) {
    throw new ApiError({ code: 'INVALID_RESPONSE_FORMAT', message: '公开智能体响应无效', raw })
  }
  return {
    slug: asString(raw.slug, 'slug'),
    title: asString(raw.title, 'title'),
    description: asString(raw.description, 'description'),
    opening_statement: asString(raw.opening_statement, 'opening_statement'),
    avatar_url: asNullableString(raw.avatar_url, 'avatar_url'),
  }
}

function mapExecutionStart(raw: unknown): PublicExecutionStart {
  if (!isRecord(raw)) {
    throw new ApiError({ code: 'INVALID_RESPONSE_FORMAT', message: '公开执行响应无效', raw })
  }
  return {
    execution_id: asString(raw.execution_id, 'execution_id'),
    request_id: asString(raw.request_id, 'request_id'),
  }
}

function mapExecutionReplay(raw: unknown): PublicExecutionReplay {
  if (!isRecord(raw)) {
    throw new ApiError({ code: 'INVALID_RESPONSE_FORMAT', message: '公开执行记录响应无效', raw })
  }
  const status = asString(raw.status, 'status').toUpperCase()
  if (status !== 'PENDING' && status !== 'RUNNING' && status !== 'SUCCEEDED' && status !== 'FAILED' && status !== 'TERMINATED') {
    throw new ApiError({ code: 'INVALID_RESPONSE_FORMAT', message: '公开执行状态无效', raw })
  }
  return {
    execution_id: asString(raw.execution_id, 'execution_id'),
    agent_id: asString(raw.agent_id, 'agent_id'),
    status,
    final_answer: asNullableString(raw.final_answer, 'final_answer'),
    error_message: asNullableString(raw.error_message, 'error_message'),
  }
}

export const publicAgentAdapter = {
  async fetchPublication(agentId: string): Promise<PublishedAgent | null> {
    try {
      const result = await apiClient.request<unknown>(`/agents/${agentId}/publish`, {
        method: 'GET',
        authMode: 'required',
      })
      return mapPublishedAgent(result.data)
    } catch (error) {
      if (isNotFound(error)) return null
      throw error
    }
  },

  async publishAgent(agentId: string, payload: PublishAgentPayload): Promise<PublishedAgent> {
    const result = await apiClient.request<unknown>(`/agents/${agentId}/publish`, {
      method: 'POST',
      authMode: 'required',
      body: payload,
    })
    return mapPublishedAgent(result.data)
  },

  async updatePublication(agentId: string, payload: PublishAgentPayload): Promise<PublishedAgent> {
    const result = await apiClient.request<unknown>(`/agents/${agentId}/publish`, {
      method: 'PATCH',
      authMode: 'required',
      body: payload,
    })
    return mapPublishedAgent(result.data)
  },

  async disablePublication(agentId: string): Promise<PublishedAgent> {
    const result = await apiClient.request<unknown>(`/agents/${agentId}/publish`, {
      method: 'DELETE',
      authMode: 'required',
    })
    return mapPublishedAgent(result.data)
  },

  async fetchPublicProfile(slug: string): Promise<PublicAgentProfile> {
    const result = await apiClient.request<unknown>(`/public/agents/${slug}`, {
      method: 'GET',
      authMode: 'none',
    })
    return mapPublicProfile(result.data)
  },

  async fetchPublicSquare(): Promise<PublicAgentSquareItem[]> {
    const result = await apiClient.request<unknown>('/public/agents', {
      method: 'GET',
      authMode: 'none',
    })
    if (!Array.isArray(result.data)) {
      throw new ApiError({ code: 'INVALID_RESPONSE_FORMAT', message: '智能体广场响应无效', raw: result.data })
    }
    return result.data.map((item) => mapPublicProfile(item))
  },

  async startPublicExecution(slug: string, input: string, conversationHistory: PublicConversationMessage[]): Promise<PublicExecutionStart> {
    const result = await apiClient.request<unknown>(`/public/agents/${slug}/execute`, {
      method: 'POST',
      authMode: 'none',
      body: {
        input,
        conversation_history: conversationHistory,
      },
    })
    return mapExecutionStart(result.data)
  },

  async fetchPublicExecution(slug: string, executionId: string): Promise<PublicExecutionReplay> {
    const result = await apiClient.request<unknown>(`/public/agents/${slug}/executions/${executionId}`, {
      method: 'GET',
      authMode: 'none',
    })
    return mapExecutionReplay(result.data)
  },
}
