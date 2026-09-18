import { apiClient } from '../../lib/api/client'
import { ApiError } from '../../lib/api/error'

export interface KnowledgeDocument {
  id: string
  agent_id: string
  title: string
  content: string
  chunk_count: number
  document_type: string
  source_filename: string | null
  source_mime_type: string | null
  source_hash: string | null
  version_label: string | null
  effective_from: string | null
  effective_to: string | null
  status: string
  metadata: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface KnowledgeSearchResult {
  document_id: string
  chunk_id: string
  title: string
  content: string
  score: number
  match_type: string
  document_type: string
  article_no: string | null
  article_label: string | null
  section_path: string[]
  page_no: number | null
  citation_label: string
  is_direct_evidence: boolean
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function asString(value: unknown, field: string): string {
  if (typeof value !== 'string') {
    throw new ApiError({ code: 'INVALID_RESPONSE_FORMAT', message: `知识库字段无效：${field}`, raw: value })
  }
  return value
}

function asOptionalString(value: unknown, field: string): string | null {
  if (value === null || value === undefined) return null
  return asString(value, field)
}

function asNumber(value: unknown, field: string): number {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    throw new ApiError({ code: 'INVALID_RESPONSE_FORMAT', message: `知识库字段无效：${field}`, raw: value })
  }
  return value
}

function asOptionalNumber(value: unknown, field: string): number | null {
  if (value === null || value === undefined) return null
  return asNumber(value, field)
}

function asBoolean(value: unknown, field: string): boolean {
  if (typeof value !== 'boolean') {
    throw new ApiError({ code: 'INVALID_RESPONSE_FORMAT', message: `知识库字段无效：${field}`, raw: value })
  }
  return value
}

function asStringArray(value: unknown, field: string): string[] {
  if (!Array.isArray(value)) {
    throw new ApiError({ code: 'INVALID_RESPONSE_FORMAT', message: `知识库字段无效：${field}`, raw: value })
  }
  return value.map((item, index) => asString(item, `${field}[${index}]`))
}

function asMetadata(value: unknown): Record<string, unknown> {
  if (value === null || value === undefined) return {}
  if (!isRecord(value)) {
    throw new ApiError({ code: 'INVALID_RESPONSE_FORMAT', message: '知识库字段无效：metadata', raw: value })
  }
  return value
}

function mapDocument(raw: unknown): KnowledgeDocument {
  if (!isRecord(raw)) {
    throw new ApiError({ code: 'INVALID_RESPONSE_FORMAT', message: '知识文档响应无效', raw })
  }
  return {
    id: asString(raw.id, 'id'),
    agent_id: asString(raw.agent_id, 'agent_id'),
    title: asString(raw.title, 'title'),
    content: asString(raw.content, 'content'),
    chunk_count: asNumber(raw.chunk_count, 'chunk_count'),
    document_type: typeof raw.document_type === 'string' ? raw.document_type : 'other',
    source_filename: asOptionalString(raw.source_filename, 'source_filename'),
    source_mime_type: asOptionalString(raw.source_mime_type, 'source_mime_type'),
    source_hash: asOptionalString(raw.source_hash, 'source_hash'),
    version_label: asOptionalString(raw.version_label, 'version_label'),
    effective_from: asOptionalString(raw.effective_from, 'effective_from'),
    effective_to: asOptionalString(raw.effective_to, 'effective_to'),
    status: typeof raw.status === 'string' ? raw.status : 'ACTIVE',
    metadata: asMetadata(raw.metadata),
    created_at: asString(raw.created_at, 'created_at'),
    updated_at: asString(raw.updated_at, 'updated_at'),
  }
}

function mapSearchResult(raw: unknown): KnowledgeSearchResult {
  if (!isRecord(raw)) {
    throw new ApiError({ code: 'INVALID_RESPONSE_FORMAT', message: '知识检索响应无效', raw })
  }
  return {
    document_id: asString(raw.document_id, 'document_id'),
    chunk_id: asString(raw.chunk_id, 'chunk_id'),
    title: asString(raw.title, 'title'),
    content: asString(raw.content, 'content'),
    score: asNumber(raw.score, 'score'),
    match_type: typeof raw.match_type === 'string' ? raw.match_type : 'keyword',
    document_type: typeof raw.document_type === 'string' ? raw.document_type : 'other',
    article_no: asOptionalString(raw.article_no, 'article_no'),
    article_label: asOptionalString(raw.article_label, 'article_label'),
    section_path: raw.section_path === undefined ? [] : asStringArray(raw.section_path, 'section_path'),
    page_no: asOptionalNumber(raw.page_no, 'page_no'),
    citation_label: typeof raw.citation_label === 'string' ? raw.citation_label : '',
    is_direct_evidence: raw.is_direct_evidence === undefined ? true : asBoolean(raw.is_direct_evidence, 'is_direct_evidence'),
  }
}

export const knowledgeAdapter = {
  async listDocuments(agentId: string): Promise<KnowledgeDocument[]> {
    const result = await apiClient.request<unknown[]>(`/agents/${agentId}/knowledge`, {
      method: 'GET',
      authMode: 'required',
    })
    return Array.isArray(result.data) ? result.data.map((item) => mapDocument(item)) : []
  },

  async createDocument(agentId: string, payload: { title: string; content: string }): Promise<KnowledgeDocument> {
    const result = await apiClient.request<unknown>(`/agents/${agentId}/knowledge`, {
      method: 'POST',
      body: payload,
      authMode: 'required',
    })
    return mapDocument(result.data)
  },

  async uploadDocument(agentId: string, payload: { file: File; title?: string }): Promise<KnowledgeDocument> {
    const formData = new FormData()
    formData.append('file', payload.file)
    if (payload.title?.trim()) {
      formData.append('title', payload.title.trim())
    }
    const result = await apiClient.request<unknown>(`/agents/${agentId}/knowledge/upload`, {
      method: 'POST',
      body: formData,
      authMode: 'required',
    })
    return mapDocument(result.data)
  },

  async search(agentId: string, payload: { query: string; limit?: number }): Promise<KnowledgeSearchResult[]> {
    const result = await apiClient.request<unknown[]>(`/agents/${agentId}/knowledge/search`, {
      method: 'POST',
      body: payload,
      authMode: 'required',
    })
    return Array.isArray(result.data) ? result.data.map((item) => mapSearchResult(item)) : []
  },

  async deleteDocument(agentId: string, documentId: string): Promise<void> {
    await apiClient.request<unknown>(`/agents/${agentId}/knowledge/${documentId}`, {
      method: 'DELETE',
      authMode: 'required',
    })
  },
}
