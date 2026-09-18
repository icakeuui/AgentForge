import { AlertCircle, CheckCircle2, ChevronRight, Cpu, Loader2 } from 'lucide-react'

import { Badge } from '../../ui/Badge'

interface SkillCallBoxProps {
  toolId: string
  argsSummary: string
  status: 'running' | 'success' | 'error'
  detailsLabel?: string
  onViewDetails?: () => void
}

const statusCopy: Record<SkillCallBoxProps['status'], string> = {
  running: '执行中',
  success: '成功',
  error: '失败',
}

export function SkillCallBox({ toolId, argsSummary, status, detailsLabel = '查看详情', onViewDetails }: SkillCallBoxProps) {
  const StatusIcon = status === 'running' ? Loader2 : status === 'success' ? CheckCircle2 : AlertCircle

  return (
    <div className="flex w-full flex-col overflow-hidden rounded-token-md border border-border bg-surface">
      <div className="border-b border-border px-3 py-2">
        <div className="flex items-center justify-between gap-2 text-xs font-medium text-text-sub">
          <div className="flex min-w-0 items-center gap-2">
            <div className="flex h-5 w-5 shrink-0 items-center justify-center rounded-token-md bg-primary/10 text-primary">
              <Cpu size={12} />
            </div>
            <span className="truncate">调用工具：{toolId || '未知工具'}</span>
          </div>
          <div className={`flex shrink-0 items-center gap-1 text-[10px] ${status === 'error' ? 'text-error' : status === 'success' ? 'text-success' : 'text-text-muted'}`}>
            <StatusIcon size={12} className={status === 'running' ? 'animate-spin' : undefined} />
            <span>{statusCopy[status]}</span>
          </div>
        </div>
        <div className="mt-2 flex items-center gap-2">
          <Badge variant="neutral" className="text-[10px]">
            类型未确认
          </Badge>
          {argsSummary ? <span className="truncate text-[11px] text-text-muted">参数：{argsSummary}</span> : null}
        </div>
      </div>
      <button
        type="button"
        onClick={onViewDetails}
        className="flex items-center justify-between bg-bg-soft px-3 py-1.5 text-xs text-text-muted transition-colors hover:text-text-main disabled:cursor-not-allowed disabled:opacity-60"
        disabled={!onViewDetails}
      >
        <span>{detailsLabel}</span>
        <ChevronRight size={14} />
      </button>
    </div>
  )
}
