import { Search } from 'lucide-react'
import type { ReactNode } from 'react'

import { useUiShellStore } from '../../features/ui-shell/uiShell.store'
import { useBreadcrumbs } from '../../hooks/useBreadcrumbs'
import { Button } from '../ui/Button.tsx'

type TopHeaderProps = {
  rightSlot?: ReactNode
}

export function TopHeader({ rightSlot }: TopHeaderProps) {
  const breadcrumbs = useBreadcrumbs()
  const setCommandPaletteOpen = useUiShellStore((state) => state.setCommandPaletteOpen)

  return (
    <header className="sticky top-0 z-10 border-b border-border bg-surface/95 px-4 backdrop-blur md:px-6">
      <div className="flex h-16 items-center justify-between gap-4">
        <div className="min-w-0">
          <div className="truncate text-xs text-text-muted">{breadcrumbs.join(' / ')}</div>
          <h1 className="truncate text-base font-semibold text-text-main">AgentForge 控制台</h1>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            leftIcon={<Search size={14} />}
            onClick={() => setCommandPaletteOpen(true)}
          >
            搜索
          </Button>
          {rightSlot}
        </div>
      </div>
    </header>
  )
}
