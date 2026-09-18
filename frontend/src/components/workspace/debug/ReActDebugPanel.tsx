import { BugPlay } from 'lucide-react'
import { useEffect, useRef } from 'react'

import { useExecutionStore } from '../../../features/execution/execution.store'
import { Badge } from '../../ui/Badge'
import type { ExecutionStatus, ExecutionStep } from '../../../features/execution/execution.types'
import { PanelSection } from '../shared/PanelSection'

interface ReActDebugPanelProps {
  react_steps: ExecutionStep[]
  status: ExecutionStatus
  final_answer?: string | null
  termination_reason: string | null
  error_message?: string | null
  isMaximized?: boolean
  onMaximize?: () => void
  focusedStepIndex?: number | null
}

function stringifyValue(value: unknown): string {
  if (typeof value === 'string') {
    return value
  }
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return String(value)
  }
}

function getThought(step: ExecutionStep): string {
  return typeof step.thought === 'string' ? step.thought : ''
}

function formatInlineValue(value: unknown): string | null {
  if (typeof value === 'string') {
    const trimmed = value.trim()
    return trimmed.length > 0 ? trimmed : null
  }
  if (Array.isArray(value)) {
    const items = value
      .map((item) => (typeof item === 'string' ? item.trim() : String(item)))
      .filter((item) => item.length > 0)
    return items.length > 0 ? items.join(', ') : null
  }
  if (value !== null && value !== undefined) {
    try {
      return JSON.stringify(value)
    } catch {
      return String(value)
    }
  }
  return null
}

export function ReActDebugPanel({ 
  react_steps, 
  status, 
  final_answer,
  termination_reason,
  error_message,
  isMaximized,
  onMaximize,
  focusedStepIndex,
}: ReActDebugPanelProps) {
  const focusedStepRef = useRef<HTMLDivElement | null>(null)
  const error_code = useExecutionStore((state) => state.error_code)
  const error_source = useExecutionStore((state) => state.error_source)
  const error_details = useExecutionStore((state) => state.error_details)
  const shouldShowTermination = status === 'FAILED' || status === 'TERMINATED'
  const visibleFailureMessage =
    final_answer !== null && final_answer !== undefined && final_answer.trim().length > 0
      ? final_answer
      : error_message !== null && error_message !== undefined && error_message.trim().length > 0
        ? error_message
      : termination_reason
  const errorSummaryRows = [
    { label: '来源', value: formatInlineValue(error_source) },
    { label: '错误码', value: formatInlineValue(error_code) },
    { label: '服务返回', value: formatInlineValue(error_details?.provider_message) },
    { label: '工具名称', value: formatInlineValue(error_details?.tool_names) },
    { label: '工具选择', value: formatInlineValue(error_details?.tool_choice) },
  ].filter((row) => row.value !== null)

  useEffect(() => {
    if (focusedStepIndex === null || focusedStepIndex === undefined) {
      return
    }
    focusedStepRef.current?.scrollIntoView({ block: 'center', behavior: 'smooth' })
  }, [focusedStepIndex])

  return (
    <PanelSection 
      title="执行调试" 
      icon={<BugPlay size={16} />} 
      className="flex-1"
      isMaximized={isMaximized}
      onMaximize={onMaximize}
    >
      <div className="flex h-full flex-col gap-3 p-4">
        {shouldShowTermination && visibleFailureMessage !== null && visibleFailureMessage.trim().length > 0 && (
          <div className="rounded-token-md border border-error bg-error-soft p-3 text-sm text-error">
            {visibleFailureMessage}
          </div>
        )}

        {status === 'FAILED' && errorSummaryRows.length > 0 && (
          <div className="rounded-token-md border border-border bg-bg-soft p-3 text-xs text-text-sub">
            <div className="mb-2 font-semibold text-text-main">错误调试</div>
            <div className="space-y-2">
              {errorSummaryRows.map((row) => (
                <div key={row.label}>
                  <span className="font-medium text-text-main">{row.label}: </span>
                  <span className="whitespace-pre-wrap break-words">{row.value}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {react_steps.length === 0 ? (
          <div className="flex flex-1 items-center justify-center text-xs text-text-muted">暂无执行步骤</div>
        ) : (
          <div className="flex flex-1 flex-col gap-3 overflow-auto">
            {react_steps.map((step) => {
              const isFocused = focusedStepIndex === step.step_index
              return (
              <div
                key={step.step_index}
                ref={isFocused ? focusedStepRef : undefined}
                className={`rounded-token-md border bg-surface p-3 text-xs ${
                  isFocused ? 'border-primary ring-2 ring-primary/20' : 'border-border'
                }`}
              >
                <div className="mb-2 flex items-center justify-between">
                  <span className="font-semibold text-text-main">第 {step.step_index} 步</span>
                  <div className="flex items-center gap-1">
                    {step.observation ? (
                      <Badge variant={step.observation.ok ? 'success' : 'error'}>
                        {step.observation.ok ? '成功' : '失败'}
                      </Badge>
                    ) : null}
                    <Badge variant="info">推理步骤</Badge>
                  </div>
                </div>
                <div className="space-y-2 text-text-sub">
                  <div>
                    <span className="font-medium text-text-main">思考过程：</span>
                    <span className="whitespace-pre-wrap">{getThought(step) || '未提供'}</span>
                  </div>
                  <div>
                    <span className="font-medium text-text-main">执行动作：</span>
                    <span>{step.action?.tool_id ?? ''}</span>
                    {step.action ? <span className="ml-2 text-[11px] text-text-muted">类型未确认</span> : null}
                  </div>
                  <div>
                    <span className="font-medium text-text-main">动作入参：</span>
                    <pre className="mt-1 whitespace-pre-wrap rounded-token-sm border border-border bg-bg-soft p-2">
                      {stringifyValue(step.action?.arguments ?? null)}
                    </pre>
                  </div>
                  <div>
                    <span className="font-medium text-text-main">观察结果：</span>
                    <pre className="mt-1 whitespace-pre-wrap rounded-token-sm border border-border bg-bg-soft p-2">
                      {stringifyValue(step.observation)}
                    </pre>
                  </div>
                </div>
              </div>
              )
            })}
          </div>
        )}
      </div>
    </PanelSection>
  )
}
