import { Blocks, Bot, Compass, ExternalLink, FolderKanban, Sparkles } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import { Button } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import { useAgentStore } from '../features/agent/agent.store'
import { useAuthStore } from '../features/auth/auth.store'

export function HomePage() {
  const navigate = useNavigate()
  const authStatus = useAuthStore((state) => state.status)
  const agentCount = useAgentStore((state) => state.agent_list.filter((agent) => !agent.archived).length)
  const isSignedIn = authStatus === 'authenticated'

  return (
    <main className="min-h-screen bg-bg text-text-main">
      <div className="mx-auto flex min-h-screen w-full max-w-6xl flex-col px-5 py-5 sm:px-8">
        <header className="flex items-center justify-between gap-4 border-b border-border pb-4">
          <div className="flex min-w-0 items-center gap-3">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-token-md bg-primary text-white shadow-token-sm">
              <Sparkles size={18} />
            </span>
            <div className="min-w-0">
              <h1 className="text-lg font-semibold">AgentForge</h1>
              <p className="truncate text-sm text-text-sub">智能体平台</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant={isSignedIn ? 'success' : 'neutral'}>{isSignedIn ? '已登录' : '访客'}</Badge>
            {!isSignedIn ? (
              <Button type="button" variant="secondary" size="sm" onClick={() => navigate('/login')}>
                登录
              </Button>
            ) : null}
          </div>
        </header>

        <section className="grid flex-1 content-center gap-4 py-8 md:grid-cols-2">
          <button
            type="button"
            className="group flex min-h-[280px] flex-col justify-between rounded-token-lg border border-border bg-surface p-6 text-left shadow-token-sm transition hover:border-primary/50 hover:shadow-token-lg"
            onClick={() => navigate(isSignedIn ? '/develop/agents' : '/login')}
          >
            <div>
              <span className="inline-flex h-11 w-11 items-center justify-center rounded-token-md bg-primary/10 text-primary">
                <FolderKanban size={21} />
              </span>
              <h2 className="mt-5 text-2xl font-semibold tracking-normal">智能体开发</h2>
              <p className="mt-3 max-w-md text-sm leading-6 text-text-sub">配置、调试、知识库、工具、发布。</p>
            </div>
            <div className="mt-6 flex items-center justify-between gap-3">
              <Badge variant="info">{agentCount} 个智能体</Badge>
              <span className="inline-flex items-center gap-2 text-sm font-medium text-primary">
                进入开发端
                <ExternalLink size={15} className="transition group-hover:translate-x-0.5" />
              </span>
            </div>
          </button>

          <button
            type="button"
            className="group flex min-h-[280px] flex-col justify-between rounded-token-lg border border-border bg-surface p-6 text-left shadow-token-sm transition hover:border-primary/50 hover:shadow-token-lg"
            onClick={() => navigate('/square')}
          >
            <div>
              <span className="inline-flex h-11 w-11 items-center justify-center rounded-token-md bg-emerald-50 text-emerald-700">
                <Compass size={21} />
              </span>
              <h2 className="mt-5 text-2xl font-semibold tracking-normal">智能体广场</h2>
              <p className="mt-3 max-w-md text-sm leading-6 text-text-sub">浏览、打开、试用。</p>
            </div>
            <div className="mt-6 flex items-center justify-between gap-3">
              <Badge variant="success">公开试用</Badge>
              <span className="inline-flex items-center gap-2 text-sm font-medium text-primary">
                打开广场
                <Blocks size={15} className="transition group-hover:translate-x-0.5" />
              </span>
            </div>
          </button>
        </section>

        <footer className="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-4 text-xs text-text-muted">
          <span className="inline-flex items-center gap-2">
            <Bot size={14} />
            双轨入口
          </span>
          <span>AgentForge</span>
        </footer>
      </div>
    </main>
  )
}
