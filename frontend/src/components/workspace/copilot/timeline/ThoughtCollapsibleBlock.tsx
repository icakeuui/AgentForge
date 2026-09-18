import { ChevronDown, ChevronRight } from 'lucide-react'
import { useMemo, useState } from 'react'

import { cn } from '../../../../lib/cn'

interface ThoughtCollapsibleBlockProps {
  thought: string
  stepIndex?: number
  defaultExpanded?: boolean
  title?: string
  compact?: boolean
}

function summarizeThought(thought: string): string {
  const compact = thought.trim().replace(/\s+/g, ' ')
  return compact.length > 90 ? `${compact.slice(0, 90)}...` : compact
}

export function ThoughtCollapsibleBlock({
  thought,
  stepIndex,
  defaultExpanded = false,
  title,
  compact = false,
}: ThoughtCollapsibleBlockProps) {
  const [expanded, setExpanded] = useState(defaultExpanded)
  const preview = useMemo(() => summarizeThought(thought), [thought])
  const resolvedTitle = title ?? (typeof stepIndex === 'number' ? `思考过程 · 第 ${stepIndex} 步` : '思考过程')

  return (
    <div className="rounded-token-md border border-border bg-bg-soft/40 p-2">
      <button
        type="button"
        className="flex w-full items-center justify-between gap-2 text-left"
        onClick={() => setExpanded((prev) => !prev)}
      >
        <div className="min-w-0">
          <div className="text-[11px] font-semibold uppercase tracking-normal text-text-muted">{resolvedTitle}</div>
          {!expanded ? <p className={cn('mt-1 truncate text-xs text-text-sub', compact && 'text-[11px]')}>{preview}</p> : null}
        </div>
        <div className="shrink-0 text-text-muted">
          {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </div>
      </button>
      <div
        className={cn(
          'overflow-hidden transition-[max-height,opacity] duration-200',
          expanded ? 'mt-2 max-h-[320px] opacity-100' : 'max-h-0 opacity-0',
        )}
      >
        <p className={cn('whitespace-pre-wrap text-xs leading-relaxed text-text-sub', compact && 'text-[11px]')}>{thought}</p>
      </div>
    </div>
  )
}
