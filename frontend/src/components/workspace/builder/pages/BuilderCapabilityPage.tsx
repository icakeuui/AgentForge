import { CheckCircle2, CircleAlert, Save } from 'lucide-react'

import { useBuilderTabsStore } from '../../../../features/ui-shell/builderTabs.store'
import { getCapabilityMeta } from '../../../../features/ui-shell/builderTabs.registry'
import type { BuilderTabType } from '../../../../features/ui-shell/builderTabs.types'
import { Button } from '../../../ui/Button'

interface BuilderCapabilityPageProps {
  type: BuilderTabType
}

export function BuilderCapabilityPage({ type }: BuilderCapabilityPageProps) {
  const tabs = useBuilderTabsStore((state) => state.tabs)
  const activeTabId = useBuilderTabsStore((state) => state.activeTabId)
  const setTabState = useBuilderTabsStore((state) => state.setTabState)
  const meta = getCapabilityMeta(type)
  const activeTab = tabs.find((tab) => tab.id === activeTabId)
  const dirty = activeTab?.state.status === 'dirty'

  return (
    <div className="h-full overflow-auto rounded-token-lg border border-border bg-surface p-5">
      <div className="max-w-4xl space-y-4">
        <div>
          <h2 className="text-lg font-semibold text-text-main">{meta.title}</h2>
          <p className="mt-1 text-sm text-text-sub">{meta.description}</p>
        </div>
        <div className="rounded-token-md border border-dashed border-border bg-bg-soft/40 p-4 text-sm text-text-sub">
          该页面在 P0 提供构建浏览器能力入口与状态位，详细管理功能将在后续阶段逐步接入。
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button
            size="sm"
            variant={dirty ? 'secondary' : 'ghost'}
            leftIcon={<CircleAlert size={14} />}
            onClick={() => {
              if (activeTabId) {
                setTabState(activeTabId, { status: 'dirty', message: '待保存配置' })
              }
            }}
          >
            标记为编辑中
          </Button>
          <Button
            size="sm"
            variant="primary"
            leftIcon={<Save size={14} />}
            onClick={() => {
              if (activeTabId) {
                setTabState(activeTabId, { status: 'ready', message: '已保存' })
              }
            }}
          >
            保存
          </Button>
          {dirty ? (
            <span className="inline-flex items-center gap-1 text-xs text-warning">
              <CircleAlert size={14} /> 当前有未保存更改
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 text-xs text-success">
              <CheckCircle2 size={14} /> 页面状态正常
            </span>
          )}
        </div>
      </div>
    </div>
  )
}
