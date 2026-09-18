import { ExternalLink, Globe } from 'lucide-react'

import type { BrowserLinkItem } from '../../../../features/ui-shell/workspaceTabs.types'
import { Button } from '../../../ui/Button'

interface SearchNodeProps {
  links: BrowserLinkItem[]
  onOpenLink: (link: BrowserLinkItem) => void
}

function host(url: string): string {
  try {
    return new URL(url).hostname
  } catch {
    return url
  }
}

export function SearchNode({ links, onOpenLink }: SearchNodeProps) {
  if (links.length === 0) {
    return null
  }

  return (
    <div className="rounded-token-md border border-border bg-surface p-3">
      <div className="mb-2 flex items-center gap-2 text-xs font-semibold text-text-main">
        <Globe size={14} className="text-text-muted" />
        检索来源
      </div>
      <div className="space-y-2">
        {links.slice(0, 4).map((link) => (
          <div key={link.id} className="rounded-token-sm border border-border bg-bg-soft/50 p-2">
            <button type="button" className="block w-full text-left" onClick={() => onOpenLink(link)}>
              <p className="truncate text-xs font-medium text-text-main">{link.title}</p>
              <p className="mt-0.5 truncate text-[11px] text-primary">{host(link.url)}</p>
            </button>
            {link.snippet ? <p className="mt-1 line-clamp-2 text-[11px] text-text-sub">{link.snippet}</p> : null}
            <div className="mt-1.5 flex justify-end">
              <Button
                size="sm"
                variant="ghost"
                className="h-6 px-2 text-[11px]"
                leftIcon={<ExternalLink size={11} />}
                onClick={() => window.open(link.url, '_blank', 'noopener,noreferrer')}
              >
                外部打开
              </Button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
