import { ShieldAlert, X } from 'lucide-react'

import type { PendingToolConfirmation } from '../../../features/execution/toolConfirmation'
import { Badge } from '../../ui/Badge'
import { Button } from '../../ui/Button'

interface ToolConfirmationCardProps {
  confirmation: PendingToolConfirmation
  isBusy?: boolean
  onConfirm: () => void
  onReject: () => void
}

export function ToolConfirmationCard({ confirmation, isBusy = false, onConfirm, onReject }: ToolConfirmationCardProps) {
  return (
    <div className="rounded-token-md border border-warning/30 bg-warning-soft px-3 py-3 text-warning shadow-token-sm">
      <div className="flex items-start gap-2">
        <span className="mt-0.5 inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-token-md bg-surface/80">
          <ShieldAlert size={15} />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-semibold text-text-main">需要确认工具动作</span>
            <Badge variant="warning">{confirmation.tool_label}</Badge>
          </div>
          <p className="mt-1 text-xs leading-relaxed text-text-sub">
            {confirmation.mode === 'intent'
              ? '该请求可能触发高风险工具。确认后系统会继续生成具体工具动作，真正执行前仍会校验工具和参数。'
              : '该工具调用带有具体参数，确认后才会重新执行。'}
          </p>
          {confirmation.arguments_summary ? (
            <pre className="mt-2 max-h-28 overflow-auto rounded-token-md border border-warning/20 bg-surface/80 px-2 py-2 text-[11px] leading-relaxed text-text-sub">
              {confirmation.arguments_summary}
            </pre>
          ) : null}
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <Button size="sm" variant="primary" onClick={onConfirm} disabled={isBusy}>
              确认继续
            </Button>
            <Button size="sm" variant="secondary" leftIcon={<X size={13} />} onClick={onReject} disabled={isBusy}>
              拒绝
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
