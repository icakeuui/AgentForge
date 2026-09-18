import type { PropsWithChildren } from 'react'

import { cn } from '../../lib/cn'

type CardProps = PropsWithChildren<{
  className?: string
  title?: string
  description?: string
}>

export function Card({ className, title, description, children }: CardProps) {
  return (
    <article className={cn('rounded-token-lg border border-border bg-surface p-4 shadow-token-sm', className)}>
      {title ? <h3 className="text-base font-semibold text-text-main">{title}</h3> : null}
      {description ? <p className="mt-1 text-sm text-text-muted">{description}</p> : null}
      <div className={cn(title || description ? 'mt-4' : '')}>{children}</div>
    </article>
  )
}
