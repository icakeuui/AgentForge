import type { ReactNode } from 'react'

import { cn } from '../../../lib/cn'

interface SessionListItemProps {
  id: string
  title: string
  subtitle?: string
  icon?: ReactNode
  active?: boolean
  onClick?: () => void
}

export function SessionListItem({ title, subtitle, icon, active, onClick }: SessionListItemProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'group relative flex w-full items-start gap-2.5 rounded-token-md px-3 py-2 text-left transition-colors',
        active
          ? 'bg-primary/8 text-text-main shadow-token-sm ring-1 ring-primary/15 before:absolute before:bottom-2 before:left-0 before:top-2 before:w-0.5 before:rounded-full before:bg-primary'
          : 'text-text-sub hover:bg-bg-soft hover:text-text-main',
      )}
    >
      {icon && <div className="mt-0.5 shrink-0 text-text-muted group-hover:text-text-sub">{icon}</div>}
      <div className="flex min-w-0 flex-1 flex-col">
        <span className="truncate text-sm font-medium">{title}</span>
        {subtitle && <span className="truncate text-xs text-text-muted">{subtitle}</span>}
      </div>
    </button>
  )
}
