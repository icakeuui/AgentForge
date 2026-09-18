import { AlertTriangle, Archive, Clock, FolderKanban, MessageSquare, MoreHorizontal, Pencil, Pin, Plus, Trash2 } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

import { AGENT_CONFIG_DRAFT_EVENT, ensureCreateAgentConfigDraft, readAgentConfigDraft } from '../../../features/agent/agentConfigDraft'
import { useAgentStore } from '../../../features/agent/agent.store'
import { notify } from '../../../features/notifications/notify'
import { useBuilderTabsStore } from '../../../features/ui-shell/builderTabs.store'
import { useUiShellStore } from '../../../features/ui-shell/uiShell.store'
import { cn } from '../../../lib/cn'
import { Button } from '../../ui/Button'
import { Input } from '../../ui/Input'
import { SessionList } from '../history/SessionList'
import { SessionListItem } from '../history/SessionListItem'
import { UserSummary } from './UserSummary'

const PINNED_AGENT_IDS_STORAGE_KEY = 'AGENTFORGE_PINNED_AGENT_IDS'

function readPinnedAgentIds(): string[] {
  if (typeof window === 'undefined') {
    return []
  }
  const raw = window.localStorage.getItem(PINNED_AGENT_IDS_STORAGE_KEY)
  if (raw === null) {
    return []
  }
  try {
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed.filter((item): item is string => typeof item === 'string') : []
  } catch {
    return []
  }
}

function writePinnedAgentIds(agentIds: string[]): void {
  if (typeof window === 'undefined') {
    return
  }
  window.localStorage.setItem(PINNED_AGENT_IDS_STORAGE_KEY, JSON.stringify(agentIds))
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

export function WorkspaceRail() {
  const navigate = useNavigate()
  const location = useLocation()
  const leftPanelWidth = useUiShellStore((state) => state.leftPanelWidth)
  const openBuilderTab = useBuilderTabsStore((state) => state.openTab)
  const agentList = useAgentStore((state) => state.agent_list)
  const currentAgentId = useAgentStore((state) => state.current_agent_id)
  const currentAgentDetail = useAgentStore((state) => state.current_agent_detail)
  const isAgentListLoading = useAgentStore((state) => state.is_agent_list_loading)
  const updateAgent = useAgentStore((state) => state.updateAgent)
  const deleteAgent = useAgentStore((state) => state.deleteAgent)
  const selectAgent = useAgentStore((state) => state.selectAgent)
  const resetCurrentAgent = useAgentStore((state) => state.resetCurrentAgent)

  const [menuOpenAgentId, setMenuOpenAgentId] = useState<string | null>(null)
  const [damagedAgentId, setDamagedAgentId] = useState<string | null>(null)
  const [isDeletingDamagedAgent, setIsDeletingDamagedAgent] = useState(false)
  const [pinnedAgentIds, setPinnedAgentIds] = useState<string[]>(() => readPinnedAgentIds())
  const [agentSearch, setAgentSearch] = useState('')
  const [hasCreateDraft, setHasCreateDraft] = useState(() => readAgentConfigDraft() !== null)
  const [createDraftName, setCreateDraftName] = useState(() => readAgentConfigDraft()?.name.trim() ?? '')
  const damagedAgent = useMemo(
    () => (damagedAgentId === null ? null : agentList.find((agent) => agent.id === damagedAgentId) ?? null),
    [agentList, damagedAgentId],
  )

  const goToAgentsWorkspace = () => {
    if (location.pathname !== '/develop/agents') {
      navigate('/develop/agents')
    }
  }

  const orderedAgents = useMemo(() => {
    const pinnedSet = new Set(pinnedAgentIds)
    const withIndex = agentList.map((agent, index) => ({ agent, index }))
    return withIndex
      .slice()
      .sort((left, right) => {
        const leftPinned = pinnedSet.has(left.agent.id)
        const rightPinned = pinnedSet.has(right.agent.id)
        if (leftPinned !== rightPinned) return leftPinned ? -1 : 1
        const leftRank = left.agent.archived ? 3 : left.agent.is_available ? 1 : 2
        const rightRank = right.agent.archived ? 3 : right.agent.is_available ? 1 : 2
        if (leftRank !== rightRank) return leftRank - rightRank
        return left.index - right.index
      })
      .map((item) => item.agent)
  }, [agentList, pinnedAgentIds])
  const recentAgents = useMemo(() => orderedAgents.filter((agent) => !agent.archived), [orderedAgents])
  const archivedAgents = useMemo(() => orderedAgents.filter((agent) => agent.archived), [orderedAgents])
  const normalizedAgentSearch = agentSearch.trim().toLowerCase()
  const visibleRecentAgents = useMemo(
    () =>
      recentAgents.filter((agent) => {
        if (!normalizedAgentSearch) return true
        return [agent.name, agent.llm_model_name, agent.description, agent.availability_reason]
          .filter((value): value is string => typeof value === 'string')
          .some((value) => value.toLowerCase().includes(normalizedAgentSearch))
      }),
    [normalizedAgentSearch, recentAgents],
  )
  const visibleArchivedAgents = useMemo(
    () =>
      archivedAgents.filter((agent) => {
        if (!normalizedAgentSearch) return true
        return [agent.name, agent.llm_model_name, agent.description, agent.availability_reason]
          .filter((value): value is string => typeof value === 'string')
          .some((value) => value.toLowerCase().includes(normalizedAgentSearch))
      }),
    [archivedAgents, normalizedAgentSearch],
  )

  useEffect(() => {
    if (menuOpenAgentId === null || typeof window === 'undefined') {
      return
    }
    const closeMenu = () => setMenuOpenAgentId(null)
    window.addEventListener('click', closeMenu)
    return () => window.removeEventListener('click', closeMenu)
  }, [menuOpenAgentId])

  useEffect(() => {
    if (typeof window === 'undefined') {
      return
    }

    const syncDraftState = () => {
      const draft = readAgentConfigDraft()
      setHasCreateDraft(draft !== null)
      setCreateDraftName(draft?.name.trim() ?? '')
    }

    syncDraftState()
    window.addEventListener(AGENT_CONFIG_DRAFT_EVENT, syncDraftState)
    window.addEventListener('storage', syncDraftState)
    return () => {
      window.removeEventListener(AGENT_CONFIG_DRAFT_EVENT, syncDraftState)
      window.removeEventListener('storage', syncDraftState)
    }
  }, [])

  const openAgentConfigTab = (mode: 'create' | 'edit', agentId?: string) => {
    if (mode === 'create') {
      const draft = ensureCreateAgentConfigDraft()
      setHasCreateDraft(true)
      setCreateDraftName(draft.name.trim())
    }
    openBuilderTab({
      type: 'agent_config',
      params: mode === 'edit' ? { mode, agentId: agentId ?? currentAgentId } : { mode },
      status: mode === 'edit' ? 'ready' : 'idle',
      message: mode === 'edit' ? '正在编辑智能体' : '准备创建智能体',
    })
  }

  const selectAgentForEditing = (agentId: string) => {
    void selectAgent(agentId)
    openAgentConfigTab('edit', agentId)
    goToAgentsWorkspace()
  }

  const togglePinned = (agentId: string) => {
    const next = pinnedAgentIds.includes(agentId)
      ? pinnedAgentIds.filter((id) => id !== agentId)
      : [...pinnedAgentIds, agentId]
    setPinnedAgentIds(next)
    writePinnedAgentIds(next)
    setMenuOpenAgentId(null)
  }

  const archiveAgent = async (agentId: string) => {
    try {
      await updateAgent(agentId, { archived: true })
      if (currentAgentId === agentId) {
        resetCurrentAgent()
      }
      setPinnedAgentIds((prev) => {
        const next = prev.filter((id) => id !== agentId)
        writePinnedAgentIds(next)
        return next
      })
      setMenuOpenAgentId(null)
    } catch (error) {
      const apiError = mapArcErrorCode(parseArcErrorCode((error as { raw?: unknown })?.raw ?? null))
      notify.error(apiError)
    }
  }

  const unarchiveAgent = async (agentId: string) => {
    try {
      await updateAgent(agentId, { archived: false })
      setMenuOpenAgentId(null)
    } catch (error) {
      const apiError = mapArcErrorCode(parseArcErrorCode((error as { raw?: unknown })?.raw ?? null))
      notify.error(apiError)
    }
  }

  const removeAgent = async (agentId: string) => {
    const confirmed = typeof window !== 'undefined' ? window.confirm('确认删除该智能体？此操作不可恢复。') : false
    if (!confirmed) {
      return
    }
    try {
      await deleteAgent(agentId)
      setPinnedAgentIds((prev) => {
        const next = prev.filter((id) => id !== agentId)
        writePinnedAgentIds(next)
        return next
      })
      setMenuOpenAgentId(null)
    } catch (error) {
      const apiError = mapArcErrorCode(parseArcErrorCode((error as { raw?: unknown })?.raw ?? null))
      notify.error(apiError)
    }
  }

  const requestDeleteDamagedAgent = (agentId: string) => {
    setMenuOpenAgentId(null)
    setDamagedAgentId(agentId)
  }

  const removeDamagedAgent = async () => {
    if (damagedAgentId === null) {
      return
    }
    setIsDeletingDamagedAgent(true)
    try {
      await deleteAgent(damagedAgentId)
      setPinnedAgentIds((prev) => {
        const next = prev.filter((id) => id !== damagedAgentId)
        writePinnedAgentIds(next)
        return next
      })
      setDamagedAgentId(null)
    } catch (error) {
      const apiError = mapArcErrorCode(parseArcErrorCode((error as { raw?: unknown })?.raw ?? null))
      notify.error(apiError)
    } finally {
      setIsDeletingDamagedAgent(false)
    }
  }

  return (
    <aside
      style={{ width: leftPanelWidth }}
      className="flex h-full shrink-0 flex-col border-r border-border bg-surface transition-all duration-300"
    >
      <div className="shrink-0 border-b border-border px-4 py-4">
        <div className="mb-3 flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h2 className="truncate text-base font-semibold text-text-main">智能体仓库</h2>
            <p className="mt-0.5 truncate text-xs text-text-muted">智能体历史管理</p>
          </div>
          <Button
            type="button"
            variant="secondary"
            size="icon"
            aria-label="新建智能体"
            title="新建智能体"
            onClick={() => {
              openAgentConfigTab('create')
              goToAgentsWorkspace()
            }}
          >
            <Plus size={16} />
          </Button>
        </div>
        <Input
          id="agent-search"
          placeholder="搜索智能体"
          value={agentSearch}
          onChange={(event) => setAgentSearch(event.target.value)}
        />
      </div>

      <div className="flex-1 overflow-y-auto overflow-x-hidden py-4">
        <div className="space-y-5">
            <SessionList title="当前智能体">
              <SessionListItem
                id="current-agent"
                title={currentAgentDetail?.name ?? '未选择智能体'}
                subtitle={
                  currentAgentDetail === null
                    ? '请选择或新建可用智能体'
                    : currentAgentDetail.is_available
                      ? currentAgentDetail.llm_model_name
                      : `不可用：${currentAgentDetail.availability_reason ?? '配置异常'}`
                }
                icon={<FolderKanban size={16} />}
                active={currentAgentId !== null}
              />
            </SessionList>

            <SessionList title="最近智能体">
              {hasCreateDraft && (
                <SessionListItem
                  id="draft-agent"
                  title={createDraftName.length > 0 ? createDraftName : '未保存的新智能体'}
                  subtitle="继续填写配置后保存"
                  icon={<Plus size={16} />}
                  onClick={() => {
                    openAgentConfigTab('create')
                    goToAgentsWorkspace()
                  }}
                />
              )}
              {isAgentListLoading && <SessionListItem id="loading-agents" title="正在加载智能体..." icon={<Clock size={16} />} />}
              {!isAgentListLoading && visibleRecentAgents.map((agent) => {
                const isPinned = pinnedAgentIds.includes(agent.id)
                return (
                  <div
                    key={agent.id}
                    className={cn(
                      'group relative flex items-start gap-2 rounded-token-md px-3 py-2 transition-colors',
                      agent.id === currentAgentId ? 'bg-bg-soft ring-1 ring-border' : 'hover:bg-bg-soft',
                    )}
                  >
                    <button
                      type="button"
                      className="flex min-w-0 flex-1 items-start gap-3 text-left"
                      onClick={() => {
                        if (!agent.is_available) {
                          requestDeleteDamagedAgent(agent.id)
                          return
                        }
                        selectAgentForEditing(agent.id)
                      }}
                    >
                      <div className="mt-0.5 shrink-0 text-text-muted"><MessageSquare size={16} /></div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="truncate text-sm font-medium text-text-main">{agent.name}</span>
                          {isPinned && <span className="rounded bg-primary/10 px-1.5 py-0.5 text-[10px] text-primary">置顶</span>}
                          {!agent.is_available && (
                            <span className="inline-flex items-center gap-1 rounded bg-red-100 px-1.5 py-0.5 text-[10px] text-red-700">
                              <AlertTriangle size={10} />
                              不可用
                            </span>
                          )}
                        </div>
                        <p className="truncate text-xs text-text-muted">
                          {agent.is_available ? agent.llm_model_name : agent.availability_reason ?? '历史配置异常'}
                        </p>
                      </div>
                    </button>

                    <div className="relative">
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7"
                        aria-label={`manage-${agent.id}`}
                        onClick={(event) => {
                          event.stopPropagation()
                          if (!agent.is_available) {
                            requestDeleteDamagedAgent(agent.id)
                            return
                          }
                          setMenuOpenAgentId((prev) => (prev === agent.id ? null : agent.id))
                        }}
                      >
                        <MoreHorizontal size={14} />
                      </Button>
                      {menuOpenAgentId === agent.id && (
                        <div className="absolute right-0 top-8 z-20 w-40 rounded-token-md border border-border bg-surface p-1 shadow-token-lg" onClick={(event) => event.stopPropagation()}>
                          <button type="button" className="flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-xs text-text-main hover:bg-bg-soft" onClick={() => { openAgentConfigTab('edit', agent.id); setMenuOpenAgentId(null) }}>
                            <Pencil size={12} />
                            编辑配置
                          </button>
                          <button type="button" className="flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-xs text-text-main hover:bg-bg-soft" onClick={() => togglePinned(agent.id)}>
                            <Pin size={12} />
                            {isPinned ? '取消置顶' : '置顶'}
                          </button>
                          <button type="button" className="flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-xs text-text-main hover:bg-bg-soft" onClick={() => { void archiveAgent(agent.id) }}>
                            <Archive size={12} />
                            归档
                          </button>
                          <button type="button" className="flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-xs text-red-600 hover:bg-red-50" onClick={() => { void removeAgent(agent.id) }}>
                            <Trash2 size={12} />
                            删除
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                )
              })}
              {!isAgentListLoading && visibleRecentAgents.length === 0 && (
                <SessionListItem
                  id="empty-agent-list"
                  title={normalizedAgentSearch ? '没有匹配的智能体' : '暂无可用智能体'}
                  subtitle={normalizedAgentSearch ? '换个关键词再试试' : '新建或恢复一个智能体后继续'}
                />
              )}
            </SessionList>

            <SessionList title="已归档">
              {visibleArchivedAgents.length === 0 && (
                <SessionListItem
                  id="empty-archived-list"
                  title={normalizedAgentSearch ? '没有匹配的归档智能体' : '暂无归档智能体'}
                  subtitle={normalizedAgentSearch ? '归档列表中没有该关键词' : '归档项会显示在这里'}
                />
              )}
              {visibleArchivedAgents.map((agent) => (
                <div key={agent.id} className="flex items-start gap-2 rounded-token-md px-3 py-2">
                  <div className="mt-0.5 shrink-0 text-text-muted"><Archive size={16} /></div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-text-main">{agent.name}</p>
                    <p className="truncate text-xs text-text-muted">{agent.availability_reason ?? '已归档'}</p>
                  </div>
                  <Button type="button" variant="ghost" size="sm" onClick={() => { void unarchiveAgent(agent.id) }}>
                    恢复
                  </Button>
                </div>
              ))}
            </SessionList>
          </div>
      </div>

      <UserSummary />

      {damagedAgent !== null && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center bg-slate-950/35 px-4">
          <div
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="damaged-agent-title"
            aria-describedby="damaged-agent-description"
            className="w-full max-w-sm rounded-token-lg border border-red-200 bg-surface p-5 shadow-token-xl"
          >
            <div className="mb-4 flex items-start gap-3">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-token-md bg-red-50 text-red-600">
                <AlertTriangle size={18} />
              </div>
              <div className="min-w-0">
                <h3 id="damaged-agent-title" className="text-sm font-semibold text-text-main">
                  智能体不可用
                </h3>
                <p id="damaged-agent-description" className="mt-1 text-sm leading-relaxed text-text-sub">
                  该智能体已损坏或不可用，要删除它吗
                </p>
                <p className="mt-2 truncate text-xs text-text-muted">{damagedAgent.name}</p>
              </div>
            </div>
            <Button
              type="button"
              className="w-full bg-red-600 hover:bg-red-700"
              disabled={isDeletingDamagedAgent}
              onClick={() => {
                void removeDamagedAgent()
              }}
            >
              {isDeletingDamagedAgent ? '正在删除...' : '是，删除'}
            </Button>
          </div>
        </div>
      )}

    </aside>
  )
}
