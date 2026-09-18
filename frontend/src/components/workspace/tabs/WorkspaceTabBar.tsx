import { Bot, BugPlay, FileText, GitBranch, Globe, LayoutDashboard, Plug, TerminalSquare } from 'lucide-react'
import type { ComponentType } from 'react'

import { useExecutionStore } from '../../../features/execution/execution.store'
import { MAIN_TAB_LABELS, type MainTabId } from '../../../features/ui-shell/workspaceTabs.types'
import { useWorkspaceTabsStore } from '../../../features/ui-shell/workspaceTabs.store'
import { cn } from '../../../lib/cn'

const TAB_ORDER: MainTabId[] = ['documents', 'terminal', 'browser', 'code-changes', 'agent', 'mcp', 'canvas', 'react-flow']

const iconMap: Record<MainTabId, ComponentType<{ size?: number; className?: string }>> = {
  documents: FileText,
  terminal: TerminalSquare,
  browser: Globe,
  'code-changes': GitBranch,
  agent: Bot,
  mcp: Plug,
  canvas: LayoutDashboard,
  'react-flow': BugPlay,
}

export function WorkspaceTabBar() {
  const activeMainTab = useWorkspaceTabsStore((state) => state.activeMainTab)
  const setActiveMainTab = useWorkspaceTabsStore((state) => state.setActiveMainTab)
  const status = useExecutionStore((state) => state.status)
  const isExecuting = status === 'PENDING' || status === 'RUNNING'

  return (
    <div className="shrink-0 border-b border-border bg-surface px-4">
      <div className="flex h-11 items-center gap-1 overflow-x-auto">
        {TAB_ORDER.map((tab) => {
          const Icon = iconMap[tab]
          const isActive = activeMainTab === tab
          return (
            <button
              key={tab}
              type="button"
              onClick={() => setActiveMainTab(tab)}
              className={cn(
                'inline-flex h-8 min-w-fit items-center gap-1.5 rounded-token-md px-3 text-xs font-medium transition-colors',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30',
                isActive
                  ? 'bg-primary text-white shadow-token-sm'
                  : 'text-text-sub hover:bg-bg-soft hover:text-text-main',
              )}
            >
              <Icon size={14} />
              <span>{MAIN_TAB_LABELS[tab]}</span>
              {tab === 'react-flow' && isExecuting ? (
                <span
                  className={cn(
                    'ml-1 h-1.5 w-1.5 rounded-full',
                    isActive ? 'bg-white' : 'bg-primary',
                  )}
                />
              ) : null}
            </button>
          )
        })}
      </div>
    </div>
  )
}
