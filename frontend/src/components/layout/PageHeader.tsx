import type { ReactNode } from 'react'

type PageHeaderProps = {
  title: string
  description?: string
  statusSlot?: ReactNode
  actions?: ReactNode
}

export function PageHeader({ title, description, statusSlot, actions }: PageHeaderProps) {
  return (
    <div className="rounded-token-lg border border-border bg-surface px-5 py-4 shadow-token-sm">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-1">
          <h2 className="text-2xl font-semibold tracking-tight text-text-main">{title}</h2>
          {description ? <p className="text-sm leading-relaxed text-text-muted">{description}</p> : null}
        </div>
        <div className="flex items-center gap-2">{statusSlot}</div>
      </div>
      {actions ? <div className="mt-4 flex items-center gap-2">{actions}</div> : null}
    </div>
  )
}
