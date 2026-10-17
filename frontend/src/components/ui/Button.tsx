import type { ButtonHTMLAttributes, ReactNode } from 'react'

import { cn } from '../../lib/cn'

type Variant = 'primary' | 'secondary' | 'ghost'
type Size = 'sm' | 'md' | 'icon'

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant
  size?: Size
  leftIcon?: ReactNode
}

const variantMap: Record<Variant, string> = {
  primary: 'bg-primary text-white shadow-token-sm hover:bg-primary-hover hover:shadow-token-lg active:translate-y-px',
  secondary: 'border border-border bg-surface text-text-main shadow-[0_1px_2px_rgba(20,35,63,0.04)] hover:border-primary/20 hover:bg-bg-soft',
  ghost: 'text-text-sub hover:bg-bg-soft hover:text-text-main',
}

const sizeMap: Record<Size, string> = {
  sm: 'h-8 px-3 text-xs',
  md: 'h-10 px-4 text-sm',
  icon: 'h-9 w-9',
}

export function Button({ className, children, variant = 'primary', size = 'md', leftIcon, ...props }: ButtonProps) {
  return (
    <button
      className={cn(
        'inline-flex items-center justify-center gap-2 rounded-token-md font-medium transition-all duration-200',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 disabled:cursor-not-allowed disabled:opacity-50',
        variantMap[variant],
        sizeMap[size],
        className,
      )}
      {...props}
    >
      {leftIcon}
      {children}
    </button>
  )
}
