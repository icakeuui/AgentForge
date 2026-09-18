import type { ReactNode } from 'react'

import { useExecutionStore } from '../../../features/execution/execution.store'
import { useUiShellStore } from '../../../features/ui-shell/uiShell.store'
import { useWorkspaceTabsStore } from '../../../features/ui-shell/workspaceTabs.store'
import { cn } from '../../../lib/cn'
import { ReActDebugPanel } from '../debug/ReActDebugPanel'
import { AgentOutputPanel } from '../output/AgentOutputPanel'
import { StatusStrip } from '../status/StatusStrip'

function EmptyState() {
  return (
    <div className="flex h-full w-full items-center justify-center rounded-token-lg border border-dashed border-border bg-surface text-sm text-text-muted">
      暂无执行
    </div>
  )
}

function TerminationNotice() {
  return (
    <div className="rounded-token-lg border border-warning bg-warning-soft p-3 text-sm text-warning">
      执行已中断
    </div>
  )
}

export function ReActFlowTab() {
  const { current_execution_id, status, final_answer, error_message, react_steps, termination_reason } = useExecutionStore()
  const focusedStepIndex = useWorkspaceTabsStore((state) => state.reactFlow.focusedStepIndex)
  const maximizedPanel = useUiShellStore((state) => state.maximizedPanel)
  const setMaximizedPanel = useUiShellStore((state) => state.setMaximizedPanel)

  const toggleMaximizeDebug = () => {
    setMaximizedPanel(maximizedPanel === 'debug' ? null : 'debug')
  }

  const toggleMaximizeOutput = () => {
    setMaximizedPanel(maximizedPanel === 'output' ? null : 'output')
  }

  let content: ReactNode
  if (current_execution_id === null) {
    content = <EmptyState />
  } else if (status === 'PENDING') {
    content = <StatusStrip status="PENDING" />
  } else if (status === 'RUNNING') {
    content = (
      <div className="flex h-full w-full flex-col gap-4 overflow-hidden">
        <StatusStrip status="RUNNING" />
        <ReActDebugPanel
          react_steps={react_steps}
          status={status}
          final_answer={final_answer}
          termination_reason={termination_reason}
          error_message={error_message}
          focusedStepIndex={focusedStepIndex}
        />
      </div>
    )
  } else if (status === 'SUCCEEDED') {
    content = (
      <div className="flex h-full w-full gap-4 overflow-hidden">
        <div
          className={cn(
            'flex flex-col overflow-hidden transition-all duration-300',
            maximizedPanel === 'debug' ? 'w-full' : maximizedPanel === 'output' ? 'w-0 opacity-0 invisible' : 'w-1/2',
          )}
        >
          <ReActDebugPanel
            react_steps={react_steps}
            status={status}
            final_answer={final_answer}
            termination_reason={termination_reason}
            error_message={error_message}
            isMaximized={maximizedPanel === 'debug'}
            onMaximize={toggleMaximizeDebug}
            focusedStepIndex={focusedStepIndex}
          />
        </div>
        <div
          className={cn(
            'flex flex-col overflow-hidden transition-all duration-300',
            maximizedPanel === 'output' ? 'w-full' : maximizedPanel === 'debug' ? 'w-0 opacity-0 invisible' : 'w-1/2',
          )}
        >
          <AgentOutputPanel
            final_answer={final_answer}
            isMaximized={maximizedPanel === 'output'}
            onMaximize={toggleMaximizeOutput}
          />
        </div>
      </div>
    )
  } else if (status === 'FAILED') {
    content = (
      <div className="flex h-full w-full gap-4 overflow-hidden">
        <div className={cn('flex flex-col overflow-hidden', react_steps.length === 0 ? 'w-1/3' : 'w-1/2')}>
          <ReActDebugPanel
            react_steps={react_steps}
            status={status}
            final_answer={final_answer}
            termination_reason={termination_reason}
            error_message={error_message}
            focusedStepIndex={focusedStepIndex}
          />
        </div>
        <div className={cn('flex flex-col overflow-hidden', react_steps.length === 0 ? 'w-2/3' : 'w-1/2')}>
          <AgentOutputPanel final_answer={final_answer ?? error_message} />
        </div>
      </div>
    )
  } else {
    content = (
      <div className="flex h-full w-full flex-col gap-4 overflow-hidden">
        <TerminationNotice />
        {final_answer !== null && final_answer.trim().length > 0 ? <AgentOutputPanel final_answer={final_answer} /> : null}
      </div>
    )
  }

  return <div className="flex h-full gap-4 overflow-hidden">{content}</div>
}
