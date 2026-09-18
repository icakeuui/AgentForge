import { ArrowLeft, Bot, ExternalLink, Loader2, Search } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { Button } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import { Input } from '../components/ui/Input'
import { normalizeApiError } from '../lib/api/error'
import { publicAgentAdapter, type PublicAgentSquareItem } from '../features/public-agent/publicAgent.adapter'

export function AgentSquarePage() {
  const navigate = useNavigate()
  const [items, setItems] = useState<PublicAgentSquareItem[]>([])
  const [query, setQuery] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setIsLoading(true)
    setError(null)
    publicAgentAdapter
      .fetchPublicSquare()
      .then((nextItems) => {
        if (!cancelled) setItems(nextItems)
      })
      .catch((err) => {
        if (!cancelled) setError(normalizeApiError(err).message)
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [])

  const visibleItems = useMemo(() => {
    const normalized = query.trim().toLowerCase()
    if (!normalized) return items
    return items.filter((item) =>
      [item.title, item.description, item.opening_statement].some((value) => value.toLowerCase().includes(normalized)),
    )
  }, [items, query])

  return (
    <main className="min-h-screen bg-bg text-text-main">
      <div className="mx-auto w-full max-w-6xl px-5 py-5 sm:px-8">
        <header className="flex flex-wrap items-center justify-between gap-3 border-b border-border pb-4">
          <div className="flex min-w-0 items-center gap-3">
            <Button type="button" variant="ghost" size="icon" aria-label="返回主界面" title="返回主界面" onClick={() => navigate('/')}>
              <ArrowLeft size={16} />
            </Button>
            <div className="min-w-0">
              <h1 className="text-lg font-semibold">智能体广场</h1>
              <p className="truncate text-sm text-text-sub">{items.length} 个已发布智能体</p>
            </div>
          </div>
          <div className="w-full sm:w-72">
            <Input id="square-search" placeholder="搜索智能体" value={query} onChange={(event) => setQuery(event.target.value)} />
          </div>
        </header>

        {isLoading ? (
          <div className="flex min-h-[420px] items-center justify-center text-sm text-text-sub">
            <Loader2 size={16} className="mr-2 animate-spin" />
            正在加载广场...
          </div>
        ) : error ? (
          <div className="mt-6 rounded-token-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
        ) : visibleItems.length === 0 ? (
          <div className="flex min-h-[420px] flex-col items-center justify-center rounded-token-md border border-dashed border-border bg-surface px-4 text-center">
            <Search size={24} className="text-text-muted" />
            <h2 className="mt-3 text-sm font-semibold text-text-main">{query.trim() ? '没有匹配的智能体' : '暂无已发布智能体'}</h2>
          </div>
        ) : (
          <section className="grid gap-4 py-6 md:grid-cols-2 xl:grid-cols-3">
            {visibleItems.map((item) => (
              <button
                type="button"
                key={item.slug}
                className="group flex min-h-[220px] flex-col justify-between rounded-token-md border border-border bg-surface p-4 text-left shadow-token-sm transition hover:border-primary/50 hover:shadow-token-lg"
                onClick={() => navigate(`/p/${item.slug}`)}
              >
                <div>
                  <div className="flex items-start justify-between gap-3">
                    <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-token-md bg-primary/10 text-primary">
                      {item.avatar_url ? <img src={item.avatar_url} alt="" className="h-10 w-10 rounded-token-md object-cover" /> : <Bot size={18} />}
                    </span>
                    <Badge variant="success">可试用</Badge>
                  </div>
                  <h2 className="mt-4 line-clamp-1 text-base font-semibold text-text-main">{item.title}</h2>
                  <p className="mt-2 line-clamp-3 text-sm leading-6 text-text-sub">{item.description || item.opening_statement}</p>
                </div>
                <span className="mt-5 inline-flex items-center gap-2 text-sm font-medium text-primary">
                  打开展示端
                  <ExternalLink size={14} className="transition group-hover:translate-x-0.5" />
                </span>
              </button>
            ))}
          </section>
        )}
      </div>
    </main>
  )
}
