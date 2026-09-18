import { Bot, Loader2, Send, TriangleAlert } from 'lucide-react'
import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { useParams } from 'react-router-dom'

import { Button } from '../components/ui/Button'
import { RichContentRenderer } from '../components/workspace/rich-content/RichContentRenderer'
import { normalizeApiError } from '../lib/api/error'
import {
  publicAgentAdapter,
  type PublicAgentProfile,
  type PublicConversationMessage,
} from '../features/public-agent/publicAgent.adapter'

type PublicChatMessage = PublicConversationMessage & {
  id: string
  status?: 'PENDING' | 'SUCCEEDED' | 'FAILED'
}

const TERMINAL_STATUSES = ['SUCCEEDED', 'FAILED', 'TERMINATED'] as const

function createMessage(role: PublicChatMessage['role'], content: string, status?: PublicChatMessage['status']): PublicChatMessage {
  return {
    id: `${role}:${Date.now()}:${Math.random().toString(16).slice(2)}`,
    role,
    content,
    status,
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
  const [error, setError] = useState<string | null>(null)

  const normalizedSlug = useMemo(() => slug.trim(), [slug])

  useEffect(() => {
    let cancelled = false
    setIsLoadingProfile(true)
    setError(null)
    setProfile(null)
    setMessages([])

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

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const normalizedInput = input.trim()
    if (!profile || normalizedInput.length === 0 || isSending) return

    const history = buildHistory(messages)
    const userMessage = createMessage('user', normalizedInput, 'SUCCEEDED')
    const assistantMessage = createMessage('assistant', '正在思考...', 'PENDING')
    setMessages((prev) => [...prev, userMessage, assistantMessage])
    setInput('')
    setIsSending(true)
    setError(null)

    try {
      const started = await publicAgentAdapter.startPublicExecution(normalizedSlug, normalizedInput, history)
      await pollExecution(started.execution_id, assistantMessage.id)
    } catch (err) {
      const message = normalizeApiError(err).message
      setMessages((prev) =>
        prev.map((item) => (item.id === assistantMessage.id ? { ...item, content: message, status: 'FAILED' } : item)),
      )
      setError(message)
    } finally {
      setIsSending(false)
    }
  }

  if (isLoadingProfile) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-bg px-4 text-text-sub">
        <div className="flex items-center gap-2 text-sm">
          <Loader2 size={16} className="animate-spin" />
          正在打开智能体链接...
        </div>
      </main>
    )
  }

  if (profile === null) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-bg px-4">
        <div className="w-full max-w-md rounded-token-md border border-border bg-surface p-5 text-center shadow-token-sm">
          <TriangleAlert className="mx-auto text-red-500" size={26} />
          <h1 className="mt-3 text-base font-semibold text-text-main">链接不可用</h1>
          <p className="mt-2 text-sm leading-relaxed text-text-sub">{error ?? '这个智能体链接不存在或已被停用。'}</p>
        </div>
      </main>
    )
  }

  return (
    <main className="min-h-screen bg-bg text-text-main">
      <div className="mx-auto flex min-h-screen w-full max-w-4xl flex-col px-4 py-5 sm:px-6">
        <header className="border-b border-border pb-4">
          <div className="flex min-w-0 items-center gap-3">
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-token-md bg-primary/10 text-primary">
              {profile.avatar_url ? <img src={profile.avatar_url} alt="" className="h-11 w-11 rounded-token-md object-cover" /> : <Bot size={20} />}
            </span>
            <div className="min-w-0">
              <h1 className="truncate text-lg font-semibold">{profile.title}</h1>
              <p className="mt-1 line-clamp-2 text-sm leading-relaxed text-text-sub">{profile.description}</p>
            </div>
          </div>
        </header>

        <section className="flex-1 overflow-y-auto py-5">
          <div className="space-y-3">
            {messages.map((message) => (
              <div key={message.id} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div
                  className={`max-w-[84%] rounded-token-md px-4 py-3 text-sm leading-relaxed shadow-token-sm ${
                    message.role === 'user'
                      ? 'bg-primary text-white'
                      : message.status === 'FAILED'
                        ? 'border border-red-200 bg-red-50 text-red-700'
                        : 'border border-border bg-surface text-text-main'
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
                </div>
              </div>
            ))}
          </div>
        </section>

        <form onSubmit={handleSubmit} className="border-t border-border pt-4">
          {error ? <p className="mb-2 text-xs text-red-500">{error}</p> : null}
          <div className="flex items-end gap-2 rounded-token-md border border-border bg-surface p-2 shadow-token-sm">
            <textarea
              className="min-h-10 flex-1 resize-none rounded-token-md bg-transparent px-2 py-2 text-sm leading-relaxed text-text-main placeholder:text-text-muted focus-visible:outline-none"
              placeholder="输入你想问的问题..."
              value={input}
              rows={1}
              onChange={(event) => setInput(event.target.value)}
              disabled={isSending}
            />
            <Button type="submit" size="icon" aria-label="发送" title="发送" disabled={isSending || input.trim().length === 0}>
              {isSending ? <Loader2 size={15} className="animate-spin" /> : <Send size={15} />}
            </Button>
          </div>
        </form>
      </div>
    </main>
  )
}
