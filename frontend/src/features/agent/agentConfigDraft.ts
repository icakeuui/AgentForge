export const AGENT_CONFIG_DRAFT_STORAGE_KEY = 'AGENTFORGE_AGENT_CONFIG_DRAFT_V1'
export const AGENT_CONFIG_DRAFT_EVENT = 'agent-config-draft:changed'

export interface AgentConfigDraft {
  name: string
  avatar_url: string
  description: string
  opening_statement: string
  llm_provider_url: string
  llm_api_key: string
  llm_model_name: string
  embedding_provider: string
  embedding_base_url: string
  embedding_api_key: string
  embedding_model: string
  temperature: string
  max_tokens: string
}

const EMPTY_DRAFT: AgentConfigDraft = {
  name: '',
  avatar_url: '',
  description: '',
  opening_statement: '你好，我是你的智能体。你可以直接告诉我想测试的问题或任务。',
  llm_provider_url: '',
  llm_api_key: '',
  llm_model_name: '',
  embedding_provider: 'openai_compatible',
  embedding_base_url: 'https://api.openai.com/v1',
  embedding_api_key: '',
  embedding_model: 'text-embedding-3-small',
  temperature: '0.7',
  max_tokens: '1000',
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function readDraftText(raw: Record<string, unknown>, key: keyof AgentConfigDraft, fallback: string): string {
  const value = raw[key]
  return typeof value === 'string' ? value : fallback
}

function emitDraftChanged(): void {
  if (typeof window === 'undefined') {
    return
  }
  window.dispatchEvent(new CustomEvent(AGENT_CONFIG_DRAFT_EVENT))
}

export function getEmptyAgentConfigDraft(): AgentConfigDraft {
  return { ...EMPTY_DRAFT }
}

export function readAgentConfigDraft(agentId: string | null = null): AgentConfigDraft | null {
  if (typeof window === 'undefined') {
    return null
  }

  const raw = window.localStorage.getItem(AGENT_CONFIG_DRAFT_STORAGE_KEY)
  if (raw === null) {
    return null
  }

  try {
    const parsed = JSON.parse(raw)
    if (!isRecord(parsed)) {
      return null
    }
    const draftAgentId = typeof parsed.__agent_id === 'string' ? parsed.__agent_id : null
    if (agentId === null && draftAgentId !== null) {
      return null
    }
    if (agentId !== null && draftAgentId !== agentId) {
      return null
    }
    return {
      name: readDraftText(parsed, 'name', EMPTY_DRAFT.name),
      avatar_url: readDraftText(parsed, 'avatar_url', EMPTY_DRAFT.avatar_url),
      description: readDraftText(parsed, 'description', EMPTY_DRAFT.description),
      opening_statement: readDraftText(parsed, 'opening_statement', EMPTY_DRAFT.opening_statement),
      llm_provider_url: readDraftText(parsed, 'llm_provider_url', EMPTY_DRAFT.llm_provider_url),
      llm_api_key: readDraftText(parsed, 'llm_api_key', EMPTY_DRAFT.llm_api_key),
      llm_model_name: readDraftText(parsed, 'llm_model_name', EMPTY_DRAFT.llm_model_name),
      embedding_provider: readDraftText(parsed, 'embedding_provider', EMPTY_DRAFT.embedding_provider),
      embedding_base_url: readDraftText(parsed, 'embedding_base_url', EMPTY_DRAFT.embedding_base_url),
      embedding_api_key: readDraftText(parsed, 'embedding_api_key', EMPTY_DRAFT.embedding_api_key),
      embedding_model: readDraftText(parsed, 'embedding_model', EMPTY_DRAFT.embedding_model),
      temperature: readDraftText(parsed, 'temperature', EMPTY_DRAFT.temperature),
      max_tokens: readDraftText(parsed, 'max_tokens', EMPTY_DRAFT.max_tokens),
    }
  } catch {
    return null
  }
}

export function saveAgentConfigDraft(draft: AgentConfigDraft, agentId: string | null = null): void {
  if (typeof window === 'undefined') {
    return
  }

  window.localStorage.setItem(AGENT_CONFIG_DRAFT_STORAGE_KEY, JSON.stringify({ ...draft, __agent_id: agentId }))
  emitDraftChanged()
}

export function clearAgentConfigDraft(agentId: string | null = null): void {
  if (typeof window === 'undefined') {
    return
  }

  const current = readAgentConfigDraft(agentId)
  if (current === null) {
    return
  }

  window.localStorage.removeItem(AGENT_CONFIG_DRAFT_STORAGE_KEY)
  emitDraftChanged()
}

export function ensureCreateAgentConfigDraft(): AgentConfigDraft {
  const existing = readAgentConfigDraft()
  if (existing !== null) {
    return existing
  }

  const nextDraft = getEmptyAgentConfigDraft()
  saveAgentConfigDraft(nextDraft, null)
  return nextDraft
}
