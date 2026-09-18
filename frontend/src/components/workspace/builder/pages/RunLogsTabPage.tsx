import { Activity, AlertCircle, AlertTriangle, Brain, CheckCircle2, Database, ExternalLink, Filter, ShieldCheck, Wrench } from 'lucide-react'
import { useEffect, useMemo } from 'react'

import { useExecutionStore } from '../../../../features/execution/execution.store'
import type { ExecutionStatus, ExecutionStepLog, PreviewPhase } from '../../../../features/execution/execution.types'
import { getBuiltinToolLabel } from '../../../../features/tools/tools.catalog'
import { useBuilderTabsStore } from '../../../../features/ui-shell/builderTabs.store'
import { Badge } from '../../../ui/Badge'
import { Button } from '../../../ui/Button'
import { SkillCallBox } from '../../chat/SkillCallBox'
import { ThoughtCollapsibleBlock } from '../../copilot/timeline/ThoughtCollapsibleBlock'
import { mapExecutionToTimeline } from '../../copilot/timeline/mapExecutionToTimeline'
import type { TimelineItem } from '../../copilot/timeline/timeline.types'
import { ReActDebugPanel } from '../../debug/ReActDebugPanel'
import { AgentOutputPanel } from '../../output/AgentOutputPanel'
import { RichContentRenderer } from '../../rich-content/RichContentRenderer'

const STATUS_LABEL: Record<ExecutionStatus, string> = {
  IDLE: '空闲',
  PENDING: '初始化中',
  RUNNING: '执行中',
  SUCCEEDED: '执行完成',
  FAILED: '执行失败',
  TERMINATED: '执行中断',
}

const PHASE_LABEL: Record<PreviewPhase, string> = {
  empty: '未开始',
  planning: '规划中',
  building: '构建中',
  booting: '沙箱启动中',
  ready: '可用',
  failed: '异常',
  deployed: '已部署',
}

function readFocusedStep(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

function stringifyValue(value: unknown): string {
  if (typeof value === 'string') {
    return value
  }
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return String(value)
  }
}

function readString(value: unknown): string | null {
  return typeof value === 'string' && value.trim().length > 0 ? value.trim() : null
}

function readNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

function readRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === 'object' && value !== null && !Array.isArray(value) ? (value as Record<string, unknown>) : null
}

function compactString(value: unknown, maxLength = 180): string | null {
  const text = stringifyValue(value).trim()
  if (text.length === 0) {
    return null
  }
  return text.length > maxLength ? `${text.slice(0, maxLength)}...` : text
}

function knowledgeHitInfo(log: ExecutionStepLog): { hit: boolean; count: number } {
  if (log.phase !== 'knowledge_retrieval' || log.status === 'error') {
    return { hit: false, count: 0 }
  }
  const hits = Array.isArray(log.payload.knowledge_hits) ? log.payload.knowledge_hits : []
  const matchedCount = readNumber(log.payload.matched_count) ?? hits.length
  const hit = log.payload.matched === true || matchedCount > 0 || readString(log.payload.context) !== null
  return { hit, count: matchedCount }
}

function phaseLabel(phase: ExecutionStepLog['phase']): string {
  if (phase === 'intent_classification') return '意图分类'
  if (phase === 'pre_policy_gate') return '前置策略'
  if (phase === 'knowledge_retrieval') return '知识库调用'
  if (phase === 'retrieval_policy_gate') return '检索策略'
  if (phase === 'model_call') return '模型调用'
  if (phase === 'tool_policy_gate') return '工具策略'
  if (phase === 'tool_call') return '工具使用'
  if (phase === 'observation') return '工具结果'
  if (phase === 'final_answer_policy_gate') return '答复策略'
  return '最终答复'
}

function phaseIcon(phase: ExecutionStepLog['phase']) {
  if (phase === 'intent_classification') return <Filter size={14} className="text-text-muted" />
  if (phase === 'pre_policy_gate' || phase === 'retrieval_policy_gate' || phase === 'tool_policy_gate' || phase === 'final_answer_policy_gate') {
    return <ShieldCheck size={14} className="text-text-muted" />
  }
  if (phase === 'knowledge_retrieval') return <Database size={14} className="text-text-muted" />
  if (phase === 'model_call') return <Brain size={14} className="text-text-muted" />
  if (phase === 'tool_call') return <Wrench size={14} className="text-text-muted" />
  return <Activity size={14} className="text-text-muted" />
}

function summarizeStepLog(log: ExecutionStepLog): string {
  if (log.phase === 'intent_classification') {
    const intent = readString(log.payload.intent_type) ?? '未知意图'
    const subtype = readString(log.payload.query_subtype)
    const confidence = readNumber(log.payload.confidence)
    const suffix = confidence !== null ? `，置信度 ${confidence.toFixed(2)}` : ''
    return subtype ? `识别为 ${intent} / ${subtype}${suffix}` : `识别为 ${intent}${suffix}`
  }
  if (log.phase === 'pre_policy_gate') {
    const retrievalMode = readString(log.payload.retrieval_mode) ?? 'none'
    const allowed = Array.isArray(log.payload.allowed_tool_ids_for_turn) ? log.payload.allowed_tool_ids_for_turn.length : 0
    const blocked = Array.isArray(log.payload.blocked_tool_ids) ? log.payload.blocked_tool_ids.length : 0
    const confirmation = log.payload.requires_user_confirmation === true ? '，需要确认' : ''
    return `检索模式 ${retrievalMode}，允许工具 ${allowed} 个，拦截工具 ${blocked} 个${confirmation}`
  }
  if (log.phase === 'knowledge_retrieval') {
    if (log.status === 'error') return '知识库检索异常'
    const { hit, count } = knowledgeHitInfo(log)
    const query = readString(log.payload.query)
    const queryText = query ? `：${query}` : ''
    if (!hit) return `已调用知识库${queryText}，未命中相关资料`
    return count > 0 ? `已调用知识库${queryText}，命中 ${count} 条知识片段` : `已调用知识库${queryText}，命中相关知识片段`
  }
  if (log.phase === 'model_call') {
    const finishReason = typeof log.payload.finish_reason === 'string' ? log.payload.finish_reason : 'unknown'
    const toolCalls = Array.isArray(log.payload.tool_calls) ? log.payload.tool_calls.length : 0
    return toolCalls > 0 ? `模型请求使用 ${toolCalls} 个工具，结束原因：${finishReason}` : `模型完成本轮思考，结束原因：${finishReason}`
  }
  if (log.phase === 'retrieval_policy_gate') {
    if (log.payload.must_return_without_model === true) {
      const code = readString(readRecord(log.payload.knowledge_miss)?.reason_code) ?? readString(log.payload.reason_code)
      return code ? `检索策略阻断模型调用：${code}` : '检索策略阻断模型调用'
    }
    return log.payload.retrieval_optional_miss === true ? '检索未命中，但允许继续模型回答' : '检索策略允许继续'
  }
  if (log.phase === 'tool_policy_gate') {
    const decision = readString(log.payload.decision) ?? (log.status === 'error' ? 'blocked' : 'allowed')
    const code = readString(log.payload.reason_code)
    const message = readString(log.payload.reason_message)
    if (decision === 'blocked') {
      return `工具策略已拦截${code ? `：${code}` : ''}${message ? ` · ${message}` : ''}`
    }
    return '工具策略允许调用'
  }
  if (log.phase === 'tool_call') {
    const toolId = readString(log.payload.resolved_tool_id) ?? readString(log.tool_id) ?? readString(log.payload.provider_tool_name) ?? '未知工具'
    return `模型正在使用工具：${getBuiltinToolLabel(toolId)}`
  }
  if (log.phase === 'observation') {
    const toolId = readString(log.tool_id) ?? readString(log.payload.tool_id) ?? '未知工具'
    return log.status === 'error' ? `${getBuiltinToolLabel(toolId)} 执行失败` : `${getBuiltinToolLabel(toolId)} 已返回结果`
  }
  if (log.phase === 'final_answer_policy_gate') {
    const accepted = log.payload.accepted === true
    const code = readString(log.payload.violation_code)
    return accepted ? '最终答复通过策略检查' : `最终答复被策略修正${code ? `：${code}` : ''}`
  }
  const finalAnswer = typeof log.payload.final_answer === 'string' ? log.payload.final_answer.trim() : ''
  return finalAnswer.length > 0 ? `生成最终答复（${Math.min(finalAnswer.length, 120)} 字符）` : '生成最终答复'
}

function renderKnowledgeHits(log: ExecutionStepLog) {
  if (log.phase !== 'knowledge_retrieval') {
    return null
  }
  const knowledgeHits = Array.isArray(log.payload.knowledge_hits) ? log.payload.knowledge_hits : []
  if (knowledgeHits.length === 0) {
    const { hit } = knowledgeHitInfo(log)
    return (
      <p className="text-xs text-text-muted">
        {hit ? '本轮命中了知识上下文，但没有返回可展示的片段摘要。' : '本轮已检索知识库，没有命中相关资料。'}
      </p>
    )
  }
  return (
    <div className="space-y-2">
      {knowledgeHits.map((item, index) => {
        const record = typeof item === 'object' && item !== null ? (item as Record<string, unknown>) : {}
        const title = typeof record.title === 'string' ? record.title : `片段 ${index + 1}`
        const score = typeof record.score === 'number' ? record.score : null
        const preview = typeof record.content_preview === 'string' ? record.content_preview : ''
        return (
          <div key={`${title}:${index}`} className="rounded-token-sm border border-border bg-bg-soft/40 p-2">
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs font-medium text-text-main">{title}</span>
              {score !== null ? <span className="text-[11px] text-text-muted">分数 {score}</span> : null}
            </div>
            <p className="mt-1 whitespace-pre-wrap text-[11px] leading-relaxed text-text-sub">{preview || '无摘要'}</p>
          </div>
        )
      })}
    </div>
  )
}

function renderIntentClassificationPayload(log: ExecutionStepLog) {
  const rules = Array.isArray(log.payload.matched_rules) ? log.payload.matched_rules : []
  const domains = Array.isArray(log.payload.candidate_tool_domains) ? log.payload.candidate_tool_domains : []
  const knowledgeDomains = Array.isArray(log.payload.required_knowledge_domains) ? log.payload.required_knowledge_domains : []
  return (
    <div className="grid gap-2 text-xs text-text-sub sm:grid-cols-2">
      <div className="rounded-token-sm border border-border bg-surface px-2 py-1">
        <span className="text-text-muted">意图：</span>
        {readString(log.payload.intent_type) ?? '未知'}
      </div>
      <div className="rounded-token-sm border border-border bg-surface px-2 py-1">
        <span className="text-text-muted">子类型：</span>
        {readString(log.payload.query_subtype) ?? '未知'}
      </div>
      <div className="rounded-token-sm border border-border bg-surface px-2 py-1">
        <span className="text-text-muted">需要引用：</span>
        {log.payload.requires_citation === true ? '是' : '否'}
      </div>
      <div className="rounded-token-sm border border-border bg-surface px-2 py-1">
        <span className="text-text-muted">允许直答：</span>
        {log.payload.allow_direct_answer === true ? '是' : '否'}
      </div>
      <div className="rounded-token-sm border border-border bg-surface px-2 py-1 sm:col-span-2">
        <span className="text-text-muted">命中规则：</span>
        {rules.length > 0 ? rules.join('、') : '无'}
      </div>
      {(domains.length > 0 || knowledgeDomains.length > 0) ? (
        <div className="rounded-token-sm border border-border bg-surface px-2 py-1 sm:col-span-2">
          <span className="text-text-muted">域：</span>
          {[...knowledgeDomains, ...domains].join('、')}
        </div>
      ) : null}
    </div>
  )
}

function renderPrePolicyPayload(log: ExecutionStepLog) {
  const allowed = Array.isArray(log.payload.allowed_tool_ids_for_turn) ? log.payload.allowed_tool_ids_for_turn : []
  const blocked = Array.isArray(log.payload.blocked_tool_ids) ? log.payload.blocked_tool_ids : []
  return (
    <div className="space-y-2">
      <div className="grid gap-2 text-xs text-text-sub sm:grid-cols-2">
        <div className="rounded-token-sm border border-border bg-surface px-2 py-1">
          <span className="text-text-muted">检索模式：</span>
          {readString(log.payload.retrieval_mode) ?? 'none'}
        </div>
        <div className="rounded-token-sm border border-border bg-surface px-2 py-1">
          <span className="text-text-muted">必须检索：</span>
          {log.payload.retrieval_required === true ? '是' : '否'}
        </div>
        <div className="rounded-token-sm border border-border bg-surface px-2 py-1">
          <span className="text-text-muted">要求引用：</span>
          {log.payload.requires_citation === true ? '是' : '否'}
        </div>
        <div className="rounded-token-sm border border-border bg-surface px-2 py-1">
          <span className="text-text-muted">需要确认：</span>
          {log.payload.requires_user_confirmation === true ? '是' : '否'}
        </div>
      </div>
      <div className="rounded-token-sm border border-border bg-bg-soft p-2 text-[11px] text-text-sub">
        允许工具：{allowed.length > 0 ? allowed.map((item) => getBuiltinToolLabel(String(item))).join('、') : '无'}
      </div>
      {blocked.length > 0 ? (
        <pre className="overflow-auto whitespace-pre-wrap rounded-token-sm border border-border bg-bg-soft p-2 text-[11px] text-text-sub">
          {stringifyValue(blocked)}
        </pre>
      ) : null}
    </div>
  )
}

function renderGatePayload(log: ExecutionStepLog) {
  const safeFallback = readString(log.payload.safe_fallback)
  const code = readString(log.payload.reason_code) ?? readString(log.payload.violation_code)
  const message = readString(log.payload.reason_message)
  return (
    <div className="space-y-2">
      <div className="grid gap-2 text-xs text-text-sub sm:grid-cols-2">
        <div className="rounded-token-sm border border-border bg-surface px-2 py-1">
          <span className="text-text-muted">决策：</span>
          {readString(log.payload.decision) ?? (log.payload.accepted === true ? 'accepted' : log.status === 'error' ? 'blocked' : 'allowed')}
        </div>
        <div className="rounded-token-sm border border-border bg-surface px-2 py-1">
          <span className="text-text-muted">代码：</span>
          {code ?? '无'}
        </div>
      </div>
      {message ? <p className="text-xs text-text-sub">{message}</p> : null}
      {safeFallback ? (
        <pre className="overflow-auto whitespace-pre-wrap rounded-token-sm border border-border bg-bg-soft p-2 text-[11px] text-text-sub">
          {safeFallback}
        </pre>
      ) : null}
    </div>
  )
}

function renderToolCallPayload(log: ExecutionStepLog) {
  const toolId = readString(log.payload.resolved_tool_id) ?? readString(log.tool_id) ?? readString(log.payload.provider_tool_name) ?? '未知工具'
  const providerToolName = readString(log.payload.provider_tool_name)
  const argumentsPayload = log.payload.arguments
  return (
    <div className="space-y-2">
      <div className="grid gap-2 text-xs text-text-sub sm:grid-cols-2">
        <div className="rounded-token-sm border border-border bg-surface px-2 py-1">
          <span className="text-text-muted">工具：</span>
          {getBuiltinToolLabel(toolId)}
        </div>
        {providerToolName ? (
          <div className="rounded-token-sm border border-border bg-surface px-2 py-1">
            <span className="text-text-muted">模型请求名：</span>
            {providerToolName}
          </div>
        ) : null}
      </div>
      <pre className="overflow-auto whitespace-pre-wrap rounded-token-sm border border-border bg-bg-soft p-2 text-[11px] text-text-sub">
        {stringifyValue(argumentsPayload ?? {})}
      </pre>
    </div>
  )
}

function renderObservationPayload(log: ExecutionStepLog) {
  const payload = readRecord(log.payload)
  const content = payload?.content ?? payload?.result ?? null
  const error = payload?.error ?? payload?.message ?? null
  if (log.status === 'error') {
    return (
      <pre className="overflow-auto whitespace-pre-wrap rounded-token-sm border border-error bg-error-soft p-2 text-[11px] text-error">
        {stringifyValue(error ?? log.payload)}
      </pre>
    )
  }

  const preview = compactString(content ?? log.payload, 800) ?? '工具没有返回可展示内容。'
  return (
    <pre className="overflow-auto whitespace-pre-wrap rounded-token-sm border border-border bg-bg-soft p-2 text-[11px] text-text-sub">
      {preview}
    </pre>
  )
}

function renderStepLogPayload(log: ExecutionStepLog) {
  if (log.phase === 'intent_classification') {
    return renderIntentClassificationPayload(log)
  }
  if (log.phase === 'pre_policy_gate') {
    return renderPrePolicyPayload(log)
  }
  if (log.phase === 'retrieval_policy_gate' || log.phase === 'tool_policy_gate' || log.phase === 'final_answer_policy_gate') {
    return renderGatePayload(log)
  }
  if (log.phase === 'knowledge_retrieval') {
    return renderKnowledgeHits(log)
  }
  if (log.phase === 'model_call') {
    const contentPreview = typeof log.payload.content_preview === 'string' ? log.payload.content_preview : ''
    const toolCalls = Array.isArray(log.payload.tool_calls) ? log.payload.tool_calls : []
    return (
      <div className="space-y-2">
        <div className="text-xs text-text-sub">
          模型：{typeof log.payload.model === 'string' ? log.payload.model : '未知'}
          {' · '}
          强制工具：{typeof log.payload.forced_tool_name === 'string' && log.payload.forced_tool_name ? log.payload.forced_tool_name : '无'}
        </div>
        {toolCalls.length > 0 ? (
          <pre className="overflow-auto whitespace-pre-wrap rounded-token-sm border border-border bg-bg-soft p-2 text-[11px] text-text-sub">
            {stringifyValue(toolCalls)}
          </pre>
        ) : null}
        {contentPreview ? (
          <pre className="overflow-auto whitespace-pre-wrap rounded-token-sm border border-border bg-bg-soft p-2 text-[11px] text-text-sub">
            {contentPreview}
          </pre>
        ) : null}
      </div>
    )
  }
  if (log.phase === 'tool_call') {
    return renderToolCallPayload(log)
  }
  if (log.phase === 'observation') {
    return renderObservationPayload(log)
  }
  return (
    <pre className="overflow-auto whitespace-pre-wrap rounded-token-sm border border-border bg-bg-soft p-2 text-[11px] text-text-sub">
      {stringifyValue(log.payload)}
    </pre>
  )
}

function phaseFromStatus(status: ExecutionStatus, phase: PreviewPhase | null): PreviewPhase {
  if (phase !== null) {
    return phase
  }
  if (status === 'IDLE') return 'empty'
  if (status === 'PENDING') return 'planning'
  if (status === 'RUNNING') return 'building'
  if (status === 'SUCCEEDED') return 'ready'
  return 'failed'
}

function renderTimelineItem(item: TimelineItem, currentExecutionId: string | null, focusStep: (stepIndex?: number | null) => void) {
  if (item.type === 'status') {
    return (
      <div className="rounded-token-md border border-border bg-bg-soft/40 p-3">
        <div className="flex items-center justify-between gap-2">
          <span className="text-xs font-semibold text-text-main">执行状态</span>
          <Badge variant={item.status === 'FAILED' ? 'error' : item.status === 'SUCCEEDED' ? 'success' : 'info'}>
            {STATUS_LABEL[item.status]}
          </Badge>
        </div>
      </div>
    )
  }

  if (item.type === 'thought') {
    return (
      <ThoughtCollapsibleBlock
        thought={item.thought}
        stepIndex={item.stepIndex}
        defaultExpanded={item.defaultExpanded}
      />
    )
  }

  if (item.type === 'action') {
    return (
      <SkillCallBox
        toolId={item.toolId}
        argsSummary={item.argsSummary}
        status={item.status}
        detailsLabel="定位原始日志"
        onViewDetails={() => focusStep(item.stepIndex)}
      />
    )
  }

  if (item.type === 'observation') {
    return (
      <div className="space-y-2 rounded-token-md border border-border bg-surface p-3">
        <div className="flex items-center justify-between gap-2">
          <span className="text-xs font-semibold text-text-main">观察结果 · 第 {item.stepIndex} 步</span>
          <div className="flex items-center gap-1 text-[11px]">
            {item.ok ? <CheckCircle2 size={12} className="text-success" /> : <AlertCircle size={12} className="text-error" />}
            <span className={item.ok ? 'text-success' : 'text-error'}>{item.ok ? '成功' : '失败'}</span>
          </div>
        </div>
        <p className="text-xs leading-relaxed text-text-sub">{item.summary}</p>
        {item.links.length > 0 ? (
          <div className="space-y-1 text-xs">
            {item.links.slice(0, 3).map((link) => (
              <button
                key={link.id}
                type="button"
                className="block max-w-full truncate text-left text-primary underline-offset-2 hover:underline"
                onClick={() => window.open(link.url, '_blank', 'noopener,noreferrer')}
              >
                {link.title}
              </button>
            ))}
          </div>
        ) : null}
        {item.files.length > 0 ? (
          <div className="space-y-2">
            <div className="text-[11px] font-semibold uppercase tracking-normal text-text-muted">文件产物</div>
            {item.files.map((file) => (
              <div key={file.id} className="rounded-token-sm border border-border bg-bg-soft/40 px-2 py-1 text-xs text-text-sub">
                {file.title}
              </div>
            ))}
          </div>
        ) : null}
        <div className="flex justify-end">
          <Button size="sm" variant="ghost" className="h-6 px-2 text-[11px]" onClick={() => focusStep(item.stepIndex)}>
            定位原始日志
          </Button>
        </div>
      </div>
    )
  }

  if (item.type === 'artifact') {
    return (
      <div className="space-y-2 rounded-token-md border border-border bg-surface p-3">
        <div className="flex items-center justify-between gap-2">
          <span className="text-xs font-semibold text-text-main">文件变更产物</span>
          <span className="text-[11px] text-text-muted">
            {item.files.length} 项（原始 {item.rawCount}）
          </span>
        </div>
        {item.files.map((file) => (
          <div key={file.id} className="rounded-token-sm border border-border bg-bg-soft/40 px-2 py-1 text-xs text-text-sub">
            {file.title}
          </div>
        ))}
      </div>
    )
  }

  if (item.type === 'final_answer') {
    return (
      <div className="space-y-2 rounded-token-md border border-border bg-surface p-3">
        <div className="flex items-center justify-between gap-2">
          <span className="text-xs font-semibold text-text-main">最终答复</span>
          {currentExecutionId ? <span className="text-[11px] text-text-muted">来自当前运行</span> : null}
        </div>
        <RichContentRenderer content={item.content} />
      </div>
    )
  }

  return (
    <div className="rounded-token-md border border-error bg-error-soft p-3">
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-semibold text-error">{item.title}</span>
        {item.code ? <Badge variant="error">{item.code}</Badge> : null}
      </div>
      <p className="mt-1 whitespace-pre-wrap text-xs leading-relaxed text-error">{item.message}</p>
      {item.source ? <p className="mt-1 text-[11px] text-error/90">来源：{item.source}</p> : null}
      <div className="mt-2 flex justify-end">
        <Button size="sm" variant="ghost" className="h-6 px-2 text-[11px] text-error hover:text-error" onClick={() => focusStep(item.stepIndex ?? null)}>
          定位原始日志
        </Button>
      </div>
    </div>
  )
}

export function RunLogsTabPage() {
  const {
    current_execution_id,
    status,
    react_steps,
    step_logs,
    final_answer,
    termination_reason,
    error_message,
    error_code,
    error_source,
    artifacts,
    preview_phase,
    preview_url,
    last_user_input,
  } = useExecutionStore()
  const tabs = useBuilderTabsStore((state) => state.tabs)
  const activeTabId = useBuilderTabsStore((state) => state.activeTabId)
  const setTabStateByType = useBuilderTabsStore((state) => state.setTabStateByType)
  const openRunLogsTab = useBuilderTabsStore((state) => state.openRunLogsTab)
  const activeTab = useMemo(() => tabs.find((tab) => tab.id === activeTabId) ?? null, [activeTabId, tabs])
  const focusedStepIndex = readFocusedStep(activeTab?.params?.stepIndex)

  const timeline = useMemo(
    () =>
      mapExecutionToTimeline({
        currentExecutionId: current_execution_id,
        status,
        reactSteps: react_steps,
        finalAnswer: final_answer,
        errorCode: error_code,
        errorSource: error_source,
        errorMessage: error_message,
        terminationReason: termination_reason,
        artifacts,
      }),
    [artifacts, current_execution_id, error_code, error_message, error_source, final_answer, react_steps, status, termination_reason],
  )

  const toolCallCount = step_logs.filter((log) => log.phase === 'tool_call').length
  const successfulToolCallCount = step_logs.filter((log) => log.phase === 'observation' && log.status === 'success').length
  const knowledgeHitCount = useMemo(
    () =>
      step_logs
        .filter((log) => log.phase === 'knowledge_retrieval')
        .reduce((sum, log) => sum + knowledgeHitInfo(log).count, 0),
    [step_logs],
  )
  const knowledgeRetrievalCount = step_logs.filter((log) => log.phase === 'knowledge_retrieval').length
  const intentLog = step_logs.find((log) => log.phase === 'intent_classification')
  const prePolicyLog = step_logs.find((log) => log.phase === 'pre_policy_gate')
  const policyBlockCount = step_logs.filter(
    (log) =>
      (log.phase === 'retrieval_policy_gate' || log.phase === 'tool_policy_gate' || log.phase === 'final_answer_policy_gate') &&
      log.status === 'error',
  ).length
  const allowedToolCount = Array.isArray(prePolicyLog?.payload.allowed_tool_ids_for_turn)
    ? prePolicyLog.payload.allowed_tool_ids_for_turn.length
    : 0
  const blockedToolCount = Array.isArray(prePolicyLog?.payload.blocked_tool_ids) ? prePolicyLog.payload.blocked_tool_ids.length : 0
  const currentPhase = phaseFromStatus(status, preview_phase)
  const progressLabel =
    status === 'RUNNING' || status === 'PENDING'
      ? `执行中 · 已完成 ${react_steps.length} 步`
      : status === 'SUCCEEDED'
        ? `执行完成 · 共 ${react_steps.length} 步`
        : status === 'FAILED' || status === 'TERMINATED'
          ? `执行异常 · 已记录 ${react_steps.length} 步`
          : '等待执行'

  useEffect(() => {
    if (status === 'FAILED' || status === 'TERMINATED') {
      setTabStateByType('run_logs', { status: 'error', message: '运行失败，请查看详情' })
      return
    }
    if (status === 'PENDING' || status === 'RUNNING') {
      setTabStateByType('run_logs', { status: 'loading', message: '运行中' })
      return
    }
    if (current_execution_id === null) {
      setTabStateByType('run_logs', { status: 'idle', message: '暂无运行记录' })
      return
    }
    setTabStateByType('run_logs', { status: 'ready', message: '运行日志就绪' })
  }, [current_execution_id, setTabStateByType, status])

  if (current_execution_id === null) {
    return (
      <div className="flex h-full flex-col items-center justify-center rounded-token-lg border border-dashed border-border bg-surface text-center">
        <Activity size={28} className="text-text-muted" />
        <p className="mt-2 text-sm font-medium text-text-main">暂无运行日志</p>
        <p className="mt-1 text-xs text-text-muted">发起一次对话后，这里会显示知识库调用、工具使用、模型思考和错误信息。</p>
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col gap-3 overflow-hidden">
      <div className="rounded-token-md border border-border bg-surface px-4 py-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-xs text-text-muted">运行编号</p>
            <p className="truncate text-sm font-semibold text-text-main">{current_execution_id}</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant={status === 'FAILED' ? 'error' : status === 'SUCCEEDED' ? 'success' : 'info'}>
              {STATUS_LABEL[status]}
            </Badge>
            {preview_url ? (
              <Button
                size="sm"
                variant="ghost"
                leftIcon={<ExternalLink size={14} />}
                onClick={() => window.open(preview_url, '_blank', 'noopener,noreferrer')}
              >
                打开沙箱页面
              </Button>
            ) : null}
          </div>
        </div>
        {(status === 'FAILED' || status === 'TERMINATED') && (error_message || termination_reason) ? (
          <div className="mt-2 inline-flex items-center gap-1 text-xs text-error">
            <AlertTriangle size={13} />
            {error_message ?? termination_reason}
          </div>
        ) : null}
      </div>

      <div className="grid min-h-0 flex-1 gap-3 xl:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
        <div className="min-h-0 overflow-hidden rounded-token-md border border-border bg-surface">
          <div className="border-b border-border px-4 py-3">
            <div className="flex items-center justify-between gap-2">
              <div>
                <p className="text-sm font-semibold text-text-main">运行时间线</p>
                <p className="mt-1 text-xs text-text-muted">工具调用、观察结果与错误详情</p>
              </div>
              <Badge variant="neutral">{progressLabel}</Badge>
            </div>
          </div>
          <div className="h-full space-y-3 overflow-auto p-4 pb-20">
            <div className="rounded-token-md border border-border bg-bg-soft/40 p-3 text-xs">
              <div className="mb-2 flex items-center justify-between gap-2">
                <span className="font-semibold text-text-main">云端构建概览</span>
                <Badge variant={status === 'FAILED' ? 'error' : status === 'SUCCEEDED' ? 'success' : 'info'}>
                  {STATUS_LABEL[status]}
                </Badge>
              </div>
              <div className="space-y-1 text-text-sub">
                <p>用户需求：{last_user_input ?? '暂无输入'}</p>
                <p>构建阶段：{PHASE_LABEL[currentPhase]}</p>
                <p>意图分类：{readString(intentLog?.payload.intent_type) ?? '未记录'}</p>
                <p>检索模式：{readString(prePolicyLog?.payload.retrieval_mode) ?? '未记录'}</p>
                <p>允许工具：{allowedToolCount} 个</p>
                <p>策略拦截：{policyBlockCount} 次</p>
                <p>被拦工具：{blockedToolCount} 个</p>
                <p>任务进度：{progressLabel}</p>
                <p>工具使用：{toolCallCount} 次</p>
                <p>工具成功返回：{successfulToolCallCount} 次</p>
                <p>知识库调用：{knowledgeRetrievalCount} 次</p>
                <p>知识命中：{knowledgeHitCount} 条</p>
                <p>沙箱状态：{currentPhase === 'ready' || currentPhase === 'deployed' ? '可用' : currentPhase === 'failed' ? '异常' : '处理中'}</p>
                <p>预览地址：{preview_url ?? '尚未生成'}</p>
              </div>
            </div>

            <div className="space-y-2 rounded-token-md border border-border bg-surface p-3">
              <div className="flex items-center justify-between gap-2">
                <div>
                  <p className="text-sm font-semibold text-text-main">阶段明细</p>
                  <p className="mt-1 text-xs text-text-muted">按顺序展示模型思考、知识库调用和工具使用的真实日志</p>
                </div>
                <Badge variant="neutral">{step_logs.length} 条</Badge>
              </div>
              {step_logs.length === 0 ? (
                <p className="text-xs text-text-muted">当前运行尚未产生阶段日志。</p>
              ) : (
                <div className="space-y-2">
                  {step_logs.map((log, index) => (
                    <div key={`${log.phase}:${log.step_index}:${log.timestamp}:${index}`} className="rounded-token-sm border border-border bg-bg-soft/40 p-3">
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          {phaseIcon(log.phase)}
                          <span className="text-xs font-semibold text-text-main">
                            {phaseLabel(log.phase)} · 第 {log.step_index} 步
                          </span>
                        </div>
                        <Badge
                          variant={
                            log.status === 'error'
                              ? 'error'
                              : log.phase === 'knowledge_retrieval' && !knowledgeHitInfo(log).hit
                                ? 'neutral'
                                : 'success'
                          }
                        >
                          {log.status === 'error'
                            ? '异常'
                            : log.phase === 'knowledge_retrieval' && !knowledgeHitInfo(log).hit
                              ? '未命中'
                              : '成功'}
                        </Badge>
                      </div>
                      <p className="mt-2 text-xs text-text-sub">{summarizeStepLog(log)}</p>
                      {log.tool_id ? <p className="mt-1 text-[11px] text-text-muted">工具：{getBuiltinToolLabel(log.tool_id)}</p> : null}
                      <div className="mt-2">{renderStepLogPayload(log)}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {timeline.map((item) => (
              <div key={item.type === 'thought' ? `${item.id}:${status}` : item.id}>
                {renderTimelineItem(item, current_execution_id, (stepIndex) => openRunLogsTab({ stepIndex, executionId: current_execution_id }))}
              </div>
            ))}
          </div>
        </div>

        <div className="grid min-h-0 gap-3 lg:grid-rows-2">
          <div className="min-h-0 overflow-hidden">
            <ReActDebugPanel
              react_steps={react_steps}
              status={status}
              final_answer={final_answer}
              termination_reason={termination_reason}
              error_message={error_message}
              focusedStepIndex={focusedStepIndex}
            />
          </div>
          <div className="min-h-0 overflow-hidden">
            <AgentOutputPanel final_answer={final_answer} />
          </div>
        </div>
      </div>
    </div>
  )
}
