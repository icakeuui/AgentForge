import { Bot, Wrench } from 'lucide-react'

import { useAgentStore } from '../../../features/agent/agent.store'
import { useExecutionStore } from '../../../features/execution/execution.store'
import { Badge } from '../../ui/Badge'

const AGENT_CONTEXT_LABEL: Record<string, string> = {
  EMPTY: '未加载',
  LIST_LOADING: '加载列表',
  DETAIL_LOADING: '加载详情',
  READY: '已就绪',
  ERROR: '异常',
}

const EXECUTION_STATUS_LABEL: Record<string, string> = {
  IDLE: '空闲',
  PENDING: '准备中',
  RUNNING: '执行中',
  SUCCEEDED: '已完成',
  FAILED: '失败',
  TERMINATED: '已中断',
}

export function AgentTab() {
  const currentAgentId = useAgentStore((state) => state.current_agent_id)
  const currentAgentDetail = useAgentStore((state) => state.current_agent_detail)
  const agentContextStatus = useAgentStore((state) => state.agent_context_status)
  const executionStatus = useExecutionStore((state) => state.status)
  const isLocked = executionStatus === 'PENDING' || executionStatus === 'RUNNING'

  if (currentAgentDetail === null) {
    return (
      <div className="flex h-full flex-col items-center justify-center rounded-token-lg border border-dashed border-border bg-surface p-6 text-center">
        <Bot size={34} className="mb-3 text-border" />
        <p className="text-sm font-medium text-text-main">未选择智能体</p>
        <p className="mt-1 max-w-md text-xs leading-relaxed text-text-muted">
          选择或创建智能体后，这里会聚合状态、模型、工具绑定入口与运行锁定提示。
        </p>
      </div>
    )
  }

  return (
    <div className="h-full overflow-auto rounded-token-lg border border-border bg-surface p-4 shadow-token-sm">
      <div className="flex items-start justify-between gap-4 border-b border-border pb-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-token-md bg-primary/10 text-primary">
              <Bot size={17} />
            </div>
            <div className="min-w-0">
              <h2 className="truncate text-base font-semibold text-text-main">{currentAgentDetail.name}</h2>
              <p className="truncate text-xs text-text-muted">智能体编号：{currentAgentId}</p>
            </div>
          </div>
          {currentAgentDetail.description ? (
            <p className="mt-3 max-w-3xl text-sm leading-relaxed text-text-sub">{currentAgentDetail.description}</p>
          ) : null}
        </div>
      </div>

      <div className="grid gap-3 py-4 md:grid-cols-3">
        <div className="rounded-token-md border border-border bg-bg-soft/50 p-3">
          <div className="text-xs font-medium text-text-muted">上下文状态</div>
          <div className="mt-2">
            <Badge variant={agentContextStatus === 'READY' ? 'success' : agentContextStatus === 'ERROR' ? 'error' : 'neutral'}>
              {AGENT_CONTEXT_LABEL[agentContextStatus] ?? agentContextStatus}
            </Badge>
          </div>
        </div>
        <div className="rounded-token-md border border-border bg-bg-soft/50 p-3">
          <div className="text-xs font-medium text-text-muted">运行状态</div>
          <div className="mt-2">
            <Badge variant={isLocked ? 'warning' : 'neutral'}>{isLocked ? '执行锁定' : EXECUTION_STATUS_LABEL[executionStatus] ?? executionStatus}</Badge>
          </div>
        </div>
        <div className="rounded-token-md border border-border bg-bg-soft/50 p-3">
          <div className="text-xs font-medium text-text-muted">模型</div>
          <p className="mt-2 truncate text-sm font-semibold text-text-main">{currentAgentDetail.llm_model_name || '未配置'}</p>
        </div>
      </div>

      <div className="rounded-token-md border border-border bg-bg-soft/40 p-3">
        <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-text-main">
          <Wrench size={15} className="text-text-muted" />
          工具绑定
        </div>
        {currentAgentDetail.tools.length === 0 ? (
          <p className="text-xs text-text-muted">当前未绑定工具；可到 MCP 标签查看真实 marketplace catalog。</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {currentAgentDetail.tools.map((tool) => (
              <span key={tool} className="rounded-token-md bg-surface px-2 py-1 font-mono text-xs text-text-sub">
                {tool}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
