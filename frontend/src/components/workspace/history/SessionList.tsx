import type { ReactNode } from 'react'

interface SessionListProps {
  title: string
  action?: ReactNode
  children: ReactNode
}

export function SessionList({ title, action, children }: SessionListProps) {
  return (
    <div className="flex flex-col space-y-2">
      <div className="flex items-center justify-between px-3 text-xs font-semibold uppercase tracking-wider text-text-muted">
        <span>{title}</span>
        {action && <div>{action}</div>}
      </div>
      <div className="flex flex-col space-y-[2px] px-2">{children}</div>
    </div>
  )
}
