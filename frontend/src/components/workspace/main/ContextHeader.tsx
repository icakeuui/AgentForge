import { Bot, CheckCircle2, CircleAlert, LayoutTemplate, Play } from 'lucide-react'

import { useAgentStore } from '../../../features/agent/agent.store'
import { RUN_AGENT_TRIGGER_EVENT } from '../../../features/execution/execution.events'
import { useExecutionStore } from '../../../features/execution/execution.store'
import { Button } from '../../ui/Button'

export function ContextHeader() {
  const currentAgentId = useAgentStore((state) => state.current_agent_id)
  const currentAgentDetail = useAgentStore((state) => state.current_agent_detail)
  const agentContextStatus = useAgentStore((state) => state.agent_context_status)
  const executionStatus = useExecutionStore((state) => state.status)
  const title = currentAgentDetail?.name ?? '未选择智能体'
  const subtitle =
    currentAgentId === null
      ? '请选择或新建一个智能体开始构建'
      : currentAgentDetail === null
        ? '当前智能体不可用'
        : currentAgentDetail.is_available
          ? currentAgentDetail.description || `模型：${currentAgentDetail.llm_model_name}`
          : `当前智能体不可用${currentAgentDetail.availability_reason ? `：${currentAgentDetail.availability_reason}` : ''}`
  const isExecutionLocked = executionStatus === 'PENDING' || executionStatus === 'RUNNING'
  const canRunAgent =
    currentAgentDetail !== null && currentAgentDetail.is_available && agentContextStatus === 'READY' && !isExecutionLocked

  return (
    <div className="z-10 mx-3 mt-3 flex shrink-0 flex-wrap items-center justify-between gap-4 rounded-token-lg border border-border/80 bg-surface px-4 py-3 shadow-token-sm md:mx-4 md:mt-4 md:px-5 xl:mx-5">
      <div className="flex min-w-0 items-center gap-3">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-token-md bg-primary/10 text-primary ring-1 ring-primary/10">
          {currentAgentDetail?.avatar_url ? (
            <img src={currentAgentDetail.avatar_url} alt="" className="h-full w-full rounded-token-md object-cover" />
          ) : currentAgentId !== null ? <Bot size={19} /> : <LayoutTemplate size={18} />}
        </div>
        <div className="min-w-0">
          <div className="flex min-w-0 flex-wrap items-center gap-2">
            <h1 className="truncate text-lg font-semibold tracking-tight text-text-main md:text-xl">{title || '云端构建器'}</h1>
            {currentAgentId !== null ? (
              <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium ${currentAgentDetail?.is_available ? 'bg-success-soft text-success' : 'bg-error-soft text-error'}`}>
                {currentAgentDetail?.is_available ? <CheckCircle2 size={12} /> : <CircleAlert size={12} />}
                {currentAgentDetail?.is_available ? '可用' : '待检查'}
              </span>
            ) : null}
          </div>
          <p className="mt-0.5 max-w-2xl truncate text-sm text-text-muted">{subtitle}</p>
        </div>
      </div>
      <div className="flex min-w-0 flex-wrap items-center gap-2">
        <Button
          variant="primary"
          size="md"
          leftIcon={<Play size={14} />}
          disabled={!canRunAgent}
          onClick={() => {
            if (typeof window === 'undefined') {
              return
            }
            window.dispatchEvent(new Event(RUN_AGENT_TRIGGER_EVENT))
          }}
        >
          运行智能体
        </Button>
      </div>
    </div>
  )
}
