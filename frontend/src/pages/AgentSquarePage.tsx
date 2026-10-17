import { ArrowRight, Bot, ExternalLink, Loader2, Search, Sparkles } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { PlatformShell } from '../components/navigation/PlatformShell'
import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { Input } from '../components/ui/Input'
import { normalizeApiError } from '../lib/api/error'
import { publicAgentAdapter, type PublicAgentSquareItem } from '../features/public-agent/publicAgent.adapter'
import { publicAgentSummary } from '../features/public-agent/publicAgent.presentation'

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
      [item.title, publicAgentSummary(item)].some((value) => value.toLowerCase().includes(normalized)),
    )
  }, [items, query])

  return (
    <PlatformShell>
      <main className="min-h-screen bg-bg/70 text-text-main">
        <div className="mx-auto w-full max-w-[1440px] px-5 py-7 sm:px-8 lg:px-10 lg:py-9">
          <header className="rounded-token-lg border border-primary/10 bg-gradient-to-br from-blue-50/90 via-surface to-surface px-5 py-6 shadow-token-sm sm:px-7 sm:py-7">
            <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-end">
              <div className="max-w-2xl">
                <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-primary/10 bg-surface/80 px-3 py-1 text-xs font-medium text-primary">
                  <Sparkles size={14} />
                  发现 · 浏览 · 试用
                </div>
                <h1 className="text-2xl font-bold tracking-tight text-text-main sm:text-3xl">智能体广场</h1>
                <p className="mt-2 text-sm leading-6 text-text-sub sm:text-base">
                  发现不同场景下的智能体，快速了解能力并开始试用。
                </p>
              </div>
              <div className="w-full lg:max-w-md">
                <label htmlFor="square-search" className="mb-1.5 block text-xs font-medium text-text-sub">搜索公开智能体</label>
                <div className="relative">
                  <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
                  <Input
                    id="square-search"
                    className="h-11 rounded-token-md bg-surface pl-10 shadow-token-sm"
                    placeholder="搜索名称、简介或开场白"
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                  />
                </div>
              </div>
            </div>
          </header>

          <section className="mt-7" aria-label="公开智能体列表">
            <div className="mb-4 flex flex-wrap items-end justify-between gap-2">
              <div>
                <h2 className="text-lg font-semibold tracking-tight text-text-main">探索智能体</h2>
                <p className="mt-1 text-sm text-text-muted">查看公开简介，选择一个智能体进入试用。</p>
              </div>
              {!isLoading && !error ? (
                <Badge variant="neutral">{query.trim() ? `${visibleItems.length} 个匹配结果` : `${items.length} 个公开智能体`}</Badge>
              ) : null}
            </div>

            {isLoading ? (
              <div className="flex min-h-[280px] items-center justify-center rounded-token-lg border border-border bg-surface text-sm text-text-sub shadow-token-sm">
                <Loader2 size={16} className="mr-2 animate-spin text-primary" />
                正在加载公开智能体...
              </div>
            ) : error ? (
              <div className="rounded-token-lg border border-error/20 bg-error-soft px-5 py-4 text-sm text-error" role="alert">
                {error}
              </div>
            ) : visibleItems.length === 0 ? (
              <Card className="flex min-h-[280px] flex-col items-center justify-center border-dashed px-5 text-center shadow-none">
                <span className="flex h-12 w-12 items-center justify-center rounded-token-md bg-primary/10 text-primary">
                  <Search size={21} />
                </span>
                <h3 className="mt-4 text-base font-semibold text-text-main">{query.trim() ? '暂时没有匹配的智能体' : '广场暂时还没有公开智能体'}</h3>
                <p className="mt-1 text-sm text-text-muted">{query.trim() ? '换个关键词试试。' : '公开发布的智能体会显示在这里。'}</p>
              </Card>
            ) : (
              <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
                {visibleItems.map((item) => (
                  <Card
                    key={item.slug}
                    className="group flex min-h-[270px] flex-col p-5 shadow-token-sm transition-all duration-200 hover:-translate-y-0.5 hover:border-primary/25 hover:shadow-token-lg"
                  >
                    <div className="flex h-full flex-1 flex-col">
                    <div className="flex items-start justify-between gap-3">
                      <span className="flex h-12 w-12 shrink-0 items-center justify-center overflow-hidden rounded-token-md bg-primary/10 text-primary ring-1 ring-primary/10">
                        {item.avatar_url ? <img src={item.avatar_url} alt="" className="h-full w-full object-cover" /> : <Bot size={21} />}
                      </span>
                      <Badge variant="success">公开 · 可试用</Badge>
                    </div>
                    <h3 className="mt-4 line-clamp-1 text-base font-semibold tracking-tight text-text-main">{item.title}</h3>
                    <p className="mt-2 line-clamp-3 min-h-[4.5rem] text-sm leading-6 text-text-sub">
                      {publicAgentSummary(item)}
                    </p>
                    <div className="mt-auto flex flex-wrap items-center gap-2 border-t border-border/70 pt-4">
                      <Button
                        type="button"
                        variant="secondary"
                        size="sm"
                        leftIcon={<ExternalLink size={14} />}
                        onClick={() => navigate(`/p/${item.slug}`)}
                      >
                        查看详情
                      </Button>
                      <Button
                        type="button"
                        size="sm"
                        leftIcon={<ArrowRight size={14} />}
                        onClick={() => navigate(`/p/${item.slug}`)}
                      >
                        立即试用
                      </Button>
                    </div>
                    </div>
                  </Card>
                ))}
              </div>
            )}
          </section>
        </div>
      </main>
    </PlatformShell>
  )
}
