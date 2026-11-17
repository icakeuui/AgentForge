import { useCallback, useEffect, useState } from 'react'

import { useAgentStore } from '../../../features/agent/agent.store'
import { executionAdapter } from '../../../features/execution/execution.adapter'
import { RUN_AGENT_TRIGGER_EVENT } from '../../../features/execution/execution.events'
import { useExecutionStore } from '../../../features/execution/execution.store'
import { knowledgeAdapter } from '../../../features/knowledge/knowledge.adapter'
import { notify } from '../../../features/notifications/notify'
import { UnifiedChatComposer } from './UnifiedChatComposer'
import type { MessageAttachment } from './MessageAttachments'

export function ChatComposer() {
  const [input, setInput] = useState('')
  const [isUploadingAttachment, setIsUploadingAttachment] = useState(false)
  const [pendingAttachments, setPendingAttachments] = useState<MessageAttachment[]>([])
  const currentAgentId = useAgentStore((state) => state.current_agent_id)
  const currentAgentDetail = useAgentStore((state) => state.current_agent_detail)
  const agentContextStatus = useAgentStore((state) => state.agent_context_status)
  const isExecutionStarting = useExecutionStore((state) => state.is_execution_starting)
  const executionStatus = useExecutionStore((state) => state.status)
  const isComposerLocked = executionStatus === 'PENDING' || executionStatus === 'RUNNING' || isExecutionStarting
  const isAgentAvailable = currentAgentDetail !== null && currentAgentDetail.is_available
  const isAgentReady = currentAgentId !== null && isAgentAvailable && agentContextStatus === 'READY'
  const isDisabled = !isAgentReady || isComposerLocked || isUploadingAttachment
  const unavailableReason = currentAgentDetail?.availability_reason
  const disabledHint =
    isComposerLocked
      ? '模型正在处理当前消息，回复完成后可以继续输入'
      : currentAgentId === null
        ? '请先选择或创建一个可用智能体'
        : !isAgentAvailable
          ? `该智能体当前不可用${unavailableReason ? `：${unavailableReason}` : ''}`
          : '当前智能体未就绪，暂不可输入'

  const submitExecution = useCallback(async () => {
    if (isDisabled || currentAgentId === null) {
      if (isComposerLocked) notify.info('模型正在处理当前消息，回复完成后可以继续输入')
      else if (!isAgentReady) notify.warning(disabledHint)
      return
    }
    const normalizedInput = input.trim()
    if (!normalizedInput) {
      notify.warning('请输入任务指令后再运行')
      return
    }
    const previousMessageIds = new Set(useExecutionStore.getState().conversation_messages.map((message) => message.id))
    const response = await executionAdapter.startExecution(currentAgentId, normalizedInput, [], pendingAttachments)
    const messageWasAdded = useExecutionStore.getState().conversation_messages.some(
      (message) => message.role === 'user' && !previousMessageIds.has(message.id),
    )
    if (response !== null || messageWasAdded) {
      setInput('')
      setPendingAttachments([])
    }
  }, [currentAgentId, disabledHint, input, isComposerLocked, isDisabled, isAgentReady, pendingAttachments])

  const stopExecution = useCallback(async () => {
    if (isComposerLocked) await executionAdapter.stopCurrentExecution()
  }, [isComposerLocked])

  const uploadAttachments = useCallback(async (files: File[]) => {
    if (currentAgentId === null || isDisabled || isUploadingAttachment) return
    setIsUploadingAttachment(true)
    try {
      for (const file of files) {
        const document = await knowledgeAdapter.uploadDocument(currentAgentId, { file })
        setPendingAttachments((current) => [...current, {
          id: document.id,
          name: file.name,
          mime_type: file.type || document.source_mime_type,
          size: file.size,
        }])
        if (document.embedding_status === 'failed') {
          notify.error(`文件已解析但索引失败：${document.embedding_error || file.name}`)
        } else {
          notify.success(`文件已上传：${file.name}`)
        }
      }
    } catch (error) {
      notify.error(error instanceof Error ? error.message : '文件上传失败')
    } finally {
      setIsUploadingAttachment(false)
    }
  }, [currentAgentId, isDisabled, isUploadingAttachment])

  useEffect(() => {
    const handleRunAgentTrigger = () => { void submitExecution() }
    window.addEventListener(RUN_AGENT_TRIGGER_EVENT, handleRunAgentTrigger)
    return () => window.removeEventListener(RUN_AGENT_TRIGGER_EVENT, handleRunAgentTrigger)
  }, [submitExecution])

  return (
    <UnifiedChatComposer
      value={input}
      onChange={setInput}
      onSend={() => void submitExecution()}
      onStop={() => void stopExecution()}
      isRunning={isComposerLocked}
      disabled={isDisabled}
      placeholder={isDisabled ? disabledHint : '请输入本次执行任务'}
      onSelectFiles={(files) => void uploadAttachments(files)}
      attachments={pendingAttachments.map(({ id, name }) => ({ id, name }))}
      onRemoveAttachment={(id) => setPendingAttachments((current) => current.filter((attachment) => attachment.id !== id))}
      isUploading={isUploadingAttachment}
      maxAttachments={1}
    />
  )
}
