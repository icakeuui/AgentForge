import { Bot, CheckCircle2, CircleAlert, Copy, ExternalLink, Eye, EyeOff, Link2, MessageSquareText, Plus, Power, Save, ScrollText, Wrench } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'

import type { AgentDetail } from '../../../../features/agent/agent.adapter'
import {
  clearAgentConfigDraft,
  ensureCreateAgentConfigDraft,
  getEmptyAgentConfigDraft,
  readAgentConfigDraft,
  saveAgentConfigDraft,
} from '../../../../features/agent/agentConfigDraft'
import { useAgentStore } from '../../../../features/agent/agent.store'
import { notify } from '../../../../features/notifications/notify'
import { publicAgentAdapter, type PublishedAgent } from '../../../../features/public-agent/publicAgent.adapter'
import { BUILTIN_TOOL_OPTIONS } from '../../../../features/tools/tools.catalog'
import { useBuilderTabsStore } from '../../../../features/ui-shell/builderTabs.store'
import { normalizeApiError } from '../../../../lib/api/error'
import { Badge } from '../../../ui/Badge'
import { Button } from '../../../ui/Button'
import { Input } from '../../../ui/Input'

type ConfigMode = 'create' | 'edit'

const DEFAULT_AGENT_TOOL_IDS = BUILTIN_TOOL_OPTIONS.map((tool) => tool.id)

interface AgentConfigFormState {
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

function validateEndpoint(value: string): string | null {
  const normalized = value.trim()
  if (normalized.length === 0) return '基础地址为必填项'
  try {
    const parsed = new URL(normalized)
    const host = parsed.hostname.toLowerCase()
    if (!['http:', 'https:'].includes(parsed.protocol)) return '基础地址必须使用 http 或 https'
    if (host === 'localhost' || host === 'host.docker.internal' || host === 'docker.internal') return '禁止使用本机或 Docker 内部地址'
    if (host === '127.0.0.1' || host.startsWith('192.168.')) return '禁止使用内网地址'
  } catch {
    return '基础地址格式非法'
  }
  return null
}

function parseArcErrorCode(raw: unknown): string | null {
  if (typeof raw !== 'object' || raw === null) return null
  const envelope = raw as Record<string, unknown>
  const data = envelope.data as Record<string, unknown> | undefined
  const error = data?.error as Record<string, unknown> | undefined
  return typeof error?.code === 'string' ? error.code : null
}

function mapArcErrorCode(code: string | null): string {
  if (code === 'AUTH_FAILED') return '鉴权失败：请检查接口密钥'
  if (code === 'MODEL_NOT_FOUND') return '模型不存在：请检查模型名称'
  if (code === 'INVALID_MODEL_REQUEST') return '模型请求参数无效：请检查模型名称、接口地址和服务商要求'
  if (code === 'MODEL_CAPABILITY_MISMATCH') return '模型能力不匹配：当前模型不支持工具调用'
  if (code === 'INVALID_ENDPOINT') return '接口地址非法或被安全策略阻断'
  if (code === 'MISSING_API_KEY') return '缺少接口密钥'
  if (code === 'PROVIDER_RATE_LIMITED') return '服务商限流，请稍后重试'
  if (code === 'INVALID_TOOL_CALL') return '工具调用参数非法'
  if (code === 'MODEL_OUTPUT_TRUNCATED') return '模型输出被截断'
  if (code === 'NETWORK_ERROR') return '网络错误：请检查连接'
  return '请求失败，请检查配置后重试'
}

function formFromAgent(agent: AgentDetail): AgentConfigFormState {
  return {
    name: agent.name,
    avatar_url: agent.avatar_url ?? '',
    description: agent.description,
    opening_statement: agent.opening_statement,
    llm_provider_url: agent.llm_provider_url,
    llm_api_key: '',
    llm_model_name: agent.llm_model_name,
    embedding_provider: agent.embedding?.provider ?? 'openai_compatible',
    embedding_base_url: agent.embedding?.base_url ?? 'https://api.openai.com/v1',
    embedding_api_key: '',
    embedding_model: agent.embedding?.model ?? 'text-embedding-3-small',
    temperature: String(agent.runtime_config.temperature),
    max_tokens: agent.runtime_config.max_tokens === null ? '' : String(agent.runtime_config.max_tokens),
  }
}

function readMode(params: Record<string, unknown> | null | undefined): ConfigMode | null {
  return params?.mode === 'create' || params?.mode === 'edit' ? params.mode : null
}

function readAgentId(params: Record<string, unknown> | null | undefined): string | null {
  return typeof params?.agentId === 'string' && params.agentId.trim().length > 0 ? params.agentId : null
}

function absolutePublicUrl(publication: PublishedAgent): string {
  if (typeof window === 'undefined') return publication.public_url
  return `${window.location.origin}${publication.public_url}`
}

function PublicationPanel({ agent }: { agent: AgentDetail | null }) {
  const [publication, setPublication] = useState<PublishedAgent | null>(null)
  const [slug, setSlug] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setPublication(null)
    setSlug('')
    setError(null)
    if (agent === null) return

    setIsLoading(true)
    publicAgentAdapter
      .fetchPublication(agent.id)
      .then((record) => {
        if (cancelled) return
        setPublication(record)
        setSlug(record?.slug ?? '')
      })
      .catch((err) => {
        if (!cancelled) setError(normalizeApiError(err).message)
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [agent])

  const publish = async () => {
    if (agent === null) return
    setIsSaving(true)
    setError(null)
    try {
      const payload = {
        title: agent.name,
        description: agent.description,
        slug: slug.trim().length > 0 ? slug.trim() : undefined,
        status: 'ACTIVE' as const,
      }
      const next = publication === null
        ? await publicAgentAdapter.publishAgent(agent.id, payload)
        : await publicAgentAdapter.updatePublication(agent.id, payload)
      setPublication(next)
      setSlug(next.slug)
      notify.success(publication === null ? '公开链接已生成' : '公开链接已更新')
    } catch (err) {
      setError(normalizeApiError(err).message)
    } finally {
      setIsSaving(false)
    }
  }

  const disable = async () => {
    if (agent === null || publication === null) return
    setIsSaving(true)
    setError(null)
    try {
      const next = await publicAgentAdapter.disablePublication(agent.id)
      setPublication(next)
      notify.success('公开链接已停用')
    } catch (err) {
      setError(normalizeApiError(err).message)
    } finally {
      setIsSaving(false)
    }
  }

  const copyLink = async () => {
    if (publication === null) return
    const url = absolutePublicUrl(publication)
    await navigator.clipboard?.writeText(url)
    notify.success('公开链接已复制')
  }

  const openLink = () => {
    if (publication === null) return
    window.open(absolutePublicUrl(publication), '_blank', 'noopener,noreferrer')
  }

  const isActive = publication?.status === 'ACTIVE'

  return (
    <section className="space-y-3 rounded-token-md border border-border bg-bg p-4">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-sm font-semibold text-text-main">
          <Link2 size={15} className="text-text-muted" />
          公开链接
        </div>
        <Badge variant={isActive ? 'success' : publication ? 'neutral' : 'info'}>
          {isLoading ? '读取中' : isActive ? '已发布' : publication ? '已停用' : '未发布'}
        </Badge>
      </div>

      {agent === null ? (
        <p className="text-xs leading-relaxed text-text-muted">保存或选择一个智能体后，可以生成外部可访问的聊天链接。</p>
      ) : (
        <>
          <Input
            id="public-agent-slug"
            label="链接标识"
            placeholder="留空自动生成"
            value={slug}
            onChange={(event) => setSlug(event.target.value)}
            disabled={isLoading || isSaving}
          />
          {publication ? (
            <p className="break-all rounded-token-md border border-border bg-surface px-3 py-2 text-xs text-text-sub">
              {absolutePublicUrl(publication)}
            </p>
          ) : (
            <p className="text-xs leading-relaxed text-text-muted">发布后访客可通过链接直接和此智能体对话。</p>
          )}
          {error ? <p className="text-xs text-red-500">{error}</p> : null}
          <div className="grid grid-cols-2 gap-2">
            <Button type="button" variant="primary" size="sm" leftIcon={isActive ? <Save size={13} /> : <Power size={13} />} onClick={() => void publish()} disabled={isLoading || isSaving}>
              {isSaving ? '处理中' : isActive ? '更新' : '发布'}
            </Button>
            <Button type="button" variant="secondary" size="sm" leftIcon={<Copy size={13} />} onClick={() => void copyLink()} disabled={!publication}>
              复制
            </Button>
            <Button type="button" variant="secondary" size="sm" leftIcon={<ExternalLink size={13} />} onClick={openLink} disabled={!publication}>
              打开
            </Button>
            <Button type="button" variant="ghost" size="sm" onClick={() => void disable()} disabled={!publication || !isActive || isSaving}>
              停用
            </Button>
          </div>
        </>
      )}
    </section>
  )
}

export function AgentConfigTabPage() {
  const tabs = useBuilderTabsStore((state) => state.tabs)
  const activeTabId = useBuilderTabsStore((state) => state.activeTabId)
  const agentList = useAgentStore((state) => state.agent_list)
  const currentAgentDetail = useAgentStore((state) => state.current_agent_detail)
  const currentAgentId = useAgentStore((state) => state.current_agent_id)

  const activeTab = tabs.find((tab) => tab.id === activeTabId)
  const requestedMode = readMode(activeTab?.params)
  const requestedAgentId = readAgentId(activeTab?.params)
  const targetId = requestedAgentId ?? currentAgentDetail?.id ?? currentAgentId
  const targetAgent =
    targetId === currentAgentDetail?.id ? currentAgentDetail : agentList.find((agent) => agent.id === targetId) ?? null
  const initialMode: ConfigMode = requestedMode === 'create' || targetAgent === null ? 'create' : 'edit'
  const editorKey = `${initialMode}:${targetAgent?.id ?? 'new'}:${requestedMode ?? 'auto'}:${requestedAgentId ?? 'current'}`

  return <AgentConfigEditor key={editorKey} initialMode={initialMode} initialAgent={initialMode === 'edit' ? targetAgent : null} />
}

interface AgentConfigEditorProps {
  initialMode: ConfigMode
  initialAgent: AgentDetail | null
}

function AgentConfigEditor({ initialMode, initialAgent }: AgentConfigEditorProps) {
  const openTab = useBuilderTabsStore((state) => state.openTab)
  const setTabStateByType = useBuilderTabsStore((state) => state.setTabStateByType)
  const agentList = useAgentStore((state) => state.agent_list)
  const currentAgentDetail = useAgentStore((state) => state.current_agent_detail)
  const currentAgentId = useAgentStore((state) => state.current_agent_id)
  const createAgent = useAgentStore((state) => state.createAgent)
  const updateAgent = useAgentStore((state) => state.updateAgent)

  const [configMode, setConfigMode] = useState<ConfigMode>(initialMode)
  const [editingAgentId, setEditingAgentId] = useState<string | null>(initialAgent?.id ?? null)
  const [form, setForm] = useState<AgentConfigFormState>(() => {
    if (initialAgent !== null) {
      return formFromAgent(initialAgent)
    }
    return readAgentConfigDraft() ?? getEmptyAgentConfigDraft()
  })
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [showApiKey, setShowApiKey] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  const editingAgent = useMemo(() => {
    if (editingAgentId === null) return null
    if (currentAgentDetail?.id === editingAgentId) return currentAgentDetail
    return agentList.find((agent) => agent.id === editingAgentId) ?? null
  }, [agentList, currentAgentDetail, editingAgentId])

  const fieldErrors = useMemo(() => {
    const errors: Partial<Record<keyof AgentConfigFormState, string>> = {}
    if (form.name.trim().length === 0) errors.name = '名称为必填项'
    if (form.description.trim().length === 0) errors.description = '描述为必填项'
    if (form.opening_statement.trim().length === 0) errors.opening_statement = '开场白为必填项'
    const endpointErr = validateEndpoint(form.llm_provider_url)
    if (endpointErr) errors.llm_provider_url = endpointErr
    if (form.llm_model_name.trim().length === 0) errors.llm_model_name = '模型名称为必填项'
    if (configMode === 'create' && form.llm_api_key.trim().length === 0) errors.llm_api_key = '接口密钥为必填项'
    if (configMode === 'edit' && editingAgent?.has_api_key === false && form.llm_api_key.trim().length === 0) {
      errors.llm_api_key = '当前智能体尚未保存接口密钥，请填写'
    }
    return errors
  }, [configMode, editingAgent?.has_api_key, form])

  const canSubmit = Object.keys(fieldErrors).length === 0 && !isSubmitting

  const setFormField = <K extends keyof AgentConfigFormState,>(key: K, value: AgentConfigFormState[K]) => {
    setForm((prev) => {
      const next = { ...prev, [key]: value }
      if (configMode === 'create') {
        saveAgentConfigDraft(next, null)
      }
      return next
    })
    setSubmitError(null)
    setTabStateByType('agent_config', { status: 'dirty', message: '待保存配置' })
  }

  const setEmbeddingProvider = (provider: string) => {
    setForm((prev) => {
      const next = provider === 'bge_local'
        ? {
            ...prev,
            embedding_provider: provider,
            embedding_base_url: '',
            embedding_api_key: '',
            embedding_model: 'BAAI/bge-large-zh-v1.5',
          }
        : {
            ...prev,
            embedding_provider: 'openai_compatible',
            embedding_base_url: prev.embedding_base_url || 'https://api.openai.com/v1',
            embedding_model: prev.embedding_model === 'BAAI/bge-large-zh-v1.5' ? 'text-embedding-3-small' : prev.embedding_model,
          }
      if (configMode === 'create') saveAgentConfigDraft(next, null)
      return next
    })
    setSubmitError(null)
    setTabStateByType('agent_config', { status: 'dirty', message: '待保存配置' })
  }

  const startCreate = () => {
    const draft = ensureCreateAgentConfigDraft()
    setConfigMode('create')
    setEditingAgentId(null)
    setForm(draft)
    setSubmitError(null)
    setShowApiKey(false)
    openTab({ type: 'agent_config', params: { mode: 'create' }, status: 'idle', message: '准备创建智能体' })
  }

  const startEditCurrent = () => {
    const target = currentAgentDetail ?? (currentAgentId === null ? null : agentList.find((agent) => agent.id === currentAgentId) ?? null)
    if (target === null) {
      notify.warning('请先选择一个智能体')
      return
    }
    setConfigMode('edit')
    setEditingAgentId(target.id)
    const nextForm = formFromAgent(target)
    setForm(nextForm)
    setSubmitError(null)
    setShowApiKey(false)
    openTab({ type: 'agent_config', params: { mode: 'edit', agentId: target.id }, status: 'ready', message: '正在编辑智能体' })
  }

  const runConnectionValidation = () => {
    const endpointErr = validateEndpoint(form.llm_provider_url)
    if (endpointErr) return setSubmitError(endpointErr)
    if (form.llm_model_name.trim().length === 0) return setSubmitError('模型名称为必填项')
    if (configMode === 'create' && form.llm_api_key.trim().length === 0) return setSubmitError('接口密钥为必填项')
    setSubmitError(null)
    notify.info('连接参数本地校验通过，保存后在真实执行链路中验证连接')
  }

  const handleSubmit = async () => {
    if (!canSubmit) return
    setIsSubmitting(true)
    setSubmitError(null)
    const embedding = form.embedding_provider === 'bge_local'
      ? { provider: 'bge_local', model: form.embedding_model.trim() || 'BAAI/bge-large-zh-v1.5' }
      : {
          provider: 'openai_compatible',
          base_url: form.embedding_base_url.trim(),
          model: form.embedding_model.trim(),
          ...(form.embedding_api_key.trim().length > 0 ? { api_key: form.embedding_api_key.trim() } : {}),
        }
    try {
      if (configMode === 'create') {
        await createAgent({
          name: form.name.trim(),
          description: form.description.trim(),
          opening_statement: form.opening_statement.trim(),
          avatar_url: form.avatar_url.trim().length > 0 ? form.avatar_url.trim() : null,
          llm_provider_url: form.llm_provider_url.trim(),
          llm_api_key: form.llm_api_key.trim(),
          llm_model_name: form.llm_model_name.trim(),
          embedding,
          runtime_config: {
            temperature: Number(form.temperature || '0.7'),
            max_tokens: form.max_tokens.trim().length > 0 ? Number(form.max_tokens) : null,
          },
          capability_flags: { supports_tools: true },
          tools: DEFAULT_AGENT_TOOL_IDS,
          constraints: { max_steps: 6 },
        })
        clearAgentConfigDraft()
        const created = useAgentStore.getState().current_agent_detail
        if (created !== null) {
          setConfigMode('edit')
          setEditingAgentId(created.id)
          setForm(formFromAgent(created))
          openTab({ type: 'agent_config', params: { mode: 'edit', agentId: created.id }, status: 'ready', message: '已创建' })
        }
        notify.success('智能体已创建')
      } else {
        const targetId = editingAgentId
        if (targetId === null) {
          setSubmitError('当前无可编辑智能体')
          return
        }
        await updateAgent(targetId, {
          name: form.name.trim(),
          description: form.description.trim(),
          opening_statement: form.opening_statement.trim(),
          avatar_url: form.avatar_url.trim().length > 0 ? form.avatar_url.trim() : null,
          llm_provider_url: form.llm_provider_url.trim(),
          llm_model_name: form.llm_model_name.trim(),
          embedding,
          runtime_config: {
            temperature: Number(form.temperature || '0.7'),
            max_tokens: form.max_tokens.trim().length > 0 ? Number(form.max_tokens) : null,
          },
          ...(form.llm_api_key.trim().length > 0 ? { llm_api_key: form.llm_api_key.trim() } : {}),
        })
        notify.success('智能体配置已保存')
      }
      setTabStateByType('agent_config', { status: 'ready', message: '已保存' })
      setShowApiKey(false)
    } catch (error) {
      const code = parseArcErrorCode((error as { raw?: unknown })?.raw ?? null)
      setSubmitError(mapArcErrorCode(code))
      setTabStateByType('agent_config', { status: 'error', message: '保存失败' })
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="h-full min-w-0 overflow-auto rounded-token-lg border border-border/80 bg-surface shadow-token-sm">
      <div className="mx-auto max-w-7xl space-y-5 p-4 md:p-5 xl:space-y-6 xl:p-6">
        <div className="flex flex-wrap items-start justify-between gap-3 border-b border-border/80 pb-5">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="inline-flex h-10 w-10 items-center justify-center rounded-token-md bg-primary/10 text-primary ring-1 ring-primary/10">
                <Bot size={17} />
              </span>
              <div className="min-w-0">
                <h2 className="text-lg font-semibold tracking-tight text-text-main">智能体配置</h2>
                <p className="mt-1 text-sm text-text-sub">以人设逻辑为中心，配置模型连接和运行参数。</p>
              </div>
            </div>
          </div>
          <div className="flex min-w-0 flex-wrap items-center gap-2">
            <div className="inline-flex rounded-token-md border border-border bg-bg-soft p-1">
              <button
                type="button"
                className={`h-8 rounded-token-md px-3 text-xs font-medium ${
                  configMode === 'edit' ? 'bg-surface text-text-main shadow-token-sm' : 'text-text-sub hover:text-text-main'
                }`}
                onClick={startEditCurrent}
              >
                编辑当前
              </button>
              <button
                type="button"
                className={`h-8 rounded-token-md px-3 text-xs font-medium ${
                  configMode === 'create' ? 'bg-surface text-text-main shadow-token-sm' : 'text-text-sub hover:text-text-main'
                }`}
                onClick={startCreate}
              >
                新建
              </button>
            </div>
            <Badge variant={configMode === 'edit' ? 'info' : 'neutral'}>{configMode === 'edit' ? '编辑' : '新建'}</Badge>
          </div>
        </div>

        {configMode === 'edit' && editingAgent !== null ? (
          <div className="grid gap-3 md:grid-cols-3">
          <div className="rounded-token-lg border border-border/80 bg-bg-soft/50 p-4">
              <p className="text-xs font-medium text-text-muted">当前智能体</p>
              <p className="mt-2 truncate text-sm font-semibold text-text-main">{editingAgent.name}</p>
            </div>
          <div className="rounded-token-lg border border-border/80 bg-bg-soft/50 p-4">
              <p className="text-xs font-medium text-text-muted">模型</p>
              <p className="mt-2 truncate text-sm font-semibold text-text-main">{editingAgent.llm_model_name || '未配置'}</p>
            </div>
          <div className="rounded-token-lg border border-border/80 bg-bg-soft/50 p-4">
              <p className="text-xs font-medium text-text-muted">可用状态</p>
              <div className="mt-2">
                <Badge variant={editingAgent.is_available ? 'success' : 'error'}>
                  {editingAgent.is_available ? '可用' : editingAgent.availability_reason ?? '不可用'}
                </Badge>
              </div>
            </div>
          </div>
        ) : null}

        <div className="grid min-w-0 gap-5 2xl:grid-cols-[minmax(0,1fr)_minmax(290px,350px)]">
          <section className="min-w-0 space-y-5 rounded-token-lg border border-border/80 bg-surface p-4 shadow-token-sm md:p-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="flex min-w-0 items-center gap-2">
                <span className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-token-md bg-primary/10 text-primary">
                  <ScrollText size={16} />
                </span>
                <div className="min-w-0">
                <h3 className="text-base font-semibold tracking-tight text-text-main">人设与逻辑</h3>
                  <p className="mt-1 text-xs leading-relaxed text-text-sub">这部分会作为 system prompt 注入每轮对话，是智能体行为的核心。</p>
                </div>
              </div>
              <Badge variant="info">System Prompt</Badge>
            </div>

            <div className="space-y-3 rounded-token-md border border-border/70 bg-bg-soft/35 p-4">
              <h4 className="text-sm font-semibold text-text-main">基本信息</h4>
              <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_minmax(220px,0.42fr)]">
                <div>
                <Input id="agent-name" label="智能体名称" placeholder="输入智能体名称" value={form.name} onChange={(e) => setFormField('name', e.target.value)} />
                {fieldErrors.name && <p className="mt-1 text-xs text-red-500">{fieldErrors.name}</p>}
                </div>
                <Input id="agent-avatar" label="头像地址" placeholder="https://example.com/avatar.png" value={form.avatar_url} onChange={(e) => setFormField('avatar_url', e.target.value)} />
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <label htmlFor="agent-description" className="text-sm font-semibold text-text-main">核心提示词</label>
                <span className="text-xs text-text-muted">System Prompt</span>
              </div>
              <textarea
                id="agent-description"
                className="min-h-[320px] w-full resize-y rounded-token-md border border-border bg-bg-soft/30 px-4 py-3 text-sm leading-relaxed text-text-main placeholder:text-text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
                placeholder="写下智能体的人设、目标、边界、判断逻辑、回复风格和禁止事项。这里保存后会作为 system prompt 参与每轮对话。"
                value={form.description}
                onChange={(e) => setFormField('description', e.target.value)}
              />
              <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-text-muted">
                <span>执行时注入模型，不只是展示说明。</span>
                <span>{form.description.trim().length} 字符</span>
              </div>
              {fieldErrors.description && <p className="text-xs text-red-500">{fieldErrors.description}</p>}
            </div>

            <div className="space-y-2 rounded-token-md border border-border/80 bg-bg-soft/35 p-4">
              <div className="flex items-center gap-2">
                <MessageSquareText size={15} className="text-text-muted" />
                <label htmlFor="agent-opening-statement" className="text-sm font-semibold text-text-main">默认开场白</label>
              </div>
              <textarea
                id="agent-opening-statement"
                className="min-h-[92px] w-full resize-y rounded-token-md border border-border bg-bg-soft px-3 py-2 text-sm leading-relaxed text-text-sub placeholder:text-text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
                placeholder="这句话会在对话预览中以灰色气泡自动展示。"
                value={form.opening_statement}
                onChange={(e) => setFormField('opening_statement', e.target.value)}
              />
              <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-text-muted">
                <span>创建智能体时自动带入；保存后会刷新到对话预览。</span>
                <span>{form.opening_statement.trim().length} 字符</span>
              </div>
              {fieldErrors.opening_statement && <p className="text-xs text-red-500">{fieldErrors.opening_statement}</p>}
            </div>
          </section>

          <aside className="min-w-0 space-y-4">
            <section className="space-y-3 rounded-token-lg border border-border/80 bg-surface p-4 shadow-token-sm">
              <div className="flex items-center gap-2 text-sm font-semibold text-text-main">
                <Wrench size={15} className="text-text-muted" />
                模型连接
              </div>
              <Input id="provider-url" label="基础地址" placeholder="https://api.openai.com/v1" value={form.llm_provider_url} onChange={(e) => setFormField('llm_provider_url', e.target.value)} />
              <p className="text-xs text-text-muted">必须为 OpenAI 兼容接口地址，禁止本机或内网地址。</p>
              {fieldErrors.llm_provider_url && <p className="text-xs text-red-500">{fieldErrors.llm_provider_url}</p>}
              <div className="space-y-1">
                <label htmlFor="api-key" className="text-xs font-medium text-text-sub">接口密钥</label>
                <div className="flex items-start gap-2">
                  <div className="min-w-0 flex-1">
                    <Input
                      id="api-key"
                      type={showApiKey ? 'text' : 'password'}
                      placeholder={configMode === 'edit' && editingAgent?.has_api_key ? '已保存，留空表示不变更' : '输入接口密钥'}
                      value={form.llm_api_key}
                      onChange={(e) => setFormField('llm_api_key', e.target.value)}
                    />
                  </div>
                  <Button type="button" variant="ghost" size="icon" aria-label="切换接口密钥可见性" title="切换接口密钥可见性" onClick={() => setShowApiKey((prev) => !prev)}>
                    {showApiKey ? <EyeOff size={14} /> : <Eye size={14} />}
                  </Button>
                </div>
                <p className="text-xs text-text-muted">密钥会写入后端配置；本机草稿会保留当前输入，重启后可继续编辑。</p>
                {fieldErrors.llm_api_key && <p className="text-xs text-red-500">{fieldErrors.llm_api_key}</p>}
              </div>
              <Input id="model-name" label="模型名称" placeholder="gpt-4o-mini" value={form.llm_model_name} onChange={(e) => setFormField('llm_model_name', e.target.value)} />
              {fieldErrors.llm_model_name && <p className="text-xs text-red-500">{fieldErrors.llm_model_name}</p>}
            </section>

            <section className="space-y-3 rounded-token-lg border border-border/80 bg-surface p-4 shadow-token-sm">
              <div className="flex items-center gap-2 text-sm font-semibold text-text-main">
                <Bot size={15} className="text-text-muted" />
                向量模型（Embedding）
              </div>
              <div className="space-y-1">
                <label htmlFor="embedding-provider" className="text-xs font-medium text-text-sub">向量模型提供商</label>
                <select
                  id="embedding-provider"
                  className="h-10 w-full rounded-token-md border border-border bg-surface px-3 text-sm text-text-main focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
                  value={form.embedding_provider}
                  onChange={(e) => setEmbeddingProvider(e.target.value)}
                >
                  <option value="openai_compatible">OpenAI-compatible</option>
                  <option value="bge_local">本地 BGE</option>
                </select>
              </div>
              {form.embedding_provider === 'openai_compatible' ? (
                <>
                  <Input
                    id="embedding-base-url"
                    label="向量接口地址"
                    placeholder="https://api.openai.com/v1"
                    value={form.embedding_base_url}
                    onChange={(e) => setFormField('embedding_base_url', e.target.value)}
                  />
                  <Input
                    id="embedding-api-key"
                    type="password"
                    label="向量接口密钥"
                    placeholder={configMode === 'edit' && editingAgent?.embedding?.has_api_key ? '已保存，留空表示不变更' : '输入 Embedding API Key'}
                    value={form.embedding_api_key}
                    onChange={(e) => setFormField('embedding_api_key', e.target.value)}
                  />
                </>
              ) : null}
              <Input
                id="embedding-model"
                label="向量模型名称"
                placeholder="text-embedding-3-small"
                value={form.embedding_model}
                onChange={(e) => setFormField('embedding_model', e.target.value)}
              />
              <p className="text-xs leading-relaxed text-text-muted">用于将知识库文档和用户查询转换为向量，以支持知识检索。接口密钥会由后端加密保存。</p>
            </section>

            <section className="space-y-3 rounded-token-lg border border-border/80 bg-surface p-4 shadow-token-sm">
              <div className="flex items-center gap-2 text-sm font-semibold text-text-main">
                <CircleAlert size={15} className="text-text-muted" />
                运行参数
              </div>
              <Input id="temperature" label="温度" placeholder="0.7" value={form.temperature} onChange={(e) => setFormField('temperature', e.target.value)} />
              <Input id="max-tokens" label="最大令牌数" placeholder="1000" value={form.max_tokens} onChange={(e) => setFormField('max_tokens', e.target.value)} />
            </section>

            <section className="space-y-3 rounded-token-lg border border-border/80 bg-surface p-4 shadow-token-sm">
              <div className="flex items-center gap-2 text-sm font-semibold text-text-main">
                <CheckCircle2 size={15} className="text-text-muted" />
                保存
              </div>
              {submitError ? (
                <p className="rounded-token-md border border-red-300 bg-red-50 px-3 py-2 text-xs text-red-600">{submitError}</p>
              ) : (
                <p className="text-xs leading-relaxed text-text-muted">
                  保存后当前智能体与左侧列表会立即刷新。模型配置会保留在后端与本机草稿中，重启后继续使用。
                </p>
              )}
              <div className="flex flex-col gap-2">
                <Button type="button" variant="secondary" onClick={runConnectionValidation} disabled={isSubmitting}>
                  测试连接
                </Button>
                <Button type="button" variant="primary" leftIcon={configMode === 'create' ? <Plus size={14} /> : <Save size={14} />} onClick={() => void handleSubmit()} disabled={!canSubmit}>
                  {isSubmitting ? '正在保存...' : configMode === 'create' ? '创建智能体' : '保存智能体'}
                </Button>
              </div>
            </section>

            <PublicationPanel agent={configMode === 'edit' ? editingAgent : null} />
          </aside>
        </div>
      </div>
    </div>
  )
}
