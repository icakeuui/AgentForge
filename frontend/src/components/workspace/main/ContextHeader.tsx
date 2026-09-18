import { LayoutTemplate, Play } from 'lucide-react'

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
    <div className="z-10 flex shrink-0 flex-wrap items-center justify-between gap-4 border-b border-border bg-bg px-4 py-4 md:px-6">
      <div className="flex min-w-0 items-center gap-3">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-token-md bg-primary/10 text-primary">
          <LayoutTemplate size={16} />
        </div>
        <div className="min-w-0">
          <h1 className="truncate text-xl font-semibold text-text-main">{title || '云端构建器'}</h1>
          <p className="mt-1 max-w-2xl truncate text-sm text-text-muted">{subtitle}</p>
        </div>
      </div>
      <div className="flex min-w-0 flex-wrap items-center gap-2">
        <Button
          variant="primary"
          size="sm"
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
