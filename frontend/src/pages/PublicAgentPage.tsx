import { ArrowLeft, Bot, Loader2, TriangleAlert } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { PlatformShell } from '../components/navigation/PlatformShell'
import { Badge } from '../components/ui/Badge'
import { Card } from '../components/ui/Card'
import { UnifiedChatComposer } from '../components/workspace/chat/UnifiedChatComposer'
import { MessageAttachments, type MessageAttachment } from '../components/workspace/chat/MessageAttachments'
import { RichContentRenderer } from '../components/workspace/rich-content/RichContentRenderer'
import { normalizeApiError } from '../lib/api/error'
import {
  publicAgentAdapter,
  type PublicAgentProfile,
  type PublicConversationMessage,
  type PublicConversation,
} from '../features/public-agent/publicAgent.adapter'
import { publicAgentSummary } from '../features/public-agent/publicAgent.presentation'

type PublicChatMessage = PublicConversationMessage & {
  id: string
  status?: 'PENDING' | 'SUCCEEDED' | 'FAILED'
  attachments?: MessageAttachment[]
}

const TERMINAL_STATUSES = ['SUCCEEDED', 'FAILED', 'TERMINATED'] as const

function createMessage(role: PublicChatMessage['role'], content: string, status?: PublicChatMessage['status'], attachments?: MessageAttachment[]): PublicChatMessage {
  return {
    id: `${role}:${Date.now()}:${Math.random().toString(16).slice(2)}`,
    role,
    content,
    status,
    attachments,
  }
}

function buildHistory(messages: PublicChatMessage[]): PublicConversationMessage[] {
  return messages
    .filter((message) => message.status !== 'PENDING' && message.content.trim().length > 0)
    .map((message) => ({ role: message.role, content: message.content }))
    .slice(-20)
}

function renderPublicMessageContent(message: PublicChatMessage) {
  if (message.role === 'assistant' && message.status === 'SUCCEEDED') {
    return <RichContentRenderer content={message.content} showTextCopy={false} />
  }

  return <span className="whitespace-pre-wrap break-words">{message.content}</span>
}

export function PublicAgentPage() {
  const { slug = '' } = useParams()
  const [profile, setProfile] = useState<PublicAgentProfile | null>(null)
  const [messages, setMessages] = useState<PublicChatMessage[]>([])
  const [input, setInput] = useState('')
  const [isLoadingProfile, setIsLoadingProfile] = useState(true)
  const [isSending, setIsSending] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [selectedFiles, setSelectedFiles] = useState<Array<{ id: string; file: File }>>([])
  const conversationRef = useRef<PublicConversation | null>(null)
  const activeSlugRef = useRef(slug.trim())
  const [error, setError] = useState<string | null>(null)

  const normalizedSlug = useMemo(() => slug.trim(), [slug])

  useEffect(() => {
    let cancelled = false
    activeSlugRef.current = normalizedSlug
    queueMicrotask(() => {
      if (cancelled) return
      setIsLoadingProfile(true)
      setError(null)
      setProfile(null)
      setMessages([])
      setInput('')
      setSelectedFiles([])
      setIsSending(false)
      setIsUploading(false)
      conversationRef.current = null
    })

    publicAgentAdapter
      .fetchPublicProfile(normalizedSlug)
      .then((nextProfile) => {
        if (cancelled) return
        setProfile(nextProfile)
        setMessages([createMessage('assistant', nextProfile.opening_statement, 'SUCCEEDED')])
      })
      .catch((err) => {
        if (cancelled) return
        setError(normalizeApiError(err).message)
      })
      .finally(() => {
        if (!cancelled) setIsLoadingProfile(false)
      })

    return () => {
      cancelled = true
    }
  }, [normalizedSlug])

  const pollExecution = async (executionId: string, assistantMessageId: string) => {
    for (let attempt = 0; attempt < 90; attempt += 1) {
      const replay = await publicAgentAdapter.fetchPublicExecution(normalizedSlug, executionId)
      if (activeSlugRef.current !== normalizedSlug) return
      if (TERMINAL_STATUSES.includes(replay.status as (typeof TERMINAL_STATUSES)[number])) {
        const isSuccess = replay.status === 'SUCCEEDED'
        setMessages((prev) =>
          prev.map((message) =>
            message.id === assistantMessageId
              ? {
                  ...message,
                  content: isSuccess ? replay.final_answer || '已完成。' : replay.error_message || '执行失败，请稍后重试。',
                  status: isSuccess ? 'SUCCEEDED' : 'FAILED',
                }
              : message,
          ),
        )
        return
      }
      await new Promise((resolve) => window.setTimeout(resolve, 1000))
    }

    setMessages((prev) =>
      prev.map((message) =>
        message.id === assistantMessageId
          ? { ...message, content: '当前回复仍在处理中，请稍后刷新查看。', status: 'FAILED' }
          : message,
      ),
    )
  }

  const handleSubmit = async () => {
    const normalizedInput = input.trim() || (selectedFiles.length > 0 ? '请阅读本次附件。' : '')
    if (!profile || normalizedInput.length === 0 || isSending) return

    const history = buildHistory(messages)
    setIsSending(true)
    setError(null)
    let assistantMessageId: string | null = null

    try {
      let conversation = conversationRef.current
      const attachmentIds: string[] = []
      const messageAttachments: MessageAttachment[] = []
      if (selectedFiles.length > 0) {
        setIsUploading(true)
        if (!conversation) {
          conversation = await publicAgentAdapter.createConversation(normalizedSlug)
          if (activeSlugRef.current !== normalizedSlug) return
          conversationRef.current = conversation
        }
        for (const selected of selectedFiles) {
          const uploaded = await publicAgentAdapter.uploadAttachment(normalizedSlug, conversation, selected.file)
          if (activeSlugRef.current !== normalizedSlug) return
          attachmentIds.push(uploaded.id)
          messageAttachments.push({
            id: uploaded.id,
            name: selected.file.name,
            mime_type: selected.file.type,
            size: selected.file.size,
            conversation_id: conversation.conversation_id,
          })
        }
        setIsUploading(false)
      }
      const userMessage = createMessage('user', normalizedInput, 'SUCCEEDED', messageAttachments)
      const assistantMessage = createMessage('assistant', '正在思考...', 'PENDING')
      assistantMessageId = assistantMessage.id
      setMessages((prev) => [...prev, userMessage, assistantMessage])
      const started = await publicAgentAdapter.startPublicExecution(normalizedSlug, normalizedInput, history, conversation ?? undefined, attachmentIds)
      if (activeSlugRef.current !== normalizedSlug) return
      setInput('')
      setSelectedFiles([])
      await pollExecution(started.execution_id, assistantMessage.id)
    } catch (err) {
      if (activeSlugRef.current !== normalizedSlug) return
      const message = normalizeApiError(err).message
      if (assistantMessageId) {
        setMessages((prev) => prev.map((item) => item.id === assistantMessageId ? { ...item, content: message, status: 'FAILED' } : item))
      }
      setError(message)
    } finally {
      if (activeSlugRef.current === normalizedSlug) {
        setIsUploading(false)
        setIsSending(false)
      }
    }
  }

  if (isLoadingProfile) {
    return (
      <PlatformShell>
        <main className="flex min-h-screen items-center justify-center bg-bg/70 px-4 text-text-sub">
          <div className="flex items-center gap-2 rounded-token-lg border border-border bg-surface px-5 py-4 text-sm shadow-token-sm">
            <Loader2 size={16} className="animate-spin text-primary" />
            正在打开智能体链接...
          </div>
        </main>
      </PlatformShell>
    )
  }

  if (profile === null) {
    return (
      <PlatformShell>
        <main className="flex min-h-screen items-center justify-center bg-bg/70 px-4">
          <Card className="w-full max-w-md p-6 text-center">
            <TriangleAlert className="mx-auto text-error" size={26} />
            <h1 className="mt-3 text-base font-semibold text-text-main">链接不可用</h1>
            <p className="mt-2 text-sm leading-relaxed text-text-sub">{error ?? '这个智能体链接不存在或已被停用。'}</p>
            <Link to="/square" className="mt-4 inline-flex items-center gap-2 text-sm font-medium text-primary hover:underline">
              <ArrowLeft size={15} /> 返回智能体广场
            </Link>
          </Card>
        </main>
      </PlatformShell>
    )
  }

  return (
    <PlatformShell>
      <main className="min-h-screen bg-bg/70 text-text-main">
        <div className="mx-auto grid min-h-screen w-full max-w-[1440px] gap-5 px-4 py-5 sm:px-6 lg:grid-cols-[minmax(260px,320px)_minmax(0,1fr)] lg:gap-6 lg:px-8 lg:py-7">
          <aside className="flex min-w-0 flex-col gap-4">
            <Link to="/square" className="inline-flex w-fit items-center gap-2 rounded-token-md px-2 py-1.5 text-sm font-medium text-text-sub transition-colors hover:bg-surface hover:text-primary">
              <ArrowLeft size={15} /> 返回智能体广场
            </Link>
            <Card className="p-5 sm:p-6">
              <div className="flex items-start gap-3">
                <span className="flex h-12 w-12 shrink-0 items-center justify-center overflow-hidden rounded-token-md bg-primary/10 text-primary ring-1 ring-primary/10">
                  {profile.avatar_url ? <img src={profile.avatar_url} alt="" className="h-full w-full object-cover" /> : <Bot size={21} />}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <h1 className="text-lg font-semibold tracking-tight text-text-main">{profile.title}</h1>
                    <Badge variant="success">公开试用</Badge>
                  </div>
                  <p className="mt-2 text-sm leading-6 text-text-sub">{publicAgentSummary(profile)}</p>
                </div>
              </div>
            </Card>
          </aside>

          <section className="flex min-h-[68vh] min-w-0 flex-col overflow-hidden rounded-token-lg border border-border/80 bg-surface shadow-token-sm lg:min-h-[calc(100vh-3.5rem)]">
            <header className="flex shrink-0 flex-wrap items-center justify-between gap-3 border-b border-border/80 px-4 py-4 sm:px-5">
              <div>
                <h2 className="text-base font-semibold tracking-tight text-text-main">对话试用</h2>
                <p className="mt-0.5 text-xs text-text-muted">向 {profile.title} 提问，体验公开智能体。</p>
              </div>
              <Badge variant={isSending ? 'info' : 'neutral'}>{isSending ? '正在回复' : '等待提问'}</Badge>
            </header>

            <div className="flex-1 overflow-y-auto bg-bg/45 p-4 sm:p-6">
              {messages.length === 0 ? (
                <div className="flex h-full min-h-40 items-center justify-center rounded-token-lg border border-dashed border-border bg-surface/80 px-5 text-center text-sm text-text-muted">
                  输入一个问题，开始体验这个智能体。
                </div>
              ) : (
                <div className="mx-auto max-w-3xl space-y-4">
                  {messages.map((message) => (
                    <div key={message.id} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                      <div
                        className={`max-w-[88%] rounded-token-lg px-4 py-3 text-sm leading-relaxed shadow-token-sm sm:max-w-[82%] ${
                          message.role === 'user'
                            ? 'bg-primary text-white'
                            : message.status === 'FAILED'
                              ? 'border border-error/20 bg-error-soft text-error'
                              : 'border border-border/80 bg-surface text-text-main'
                        }`}
                      >
                        {message.status === 'PENDING' ? (
                          <span className="inline-flex items-center gap-2">
                            <Loader2 size={14} className="animate-spin" />
                            {message.content}
                          </span>
                        ) : (
                          renderPublicMessageContent(message)
                        )}
                        {message.role === 'user' && <MessageAttachments attachments={message.attachments} />}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="shrink-0 border-t border-border/80 bg-surface p-4 sm:p-5">
              {error ? <p className="mb-2 text-xs text-error" role="alert">{error}</p> : null}
              <div className="mx-auto max-w-3xl">
                <UnifiedChatComposer
                  value={input}
                  onChange={setInput}
                  onSend={() => void handleSubmit()}
                  disabled={isSending}
                  isRunning={isSending}
                  isUploading={isUploading}
                  placeholder="输入你想问的问题..."
                  attachments={selectedFiles.map(({ id, file }) => ({ id, name: file.name }))}
                  onSelectFiles={(files) => setSelectedFiles((current) => [...current, ...files.map((file) => ({ id: crypto.randomUUID(), file }))])}
                  onRemoveAttachment={(id) => setSelectedFiles((current) => current.filter((entry) => entry.id !== id))}
                />
              </div>
            </div>
          </section>
        </div>
      </main>
    </PlatformShell>
  )
}
