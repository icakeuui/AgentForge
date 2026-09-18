import { Brain, CheckCircle2, ChevronDown, Database, ExternalLink, MessageSquareText, ShieldCheck, Wrench } from 'lucide-react'
import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'

import { cn } from '../../../../lib/cn'
import { useAgentStore } from '../../../../features/agent/agent.store'
import { executionAdapter } from '../../../../features/execution/execution.adapter'
import { getAssistantPlaceholder, getLiveExecutionStage } from '../../../../features/execution/execution.presentation'
import { useExecutionStore } from '../../../../features/execution/execution.store'
import type { ConversationMessage, ExecutionStatus } from '../../../../features/execution/execution.types'
import { findPendingToolConfirmation, toConfirmedToolAction } from '../../../../features/execution/toolConfirmation'
import { notify } from '../../../../features/notifications/notify'
import { useBuilderTabsStore } from '../../../../features/ui-shell/builderTabs.store'
import { Badge } from '../../../ui/Badge'
import { Button } from '../../../ui/Button'
import { MessageBubbleRich } from '../../chat/MessageBubbleRich'
import { ToolConfirmationCard } from '../../chat/ToolConfirmationCard'
import { RichContentRenderer } from '../../rich-content/RichContentRenderer'

const STATUS_LABEL: Record<ExecutionStatus, string> = {
  IDLE: '空闲',
  PENDING: '准备中',
  RUNNING: '执行中',
  SUCCEEDED: '已完成',
  FAILED: '失败',
  TERMINATED: '已中断',
}

function assistantPreviewContent(status: ExecutionStatus, finalAnswer: string | null, errorMessage: string | null, terminationReason: string | null): string | null {
  if (finalAnswer !== null && finalAnswer.trim().length > 0) {
    return finalAnswer
  }
  if (status === 'PENDING' || status === 'RUNNING') {
    return null
  }
  if (status === 'FAILED' || status === 'TERMINATED') {
    return errorMessage ?? terminationReason ?? '本次执行未能完成，请查看运行日志。'
  }
  return null
}

function renderMessageContent(message: ConversationMessage) {
  if (message.role === 'assistant') {
    return <RichContentRenderer content={message.content} showTextCopy={false} />
  }
  return <span className="whitespace-pre-wrap break-words">{message.content}</span>
}

function previousUserInput(messages: ConversationMessage[], index: number): string | null {
  for (let current = index - 1; current >= 0; current -= 1) {
    const message = messages[current]
    if (message.role === 'user' && message.content.trim().length > 0) {
      return message.content.trim()
    }
  }
  return null
}

function stageIcon(label: string) {
  if (label.includes('知识库')) return <Database size={14} className="text-primary" />
  if (label.includes('工具')) return <Wrench size={14} className="text-primary" />
  return <Brain size={14} className="text-primary" />
}

type ConversationDisplayItem =
  | {
      type: 'message'
      message: ConversationMessage
      index: number
    }
  | {
      type: 'process'
      id: string
      status?: ExecutionStatus
      messages: ConversationMessage[]
    }

function createConversationDisplayItems(messages: ConversationMessage[]): ConversationDisplayItem[] {
  const items: ConversationDisplayItem[] = []
  let processMessages: ConversationMessage[] = []

  const flushProcessMessages = () => {
    if (processMessages.length === 0) {
      return
    }

    const first = processMessages[0]
    items.push({
      type: 'process',
      id: `process:${first.execution_id ?? first.id}:${processMessages.length}`,
      status: processMessages[processMessages.length - 1].status,
      messages: processMessages,
    })
    processMessages = []
  }

  messages.forEach((message, index) => {
    if (message.source === 'activity') {
      processMessages.push(message)
      return
    }

    flushProcessMessages()
    items.push({ type: 'message', message, index })
  })

  flushProcessMessages()
  return items
}

function processStepIcon(content: string) {
  if (content.includes('知识库')) return <Database size={14} />
  if (content.includes('工具')) return <Wrench size={14} />
  if (content.includes('策略') || content.includes('校验') || content.includes('修正')) return <ShieldCheck size={14} />
  return <Brain size={14} />
}

function processSummary(messages: ConversationMessage[]) {
  const hasKnowledge = messages.some((message) => message.content.includes('知识库'))
  const hasTool = messages.some((message) => message.content.includes('工具'))
  const hasPolicy = messages.some((message) => message.content.includes('策略') || message.content.includes('校验') || message.content.includes('修正'))
  const parts = [hasKnowledge ? '知识库检索' : null, hasTool ? '工具调用' : null, hasPolicy ? '策略校验' : null].filter((part): part is string => part !== null)

  if (parts.length === 0) {
    return `已处理 ${messages.length} 个过程步骤`
  }
  return `${parts.join(' · ')} · ${messages.length} 个步骤`
}

function AssistantProcessPanel({ messages, status }: { messages: ConversationMessage[]; status?: ExecutionStatus }) {
  const [isOpen, setIsOpen] = useState(status === 'PENDING' || status === 'RUNNING')
  const isBusy = status === 'PENDING' || status === 'RUNNING'

  return (
    <section className="max-w-[90%] rounded-token-md border border-primary/10 bg-primary/[0.03] px-3 py-2 text-xs text-text-sub">
      <button
        type="button"
        className="flex w-full items-center justify-between gap-3 text-left"
        aria-expanded={isOpen}
        onClick={() => setIsOpen((current) => !current)}
      >
        <span className="flex min-w-0 items-center gap-2">
          <span
            className={cn(
              'flex h-5 w-5 shrink-0 items-center justify-center rounded-full border',
              isBusy ? 'border-primary/25 bg-primary/10 text-primary' : 'border-success/25 bg-success/10 text-success',
            )}
          >
            {isBusy ? <Brain size={12} /> : <CheckCircle2 size={12} />}
          </span>
          <span className="shrink-0 font-semibold text-text-main">过程摘要</span>
          <span className="truncate text-text-muted">{processSummary(messages)}</span>
        </span>
        <ChevronDown size={15} className={cn('shrink-0 text-text-muted transition-transform duration-200', isOpen && 'rotate-180')} />
      </button>

      {isOpen ? (
        <div className="mt-3 space-y-2 border-l border-primary/15 pl-3">
          {messages.map((message) => (
            <div key={message.id} className="relative">
              <span className="absolute -left-[19px] top-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-surface text-primary">
                {processStepIcon(message.content)}
              </span>
              <p className="leading-relaxed text-text-sub">{message.content}</p>
            </div>
          ))}
        </div>
      ) : null}
    </section>
  )
}

export function PreviewTabPage() {
  const currentAgentId = useAgentStore((state) => state.current_agent_id)
  const { current_execution_id, status, final_answer, error_message, termination_reason, last_user_input, preview_url, conversation_messages, conversation_cleared_execution_id, step_logs } =
    useExecutionStore()
  const openRunLogsTab = useBuilderTabsStore((state) => state.openRunLogsTab)
  const setTabStateByType = useBuilderTabsStore((state) => state.setTabStateByType)
  const liveStage = useMemo(() => getLiveExecutionStage(status, step_logs), [status, step_logs])
  const conversationDisplayItems = useMemo(() => createConversationDisplayItems(conversation_messages), [conversation_messages])
  const liveContent = useMemo(() => {
    const staticContent = assistantPreviewContent(status, final_answer, error_message, termination_reason)
    if (staticContent !== null) {
      return staticContent
    }
    if (status === 'PENDING' || status === 'RUNNING') {
      return getAssistantPlaceholder(status, step_logs)
    }
    return null
  }, [status, final_answer, error_message, termination_reason, step_logs])
  const hasLiveContentInHistory =
    liveContent !== null &&
    conversation_messages.some((message) => message.role === 'assistant' && message.content === liveContent)
  const isCurrentExecutionCleared = current_execution_id !== null && conversation_cleared_execution_id === current_execution_id
  const shouldShowLiveAssistant = liveContent !== null && !hasLiveContentInHistory && !isCurrentExecutionCleared
  const hasConversation = conversation_messages.length > 0 || shouldShowLiveAssistant
  const canConfirmToolAction = status !== 'PENDING' && status !== 'RUNNING'
  const [dismissedConfirmationIds, setDismissedConfirmationIds] = useState<Set<string>>(() => new Set())
  const detectedPendingConfirmation = canConfirmToolAction ? findPendingToolConfirmation(step_logs) : null
  const pendingConfirmation =
    detectedPendingConfirmation !== null && !dismissedConfirmationIds.has(detectedPendingConfirmation.id)
      ? detectedPendingConfirmation
      : null
  const shouldShowLiveProcess = shouldShowLiveAssistant && (status === 'PENDING' || status === 'RUNNING')
  const previewScrollRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    setTabStateByType('preview', {
      status: status === 'FAILED' || status === 'TERMINATED' ? 'error' : status === 'PENDING' || status === 'RUNNING' ? 'loading' : hasConversation ? 'ready' : 'idle',
      message: hasConversation ? '对话已更新' : '暂无交流内容',
    })
  }, [hasConversation, setTabStateByType, status])

  useEffect(() => {
    const scrollContainer = previewScrollRef.current
    if (scrollContainer === null || !hasConversation) {
      return
    }

    const frameId = window.requestAnimationFrame(() => {
      scrollContainer.scrollTo({
        top: scrollContainer.scrollHeight,
        behavior: status === 'PENDING' || status === 'RUNNING' ? 'auto' : 'smooth',
      })
    })

    return () => window.cancelAnimationFrame(frameId)
  }, [conversation_messages.length, hasConversation, liveContent, liveStage, pendingConfirmation, status])

  const handleRegenerate = (input: string | null) => {
    if (currentAgentId === null || input === null) {
      notify.warning('没有可重新生成的用户输入')
      return
    }
    void executionAdapter.startExecution(currentAgentId, input)
  }

  const handleConfirmToolAction = () => {
    if (currentAgentId === null || last_user_input === null || pendingConfirmation === null) {
      notify.warning('没有可确认的工具动作')
      return
    }
    void executionAdapter.startExecution(currentAgentId, last_user_input, [toConfirmedToolAction(pendingConfirmation)])
  }

  const handleRejectToolAction = () => {
    if (pendingConfirmation !== null) {
      setDismissedConfirmationIds((current) => new Set(current).add(pendingConfirmation.id))
    }
    notify.info('已拒绝工具动作，本次执行不会继续调用该工具')
  }

  let body: ReactNode
  if (!hasConversation) {
    body = (
      <div className="flex h-full flex-col items-center justify-center gap-3 rounded-token-md border border-dashed border-border bg-bg-soft/30 px-6 text-center">
        <MessageSquareText size={28} className="text-primary" />
        <p className="text-base font-semibold text-text-main">暂无交流测试内容</p>
        <p className="max-w-xl text-sm text-text-sub">在右侧对话预览输入测试消息后，这里会展示用户与对话预览的气泡对话。</p>
      </div>
    )
  } else {
    body = (
      <div ref={previewScrollRef} className="h-full overflow-auto rounded-token-md border border-border bg-bg-soft/30 p-4">
        <div className="mx-auto flex max-w-3xl flex-col gap-4">
          {liveStage ? (
            <div className="rounded-token-md border border-primary/20 bg-primary/5 px-4 py-3">
              <div className="flex items-center gap-2 text-sm font-semibold text-text-main">
                {stageIcon(liveStage.label)}
                <span>{liveStage.label}</span>
              </div>
              <p className="mt-1 text-xs leading-relaxed text-text-sub">{liveStage.description}</p>
            </div>
          ) : null}
          {pendingConfirmation ? (
            <ToolConfirmationCard
              confirmation={pendingConfirmation}
              isBusy={!canConfirmToolAction}
              onConfirm={handleConfirmToolAction}
              onReject={handleRejectToolAction}
            />
          ) : null}
          {conversationDisplayItems.map((item) => {
            if (item.type === 'process') {
              return <AssistantProcessPanel key={item.id} messages={item.messages} status={item.status} />
            }

            const { message, index } = item
            const regenerateInput = message.role === 'assistant' ? previousUserInput(conversation_messages, index) : null
            return (
              <MessageBubbleRich
                key={message.id}
                role={message.role}
                badge={message.knowledge_badge ?? null}
                tone={message.source === 'opening' || message.source === 'activity' ? 'muted' : 'normal'}
                content={renderMessageContent(message)}
                contentText={message.content}
                status={message.status}
                showActions={message.role === 'assistant' && message.source !== 'opening' && message.source !== 'activity'}
                showStatus={message.role === 'assistant' && message.source !== 'opening' && message.source !== 'activity'}
                onRegenerate={message.role === 'assistant' && regenerateInput !== null ? () => handleRegenerate(regenerateInput) : undefined}
              />
            )
          })}
          {shouldShowLiveProcess ? (
            <AssistantProcessPanel
              messages={[
                {
                  id: `live-process:${current_execution_id ?? 'draft'}`,
                  role: 'assistant',
                  content: liveContent,
                  execution_id: current_execution_id,
                  status,
                  source: 'activity',
                },
              ]}
              status={status}
            />
          ) : shouldShowLiveAssistant ? (
            <MessageBubbleRich
              role="assistant"
              content={<RichContentRenderer content={liveContent} showTextCopy={false} />}
              contentText={liveContent}
              status={status}
              onRegenerate={() => handleRegenerate(last_user_input)}
            />
          ) : null}
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col gap-4 overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-token-md border border-border bg-surface px-4 py-3">
        <div>
          <p className="text-xs text-text-muted">预览</p>
          <p className="text-sm font-semibold text-text-main">用户与对话预览测试对话</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={status === 'FAILED' || status === 'TERMINATED' ? 'error' : status === 'SUCCEEDED' ? 'success' : 'info'}>
            {STATUS_LABEL[status]}
          </Badge>
          <Button size="sm" variant="ghost" onClick={() => openRunLogsTab({ executionId: current_execution_id, stepIndex: null })}>
            查看运行日志
          </Button>
          {preview_url ? (
            <Button
              size="sm"
              variant="ghost"
              leftIcon={<ExternalLink size={14} />}
              onClick={() => window.open(preview_url, '_blank', 'noopener,noreferrer')}
            >
              打开沙箱页面
            </Button>
          ) : null}
        </div>
      </div>
      <div className="min-h-0 flex-1 overflow-hidden">{body}</div>
    </div>
  )
}
