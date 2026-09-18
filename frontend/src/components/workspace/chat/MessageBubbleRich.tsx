import { Bot, Check, CheckCircle2, Copy, LoaderCircle, RefreshCw, ThumbsDown, ThumbsUp, User } from 'lucide-react'
import type { ReactNode } from 'react'
import { useMemo, useState } from 'react'

import { cn } from '../../../lib/cn'
import type { ExecutionStatus } from '../../../features/execution/execution.types'

interface MessageBubbleRichProps {
  role: 'assistant' | 'user'
  content: ReactNode
  contentText?: string
  timestamp?: string
  compact?: boolean
  tone?: 'normal' | 'muted'
  badge?: string | null
  status?: ExecutionStatus
  onRegenerate?: () => void
  showActions?: boolean
  showStatus?: boolean
}

type FeedbackState = 'up' | 'down' | null

function statusCopy(status?: ExecutionStatus): { label: string; icon: ReactNode; tone: string } {
  if (status === 'FAILED' || status === 'TERMINATED') {
    return {
      label: status === 'TERMINATED' ? '任务中断' : '任务失败',
      icon: <CheckCircle2 size={14} />,
      tone: 'text-error',
    }
  }
  if (status === 'PENDING' || status === 'RUNNING') {
    return {
      label: '任务进行中',
      icon: <LoaderCircle size={14} className="animate-spin" />,
      tone: 'text-primary',
    }
  }
  return {
    label: '任务完成',
    icon: <CheckCircle2 size={14} />,
    tone: 'text-success',
  }
}

export function MessageBubbleRich({
  role,
  content,
  contentText,
  timestamp,
  compact = false,
  tone = 'normal',
  badge = null,
  status,
  onRegenerate,
  showActions = true,
  showStatus = true,
}: MessageBubbleRichProps) {
  const isAssistant = role === 'assistant'
  const isMuted = tone === 'muted'
  const canCopy = contentText !== undefined && contentText.trim().length > 0
  const [feedback, setFeedback] = useState<FeedbackState>(null)
  const [copied, setCopied] = useState(false)
  const assistantStatus = useMemo(() => statusCopy(status), [status])

  const handleCopy = async () => {
    if (!canCopy || typeof navigator === 'undefined') {
      return
    }
    await navigator.clipboard.writeText(contentText)
    setCopied(true)
    setTimeout(() => setCopied(false), 1600)
  }

  return (
    <div className={cn('flex flex-col gap-2', isAssistant ? 'items-start' : 'items-end')}>
      <div className="flex items-center gap-2 px-1">
        {isAssistant && (
          <div className="flex h-5 w-5 items-center justify-center rounded-full bg-primary/10 text-primary">
            <Bot size={12} />
          </div>
        )}
        <span className="text-xs font-semibold text-text-sub">{isAssistant ? '对话预览' : '你'}</span>
        {timestamp && <span className="text-[10px] text-text-muted">{timestamp}</span>}
        {!isAssistant && (
          <div className="flex h-5 w-5 items-center justify-center rounded-full bg-bg-soft text-text-main">
            <User size={12} />
          </div>
        )}
      </div>

      <div className={cn('flex w-fit max-w-[90%] flex-col items-start gap-1', compact && 'max-w-full')}>
        <div
          className={cn(
            'max-w-full rounded-token-lg px-3 py-2 text-sm',
            compact && 'text-xs',
            isMuted
              ? 'border border-border bg-bg-soft/70 text-text-muted'
              : isAssistant
                ? 'bg-surface text-text-main shadow-token-sm border border-border'
                : 'bg-bg-soft text-text-main border border-border/50',
          )}
        >
          {isAssistant && badge ? (
            <div className="mb-2 inline-flex items-center rounded-full border border-primary/20 bg-primary/5 px-2 py-0.5 text-[11px] font-medium text-primary">
              {badge}
            </div>
          ) : null}
          <div className="leading-relaxed">{content}</div>
        </div>

        {!isAssistant ? (
          <div className="flex items-center px-1">
            <button
              type="button"
              className="rounded-token-md p-1 text-text-muted transition-colors duration-200 hover:bg-bg-soft hover:text-text-main focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 disabled:cursor-not-allowed disabled:opacity-40"
              aria-label="复制消息"
              title="复制消息"
              disabled={!canCopy}
              onClick={() => void handleCopy()}
            >
              {copied ? <Check size={14} className="text-success" /> : <Copy size={14} />}
            </button>
          </div>
        ) : null}
      </div>

      {isAssistant && (showActions || showStatus) ? (
        <div
          className={cn(
            'flex w-full max-w-[90%] items-center justify-between gap-3 px-1 text-xs text-text-muted',
            compact && 'max-w-full',
          )}
        >
          <div className="flex min-w-0 items-center gap-3">
            {showStatus ? (
              <span className={cn('inline-flex items-center gap-1.5 font-semibold', assistantStatus.tone)}>
                {assistantStatus.icon}
                {assistantStatus.label}
              </span>
            ) : null}
          </div>
          {showActions ? (
            <div className="flex shrink-0 items-center gap-1">
              <button
                type="button"
                className={cn('rounded-token-md p-1 text-text-sub hover:bg-bg-soft hover:text-text-main', feedback === 'up' && 'text-primary')}
                aria-label="点赞"
                title="点赞"
                onClick={() => setFeedback((current) => (current === 'up' ? null : 'up'))}
              >
                <ThumbsUp size={15} />
              </button>
              <button
                type="button"
                className={cn('rounded-token-md p-1 text-text-sub hover:bg-bg-soft hover:text-text-main', feedback === 'down' && 'text-primary')}
                aria-label="点踩"
                title="点踩"
                onClick={() => setFeedback((current) => (current === 'down' ? null : 'down'))}
              >
                <ThumbsDown size={15} />
              </button>
              <button
                type="button"
                className="rounded-token-md p-1 text-text-sub hover:bg-bg-soft hover:text-text-main disabled:cursor-not-allowed disabled:opacity-40"
                aria-label="复制回复"
                title="复制回复"
                disabled={!canCopy}
                onClick={() => void handleCopy()}
              >
                {copied ? <Check size={15} className="text-success" /> : <Copy size={15} />}
              </button>
              <button
                type="button"
                className="rounded-token-md p-1 text-text-sub hover:bg-bg-soft hover:text-text-main disabled:cursor-not-allowed disabled:opacity-40"
                aria-label="重新生成"
                title="重新生成"
                disabled={onRegenerate === undefined}
                onClick={onRegenerate}
              >
                <RefreshCw size={15} />
              </button>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}
