import type { PropsWithChildren } from 'react'

import { cn } from '../../lib/cn'

type Variant = 'neutral' | 'success' | 'error' | 'warning' | 'info'
type BadgeProps = PropsWithChildren<{ variant?: Variant; className?: string }>

const map: Record<Variant, string> = {
  neutral: 'bg-bg-soft text-text-sub',
  success: 'bg-success-soft text-success',
  error: 'bg-error-soft text-error',
  warning: 'bg-warning-soft text-warning',
  info: 'bg-info-soft text-info',
}

export function Badge({ variant = 'neutral', className, children }: BadgeProps) {
  return (
    <span className={cn('inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium', map[variant], className)}>
      {children}
    </span>
  )
}
