import { X } from 'lucide-react'
import type { PropsWithChildren } from 'react'

import { cn } from '../../lib/cn'
import { Button } from '../ui/Button'

type DrawerProps = PropsWithChildren<{ open: boolean; onClose: () => void; title: string }>

export function Drawer({ open, onClose, title, children }: DrawerProps) {
  return (
    <>
      <div
        className={cn('fixed inset-0 z-40 bg-slate-900/20 transition-opacity', open ? 'opacity-100' : 'pointer-events-none opacity-0')}
        onClick={onClose}
      />
      <aside
        className={cn(
          'fixed right-0 top-0 z-50 h-full w-full max-w-md border-l border-border bg-surface shadow-token-xl transition-transform',
          open ? 'translate-x-0' : 'translate-x-full',
        )}
      >
        <header className="flex h-14 items-center justify-between border-b border-border px-4">
          <h3 className="text-sm font-semibold text-text-main">{title}</h3>
          <Button variant="ghost" size="icon" onClick={onClose} aria-label="close drawer">
            <X size={16} />
          </Button>
        </header>
        <div className="h-[calc(100%-3.5rem)] overflow-y-auto p-4">{children}</div>
      </aside>
    </>
  )
}
