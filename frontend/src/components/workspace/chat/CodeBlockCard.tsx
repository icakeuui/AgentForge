import { Check, Copy, Plus, Terminal } from 'lucide-react'
import { useState } from 'react'

import { Button } from '../../ui/Button'

interface CodeBlockCardProps {
  code: string
  title?: string
  language?: string
  kind?: 'code' | 'command'
  onAddCommand?: () => void
}

export function CodeBlockCard({ code, title, language, kind = 'code', onAddCommand }: CodeBlockCardProps) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    if (typeof navigator !== 'undefined') {
      await navigator.clipboard.writeText(code)
    }
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="overflow-hidden rounded-token-md border border-border bg-[#0F172A]">
      <div className="flex items-center justify-between border-b border-[#334155] bg-[#1E293B] px-3 py-1.5 text-xs text-[#CBD5E1]">
        <div className="flex min-w-0 items-center gap-2">
          <Terminal size={14} />
          <span className="truncate">{title ?? (kind === 'command' ? '命令' : language ?? '代码')}</span>
        </div>
        <div className="flex items-center gap-1">
          {kind === 'command' && onAddCommand ? (
            <Button
              variant="ghost"
              size="sm"
              className="h-6 px-2 text-[#CBD5E1] hover:bg-[#334155] hover:text-[#F8FAFC]"
              leftIcon={<Plus size={12} />}
              onClick={onAddCommand}
            >
              加入终端
            </Button>
          ) : null}
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6 text-[#CBD5E1] hover:bg-[#334155] hover:text-[#F8FAFC]"
            onClick={handleCopy}
            aria-label="复制代码"
            title="复制代码"
          >
            {copied ? <Check size={12} className="text-[#22C55E]" /> : <Copy size={12} />}
          </Button>
        </div>
      </div>
      <div className="overflow-x-auto p-3 text-xs leading-loose">
        <pre className="text-[#F8FAFC]">
          <code>{code}</code>
        </pre>
      </div>
    </div>
  )
}
