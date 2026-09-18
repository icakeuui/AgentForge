import type { SelectHTMLAttributes } from 'react'

import { cn } from '../../lib/cn'

type SelectProps = SelectHTMLAttributes<HTMLSelectElement> & { label?: string }

export function Select({ className, label, id, children, ...props }: SelectProps) {
  return (
    <div className="space-y-1">
      {label ? (
        <label htmlFor={id} className="text-xs font-medium text-text-sub">
          {label}
        </label>
      ) : null}
      <select
        id={id}
        className={cn(
          'h-10 w-full rounded-token-md border border-border bg-surface px-3 text-sm text-text-main',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40',
          className,
        )}
        {...props}
      >
        {children}
      </select>
    </div>
  )
}
