import { Maximize2, Minimize2, MoreHorizontal } from 'lucide-react'
import type { ReactNode } from 'react'

import { cn } from '../../../lib/cn'
import { Button } from '../../ui/Button'

interface PanelSectionProps {
  title: string
  icon?: ReactNode
  action?: ReactNode
  children: ReactNode
  className?: string
  contentClassName?: string
  isMaximized?: boolean
  onMaximize?: () => void
}

export function PanelSection({ 
  title, 
  icon, 
  action, 
  children, 
  className, 
  contentClassName,
  isMaximized,
  onMaximize
}: PanelSectionProps) {
  return (
    <div className={cn('flex h-full flex-col overflow-hidden rounded-token-lg border border-border bg-surface shadow-token-sm transition-all', className)}>
      <div className="flex h-12 shrink-0 items-center justify-between border-b border-border px-4">
        <div className="flex items-center gap-2 font-semibold text-text-main text-sm">
          {icon && <div className="text-text-muted">{icon}</div>}
          {title}
        </div>
        <div className="flex items-center gap-1">
          {action}
          <Button variant="ghost" size="icon" className="h-6 w-6">
            <MoreHorizontal size={14} className="text-text-muted" />
          </Button>
          {onMaximize && (
            <Button variant="ghost" size="icon" className="h-6 w-6" onClick={onMaximize}>
              {isMaximized ? (
                <Minimize2 size={14} className="text-text-muted" />
              ) : (
                <Maximize2 size={14} className="text-text-muted" />
              )}
            </Button>
          )}
        </div>
      </div>
      <div className={cn('flex-1 overflow-auto bg-bg-soft/50', contentClassName)}>
        {children}
      </div>
    </div>
  )
}
