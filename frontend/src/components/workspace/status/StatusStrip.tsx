import { Loader2 } from 'lucide-react'

import type { ExecutionStatus } from '../../../features/execution/execution.types'

interface StatusStripProps {
  status: ExecutionStatus
}

export function StatusStrip({ status }: StatusStripProps) {
  const text = status === 'PENDING' ? '正在初始化...' : '正在思考...'

  return (
    <div className="flex h-10 shrink-0 items-center gap-2 rounded-token-lg border border-border bg-surface px-4 text-sm text-text-main shadow-token-sm">
      <Loader2 size={14} className="animate-spin text-primary" />
      <span>{text}</span>
    </div>
  )
}
