import { LayoutDashboard } from 'lucide-react'

import { useWorkspaceTabsStore } from '../../../features/ui-shell/workspaceTabs.store'
import { Button } from '../../ui/Button'

export function CanvasTab() {
  const pins = useWorkspaceTabsStore((state) => state.canvas.pins)
  const jumpTo = useWorkspaceTabsStore((state) => state.jumpTo)

  if (pins.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center rounded-token-lg border border-dashed border-border bg-surface p-6 text-center">
        <LayoutDashboard size={34} className="mb-3 text-border" />
        <p className="text-sm font-medium text-text-main">画布当前为空</p>
        <p className="mt-1 max-w-md text-xs leading-relaxed text-text-muted">
          这里是轻量 pinboard，用于固定最终答复、文件、链接或步骤引用；不是工作流编排画布。
        </p>
      </div>
    )
  }

  return (
    <div className="h-full overflow-auto rounded-token-lg border border-border bg-surface p-4 shadow-token-sm">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-text-main">画布</h2>
        <span className="text-xs text-text-muted">{pins.length} 个固定项</span>
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        {pins.map((pin) => (
          <article key={pin.id} className="rounded-token-md border border-border bg-bg-soft/50 p-3">
            <div className="mb-1 text-[11px] uppercase tracking-normal text-text-muted">{pin.type}</div>
            <h3 className="text-sm font-semibold text-text-main">{pin.title}</h3>
            {pin.summary ? <p className="mt-2 text-xs leading-relaxed text-text-sub">{pin.summary}</p> : null}
            {pin.target ? (
              <Button variant="ghost" size="sm" className="mt-3" onClick={() => jumpTo(pin.target ?? { type: 'tab', tab: 'canvas' })}>
                跳到来源
              </Button>
            ) : null}
          </article>
        ))}
      </div>
    </div>
  )
}
