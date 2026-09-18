import { ChevronLeft, ChevronRight, Settings2 } from 'lucide-react'
import { NavLink } from 'react-router-dom'

import { useUiShellStore } from '../../features/ui-shell/uiShell.store'
import { cn } from '../../lib/cn'
import { NAV_ITEMS } from '../../shared/navigation'
import { Button } from '../ui/Button'

export function SidebarNav() {
  const sidebarCollapsed = useUiShellStore((state) => state.sidebarCollapsed)
  const toggleSidebar = useUiShellStore((state) => state.toggleSidebar)

  return (
    <aside
      className={cn(
        'fixed inset-y-0 left-0 z-20 hidden border-r border-border bg-surface md:flex md:flex-col',
        sidebarCollapsed ? 'w-20' : 'w-72',
      )}
    >
      <div className="flex h-16 items-center justify-between border-b border-border px-4">
        <div className="overflow-hidden">
          <p className="truncate text-sm font-semibold text-text-main">AgentForge</p>
          <p className="truncate text-xs text-text-muted">平台控制台</p>
        </div>
        <Button variant="ghost" size="icon" onClick={toggleSidebar} aria-label="切换侧边栏" title="切换侧边栏">
          {sidebarCollapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        </Button>
      </div>

      <nav className="flex-1 space-y-1 p-3">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 rounded-token-md px-3 py-2 text-sm transition-colors duration-200',
                  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40',
                  isActive
                    ? 'bg-primary text-white shadow-token-sm'
                    : 'text-text-sub hover:bg-bg-soft hover:text-text-main',
                )
              }
            >
              <Icon size={16} />
              {!sidebarCollapsed && <span>{item.label}</span>}
            </NavLink>
          )
        })}
      </nav>

      <div className="border-t border-border p-3">
        <button
          type="button"
          className="flex w-full items-center gap-3 rounded-token-md px-3 py-2 text-sm text-text-sub transition-colors hover:bg-bg-soft hover:text-text-main"
        >
          <Settings2 size={16} />
          {!sidebarCollapsed && <span>账户与偏好</span>}
        </button>
      </div>
    </aside>
  )
}
