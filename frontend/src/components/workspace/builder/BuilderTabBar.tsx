import { useBuilderTabsStore } from '../../../features/ui-shell/builderTabs.store'
import { getCapabilityMeta } from '../../../features/ui-shell/builderTabs.registry'
import type { BuilderTabType } from '../../../features/ui-shell/builderTabs.types'
import { cn } from '../../../lib/cn'

const SIMPLE_BUILDER_TABS: BuilderTabType[] = ['agent_config', 'skills', 'knowledge', 'run_logs']

export function BuilderTabBar() {
  const tabs = useBuilderTabsStore((state) => state.tabs)
  const activeTabId = useBuilderTabsStore((state) => state.activeTabId)
  const openCapabilityTab = useBuilderTabsStore((state) => state.openCapabilityTab)
  const activeTab = tabs.find((tab) => tab.id === activeTabId) ?? tabs[0]

  return (
    <nav className="shrink-0 border-b border-border bg-bg px-4 md:px-6" aria-label="智能体构建步骤">
      <div className="flex h-12 items-end gap-6 overflow-x-auto">
        {SIMPLE_BUILDER_TABS.map((type) => {
          const meta = getCapabilityMeta(type)
          const isActive = activeTab?.type === type
          return (
            <button
              key={type}
              type="button"
              className={cn(
                'h-12 shrink-0 border-b-2 px-0.5 text-sm transition-colors',
                isActive
                  ? 'border-primary font-semibold text-primary'
                  : 'border-transparent text-text-sub hover:text-text-main',
              )}
              onClick={() => {
                openCapabilityTab(type)
              }}
            >
              {meta.title}
            </button>
          )
        })}
      </div>
    </nav>
  )
}
