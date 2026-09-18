import { ChevronDown, ChevronUp, Plus } from 'lucide-react'
import { useMemo, useState } from 'react'

import {
  BUILDER_TAB_REGISTRY,
  NEW_TAB_GROUP_LABELS,
  NEW_TAB_GROUP_ORDER,
} from '../../../../features/ui-shell/builderTabs.registry'
import { useBuilderTabsStore } from '../../../../features/ui-shell/builderTabs.store'
import type { BuilderCapabilityGroup, BuilderCapabilityMeta } from '../../../../features/ui-shell/builderTabs.types'
import { cn } from '../../../../lib/cn'
import { Button } from '../../../ui/Button'
import { getBuilderIcon } from '../builderTabIcons'

function groupCapabilities(group: BuilderCapabilityGroup): BuilderCapabilityMeta[] {
  return Object.values(BUILDER_TAB_REGISTRY).filter((item) => item.group === group && item.type !== 'new_tab')
}

export function NewTabSelectorPage() {
  const [devToolsCollapsed, setDevToolsCollapsed] = useState(true)
  const selectCapabilityInActiveTab = useBuilderTabsStore((state) => state.selectCapabilityInActiveTab)
  const grouped = useMemo(
    () =>
      NEW_TAB_GROUP_ORDER.map((group) => ({
        group,
        label: NEW_TAB_GROUP_LABELS[group],
        cards: groupCapabilities(group),
      })),
    [],
  )

  return (
    <div className="h-full overflow-auto rounded-token-lg border border-border bg-surface p-5">
      <div className="max-w-5xl space-y-5">
        <div>
          <h2 className="text-lg font-semibold text-text-main">新标签页</h2>
          <p className="mt-1 text-sm text-text-sub">选择要打开的云端页面能力。默认只保留预览页，其他能力按需打开。</p>
        </div>
        {grouped.map((section) => {
          const isDevTools = section.group === 'dev_tools'
          const collapsed = isDevTools && devToolsCollapsed
          return (
            <section key={section.group} className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-text-main">{section.label}</h3>
                {isDevTools ? (
                  <Button
                    variant="ghost"
                    size="sm"
                    leftIcon={devToolsCollapsed ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
                    onClick={() => setDevToolsCollapsed((prev) => !prev)}
                  >
                    {devToolsCollapsed ? '展开' : '折叠'}
                  </Button>
                ) : null}
              </div>
              {collapsed ? (
                <div className="rounded-token-md border border-dashed border-border bg-bg-soft/30 p-3 text-xs text-text-muted">
                  开发工具默认折叠，且均为云端沙箱能力，不会访问本地终端或本地文件系统。
                </div>
              ) : (
                <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                  {section.cards.map((card) => {
                    const Icon = getBuilderIcon(card.icon)
                    return (
                      <article
                        key={card.type}
                        className={cn(
                          'rounded-token-md border bg-bg p-3 transition-colors',
                          card.enabled ? 'border-border hover:border-primary/40 hover:bg-bg-soft/60' : 'border-border/80 opacity-70',
                        )}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex items-center gap-2">
                            <span className="inline-flex h-7 w-7 items-center justify-center rounded-token-md bg-primary/10 text-primary">
                              <Icon size={15} />
                            </span>
                            <div className="min-w-0">
                              <p className="truncate text-sm font-medium text-text-main">{card.title}</p>
                              <p className="text-[11px] text-text-muted">{card.tier}</p>
                            </div>
                          </div>
                          <Button
                            size="sm"
                            variant={card.enabled ? 'primary' : 'ghost'}
                            leftIcon={<Plus size={13} />}
                            disabled={!card.enabled}
                            onClick={() => {
                              selectCapabilityInActiveTab(card.type)
                            }}
                          >
                            {card.enabled ? '打开' : '即将开放'}
                          </Button>
                        </div>
                        <p className="mt-2 text-xs leading-relaxed text-text-sub">{card.description}</p>
                        {!card.enabled ? (
                          <p className="mt-2 text-[11px] text-text-muted">该能力属于后续阶段，当前仅展示信息架构。</p>
                        ) : null}
                      </article>
                    )
                  })}
                </div>
              )}
            </section>
          )
        })}
      </div>
    </div>
  )
}
