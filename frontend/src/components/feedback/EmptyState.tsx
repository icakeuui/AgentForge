import { Inbox } from 'lucide-react'
import type { ReactNode } from 'react'

import { Button } from '../ui/Button'

type EmptyStateProps = {
  title: string
  description: string
  actionLabel?: string
  onAction?: () => void
  icon?: ReactNode
}

export function EmptyState({ title, description, actionLabel, onAction, icon = <Inbox size={18} /> }: EmptyStateProps) {
  return (
    <div className="rounded-token-lg border border-dashed border-border bg-surface px-5 py-10 text-center">
      <div className="mx-auto mb-3 flex h-9 w-9 items-center justify-center rounded-full bg-bg-soft text-text-sub">{icon}</div>
      <h3 className="text-sm font-semibold text-text-main">{title}</h3>
      <p className="mx-auto mt-1 max-w-prose text-sm leading-relaxed text-text-muted">{description}</p>
      {actionLabel ? (
        <div className="mt-4">
          <Button variant="secondary" onClick={onAction}>
            {actionLabel}
          </Button>
        </div>
      ) : null}
    </div>
  )
}
