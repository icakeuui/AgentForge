import type { InputHTMLAttributes } from 'react'

import { cn } from '../../lib/cn'

type InputProps = InputHTMLAttributes<HTMLInputElement> & { label?: string }

export function Input({ className, label, id, ...props }: InputProps) {
  return (
    <div className="space-y-1">
      {label ? (
        <label htmlFor={id} className="text-xs font-medium text-text-sub">
          {label}
        </label>
      ) : null}
      <input
        id={id}
        className={cn(
          'h-10 w-full rounded-token-md border border-border bg-surface px-3 text-sm text-text-main',
          'placeholder:text-text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40',
          className,
        )}
        {...props}
      />
    </div>
  )
}
