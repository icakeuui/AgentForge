import { ExternalLink, Globe } from 'lucide-react'

import { useWorkspaceTabsStore } from '../../../features/ui-shell/workspaceTabs.store'
import { Button } from '../../ui/Button'

function domainOf(url: string): string {
  try {
    return new URL(url).hostname
  } catch {
    return url
  }
}

export function BrowserTab() {
  const links = useWorkspaceTabsStore((state) => state.browser.links)
  const activeUrl = useWorkspaceTabsStore((state) => state.browser.activeUrl)
  const selectBrowserLink = useWorkspaceTabsStore((state) => state.selectBrowserLink)

  if (links.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center rounded-token-lg border border-dashed border-border bg-surface p-6 text-center">
        <Globe size={34} className="mb-3 text-border" />
        <p className="text-sm font-medium text-text-main">当前为链接预览模式（无嵌入浏览器）</p>
        <p className="mt-1 max-w-md text-xs leading-relaxed text-text-muted">
          右侧检索来源或最终答复里的链接会进入这里；打开操作始终交给外部浏览器。
        </p>
      </div>
    )
  }

  return (
    <div className="h-full overflow-auto rounded-token-lg border border-border bg-surface p-4 shadow-token-sm">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-text-main">链接预览</h2>
        <span className="text-xs text-text-muted">{links.length} 条来源</span>
      </div>
      <div className="space-y-3">
        {links.map((link) => {
          const isActive = link.url === activeUrl
          return (
            <article
              key={link.id}
              className={`rounded-token-md border p-3 transition-colors ${
                isActive ? 'border-primary bg-info-soft' : 'border-border bg-bg-soft/50'
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <button
                  type="button"
                  onClick={() => selectBrowserLink(link)}
                  className="min-w-0 text-left"
                >
                  <h3 className="truncate text-sm font-semibold text-text-main">{link.title}</h3>
                  <p className="mt-1 truncate text-xs text-primary">{domainOf(link.url)}</p>
                </button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7 shrink-0"
                  aria-label={`open ${link.title}`}
                  onClick={() => window.open(link.url, '_blank', 'noopener,noreferrer')}
                >
                  <ExternalLink size={14} />
                </Button>
              </div>
              {link.snippet ? <p className="mt-2 text-xs leading-relaxed text-text-sub">{link.snippet}</p> : null}
              {link.source ? <p className="mt-2 text-[11px] text-text-muted">来源：{link.source}</p> : null}
            </article>
          )
        })}
      </div>
    </div>
  )
}
