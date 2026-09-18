import { Check, Copy } from 'lucide-react'
import type { ReactNode } from 'react'
import { useState } from 'react'
import ReactMarkdown, { type Components } from 'react-markdown'
import remarkGfm from 'remark-gfm'

import { ThoughtCollapsibleBlock } from '../copilot/timeline/ThoughtCollapsibleBlock'
import { useWorkspaceTabsStore } from '../../../features/ui-shell/workspaceTabs.store'
import { cn } from '../../../lib/cn'
import { CodeBlockCard } from '../chat/CodeBlockCard'

interface RichContentRendererProps {
  content: string
  compact?: boolean
  showTextCopy?: boolean
}

type RichBlock =
  | { type: 'text'; text: string }
  | { type: 'code'; language: string | null; code: string }
  | { type: 'think'; text: string }

const COMMAND_LANGUAGES = new Set(['bash', 'sh', 'shell', 'zsh', 'terminal', 'console'])

function splitBlocks(content: string): RichBlock[] {
  const blocks: RichBlock[] = []
  const blockPattern = /```([^\n`]*)?\n?([\s\S]*?)```|<think>([\s\S]*?)<\/think>/g
  let lastIndex = 0
  let match: RegExpExecArray | null

  while ((match = blockPattern.exec(content)) !== null) {
    if (match.index > lastIndex) {
      blocks.push({ type: 'text', text: content.slice(lastIndex, match.index) })
    }
    if (match[3] !== undefined) {
      blocks.push({ type: 'think', text: match[3].trim() })
    } else {
      const language = match[1]?.trim() || null
      blocks.push({ type: 'code', language, code: match[2].replace(/\n$/, '') })
    }
    lastIndex = blockPattern.lastIndex
  }

  if (lastIndex < content.length) {
    blocks.push({ type: 'text', text: content.slice(lastIndex) })
  }

  return blocks.filter((block) => {
    if (block.type === 'text') {
      return block.text.trim().length > 0
    }
    if (block.type === 'think') {
      return block.text.length > 0
    }
    return block.code.length > 0
  })
}

function isCommandBlock(language: string | null, code: string): boolean {
  const normalized = language?.trim().toLowerCase() ?? ''
  if (COMMAND_LANGUAGES.has(normalized)) {
    return true
  }
  const firstLine = code.trimStart().split('\n')[0] ?? ''
  return firstLine.startsWith('$ ') || firstLine.startsWith('npm ') || firstLine.startsWith('pnpm ') || firstLine.startsWith('yarn ')
}

function normalizeUrl(raw: string): string {
  return raw.replace(/[.,;:!?]+$/, '')
}

function titleFromUrl(url: string): string {
  try {
    return new URL(url).hostname
  } catch {
    return url
  }
}

async function copyToClipboard(text: string): Promise<boolean> {
  if (typeof navigator === 'undefined' || text.trim().length === 0) {
    return false
  }
  await navigator.clipboard.writeText(text)
  return true
}

function CopyActionButton({ text, label }: { text: string; label: string }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    const success = await copyToClipboard(text)
    if (!success) {
      return
    }
    setCopied(true)
    setTimeout(() => setCopied(false), 1600)
  }

  return (
    <button
      type="button"
      className="inline-flex h-7 w-7 items-center justify-center rounded-token-md border border-border bg-surface text-text-sub transition-colors duration-200 hover:bg-bg-soft hover:text-text-main"
      aria-label={label}
      title={label}
      onClick={() => void handleCopy()}
    >
      {copied ? <Check size={14} className="text-success" /> : <Copy size={14} />}
    </button>
  )
}

function MarkdownLink({ href, children }: { href?: string; children: ReactNode }) {
  const selectBrowserLink = useWorkspaceTabsStore((state) => state.selectBrowserLink)

  if (!href) {
    return <>{children}</>
  }

  const url = normalizeUrl(href)
  const isBrowserUrl = /^https?:\/\//i.test(url)
  if (!isBrowserUrl) {
    return <span className="font-medium text-primary">{children}</span>
  }

  return (
    <button
      type="button"
      className="font-medium text-primary underline-offset-2 hover:underline"
      onClick={() => selectBrowserLink({ url, title: titleFromUrl(url), source: 'final_answer' })}
    >
      {children}
    </button>
  )
}

function MarkdownContent({ text, compact, showTextCopy }: { text: string; compact: boolean; showTextCopy: boolean }) {
  const addTerminalCommand = useWorkspaceTabsStore((state) => state.addTerminalCommand)
  const components: Components = {
    h1: ({ children }) => <h1 className={cn('mt-3 text-xl font-semibold leading-snug text-text-main first:mt-0', compact && 'text-base')}>{children}</h1>,
    h2: ({ children }) => <h2 className={cn('mt-3 text-lg font-semibold leading-snug text-text-main first:mt-0', compact && 'text-sm')}>{children}</h2>,
    h3: ({ children }) => <h3 className="mt-3 text-base font-semibold leading-snug text-text-main first:mt-0">{children}</h3>,
    p: ({ children }) => <p className="my-2 break-words first:mt-0 last:mb-0">{children}</p>,
    strong: ({ children }) => <strong className="font-semibold text-text-main">{children}</strong>,
    em: ({ children }) => <em className="italic text-text-main">{children}</em>,
    del: ({ children }) => <del className="text-text-muted">{children}</del>,
    a: ({ href, children }) => <MarkdownLink href={href}>{children}</MarkdownLink>,
    ul: ({ children }) => <ul className="my-2 list-disc space-y-1 pl-5">{children}</ul>,
    ol: ({ children }) => <ol className="my-2 list-decimal space-y-1 pl-5">{children}</ol>,
    li: ({ children }) => <li className="pl-1 marker:text-text-muted">{children}</li>,
    input: ({ type, checked }) =>
      type === 'checkbox' ? (
        <input type="checkbox" checked={checked} readOnly className="mr-2 h-3.5 w-3.5 rounded border-border align-[-2px] accent-primary" />
      ) : null,
    blockquote: ({ children }) => <blockquote className="my-3 border-l-4 border-border pl-3 text-text-sub">{children}</blockquote>,
    hr: () => <hr className="my-4 border-border" />,
    code: ({ className, children }) => {
      const code = String(children).replace(/\n$/, '')
      const language = /language-(\w+)/.exec(className ?? '')?.[1]
      if (code.includes('\n')) {
        const command = isCommandBlock(language ?? null, code)
        return (
          <CodeBlockCard
            code={code}
            language={language}
            kind={command ? 'command' : 'code'}
            title={command ? '命令' : language ?? '代码'}
            onAddCommand={command ? () => addTerminalCommand({ command: code, title: language ?? '命令', source: 'final_answer' }) : undefined}
          />
        )
      }
      return <code className="rounded-token-sm bg-bg-soft px-1 py-0.5 font-mono text-[0.92em] text-text-main">{children}</code>
    },
    table: ({ children }) => (
      <div className="my-3 max-w-full overflow-x-auto rounded-token-md border border-border">
        <table className="min-w-full border-collapse bg-surface text-left text-xs">{children}</table>
      </div>
    ),
    thead: ({ children }) => <thead className="bg-bg-soft text-text-main">{children}</thead>,
    tbody: ({ children }) => <tbody className="divide-y divide-border">{children}</tbody>,
    tr: ({ children }) => <tr className="divide-x divide-border align-top">{children}</tr>,
    th: ({ children }) => <th className="whitespace-nowrap px-3 py-2 font-semibold text-text-main">{children}</th>,
    td: ({ children }) => <td className="min-w-32 px-3 py-2 leading-relaxed text-text-sub">{children}</td>,
  }

  return (
    <div className="space-y-1">
      {showTextCopy ? (
        <div className="flex justify-end">
          <CopyActionButton text={text.trim()} label="复制正文" />
        </div>
      ) : null}
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {text.trim()}
      </ReactMarkdown>
    </div>
  )
}

export function RichContentRenderer({ content, compact = false, showTextCopy = true }: RichContentRendererProps) {
  const addTerminalCommand = useWorkspaceTabsStore((state) => state.addTerminalCommand)
  const blocks = splitBlocks(content)

  return (
    <div className={cn('space-y-3 text-sm leading-relaxed text-text-main', compact && 'space-y-2 text-xs')}>
      {blocks.map((block, index) => {
        if (block.type === 'think') {
          return (
            <ThoughtCollapsibleBlock
              key={`think-${index}`}
              thought={block.text}
              title="模型思考"
              compact={compact}
            />
          )
        }

        if (block.type === 'code') {
          const command = isCommandBlock(block.language, block.code)
          return (
            <CodeBlockCard
              key={`code-${index}`}
              code={block.code}
              language={block.language ?? undefined}
              kind={command ? 'command' : 'code'}
              title={command ? '命令' : block.language ?? '代码'}
              onAddCommand={command ? () => addTerminalCommand({ command: block.code, title: block.language ?? '命令', source: 'final_answer' }) : undefined}
            />
          )
        }

        return <MarkdownContent key={`text-${index}`} text={block.text} compact={compact} showTextCopy={showTextCopy} />
      })}
    </div>
  )
}
