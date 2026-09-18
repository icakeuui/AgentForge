import { AlertCircle, CircleCheck, Info, TriangleAlert } from 'lucide-react'
import type { PropsWithChildren } from 'react'

import { cn } from '../../lib/cn'

type Variant = 'success' | 'error' | 'warning' | 'info'

const map = {
  success: { wrapper: 'border-success/25 bg-success-soft text-success', icon: CircleCheck },
  error: { wrapper: 'border-error/25 bg-error-soft text-error', icon: AlertCircle },
  warning: { wrapper: 'border-warning/25 bg-warning-soft text-warning', icon: TriangleAlert },
  info: { wrapper: 'border-info/25 bg-info-soft text-info', icon: Info },
} as const

type AlertProps = PropsWithChildren<{ variant?: Variant; title: string; className?: string }>

export function Alert({ variant = 'info', title, className, children }: AlertProps) {
  const Icon = map[variant].icon

  return (
    <div className={cn('rounded-token-md border p-3', map[variant].wrapper, className)}>
      <div className="flex items-start gap-2">
        <Icon size={16} className="mt-0.5 shrink-0" />
        <div className="space-y-1 text-sm">
          <p className="font-semibold">{title}</p>
          {children ? <p className="leading-relaxed">{children}</p> : null}
        </div>
      </div>
    </div>
  )
}
