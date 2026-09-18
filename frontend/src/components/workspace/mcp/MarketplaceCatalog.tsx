import { ExternalLink, Plug, RefreshCcw } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'

import { marketplaceAdapter, type MarketplaceExtension } from '../../../features/marketplace/marketplace.adapter'
import { normalizeApiError } from '../../../lib/api/error'
import { Badge } from '../../ui/Badge'
import { Button } from '../../ui/Button'

interface MarketplaceCatalogProps {
  compact?: boolean
}

export function MarketplaceCatalog({ compact = false }: MarketplaceCatalogProps) {
  const [extensions, setExtensions] = useState<MarketplaceExtension[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const loadExtensions = useCallback(async () => {
    setIsLoading(true)
    setErrorMessage(null)
    try {
      const nextExtensions = await marketplaceAdapter.fetchExtensions()
      setExtensions(nextExtensions)
    } catch (error) {
      setErrorMessage(normalizeApiError(error).message)
      setExtensions([])
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    let cancelled = false

    marketplaceAdapter
      .fetchExtensions()
      .then((nextExtensions) => {
        if (cancelled) {
          return
        }
        setExtensions(nextExtensions)
        setErrorMessage(null)
      })
      .catch((error: unknown) => {
        if (cancelled) {
          return
        }
        setErrorMessage(normalizeApiError(error).message)
        setExtensions([])
      })
      .finally(() => {
        if (cancelled) {
          return
        }
        setIsLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [])

  if (isLoading) {
    return (
      <div className="flex h-full min-h-48 items-center justify-center rounded-token-lg border border-dashed border-border bg-surface text-sm text-text-muted">
        正在加载扩展目录…
      </div>
    )
  }

  if (errorMessage !== null) {
    return (
      <div className="rounded-token-lg border border-error bg-error-soft p-4 text-sm text-error">
        <div className="font-semibold">扩展目录加载失败</div>
        <p className="mt-1 text-xs leading-relaxed">{errorMessage}</p>
        <Button variant="secondary" size="sm" className="mt-3" leftIcon={<RefreshCcw size={13} />} onClick={loadExtensions}>
          重试
        </Button>
      </div>
    )
  }

  if (extensions.length === 0) {
    return (
      <div className="flex h-full min-h-48 items-center justify-center rounded-token-lg border border-dashed border-border bg-surface text-sm text-text-muted">
        未加载到扩展
      </div>
    )
  }

  return (
    <div className={compact ? 'space-y-3' : 'grid gap-3 md:grid-cols-2 xl:grid-cols-3'}>
      {extensions.map((extension) => (
        <article key={extension.id} className="rounded-token-lg border border-border bg-surface p-4 shadow-token-sm">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-token-md bg-primary/10 text-primary">
                  <Plug size={15} />
                </div>
                <div className="min-w-0">
                  <h3 className="truncate text-sm font-semibold text-text-main">{extension.name}</h3>
                  <p className="truncate font-mono text-[11px] text-text-muted">{extension.id}</p>
                </div>
              </div>
            </div>
            {extension.is_official ? <Badge variant="info">官方</Badge> : null}
          </div>
          {extension.description ? (
            <p className="mt-3 line-clamp-3 text-xs leading-relaxed text-text-sub">{extension.description}</p>
          ) : null}
          <div className="mt-3 flex flex-wrap gap-1.5">
            <Badge variant="neutral" className="text-[11px]">
              {extension.tool_type}
            </Badge>
            {extension.categories.slice(0, 3).map((category) => (
              <Badge key={category} variant="neutral" className="text-[11px]">
                {category}
              </Badge>
            ))}
          </div>
          <div className="mt-4 flex items-center justify-between gap-2 border-t border-border pt-3">
            <span className="text-[11px] text-text-muted">
              {extension.config_fields.length > 0 ? `${extension.config_fields.length} 个配置项` : '无需配置'}
            </span>
            <div className="flex items-center gap-1">
              {extension.homepage ? (
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7"
                  aria-label={`打开 ${extension.name}`}
                  title={`打开 ${extension.name}`}
                  onClick={() => window.open(extension.homepage ?? '', '_blank', 'noopener,noreferrer')}
                >
                  <ExternalLink size={13} />
                </Button>
              ) : null}
              <Button variant="secondary" size="sm" disabled>
                安装需用户上下文
              </Button>
            </div>
          </div>
        </article>
      ))}
    </div>
  )
}
