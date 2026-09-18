import { TerminalSquare } from 'lucide-react'

import { useWorkspaceTabsStore } from '../../../features/ui-shell/workspaceTabs.store'
import { CodeBlockCard } from '../chat/CodeBlockCard'

export function TerminalTab() {
  const commandHistory = useWorkspaceTabsStore((state) => state.terminal.commandHistory)

  if (commandHistory.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center rounded-token-lg border border-dashed border-border bg-surface p-6 text-center">
        <TerminalSquare size={34} className="mb-3 text-border" />
        <p className="text-sm font-medium text-text-main">当前为命令记录模式（无 PTY）</p>
        <p className="mt-1 max-w-md text-xs leading-relaxed text-text-muted">
          这里仅承载从最终答复或节点中加入的命令块；没有实时 shell、stdout 流或执行状态。
        </p>
      </div>
    )
  }

  return (
    <div className="h-full overflow-auto rounded-token-lg border border-border bg-surface p-4 shadow-token-sm">
      <div className="mb-3 text-sm font-semibold text-text-main">命令记录</div>
      <div className="space-y-3">
        {commandHistory.map((item) => (
          <CodeBlockCard
            key={item.id}
            title={item.title ?? 'Command'}
            code={item.command}
            language="shell"
            kind="command"
          />
        ))}
      </div>
    </div>
  )
}
