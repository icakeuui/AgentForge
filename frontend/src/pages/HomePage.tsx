import { ArrowRight, Blocks, BookOpen, Bot, Compass, ExternalLink, FolderKanban, Sparkles } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { useAgentStore } from '../features/agent/agent.store'
import { useAuthStore } from '../features/auth/auth.store'
import { PlatformShell } from '../components/navigation/PlatformShell'

const destinations = [
  {
    title: '学习中心',
    description: '从平台使用指南开始，逐步学习 Agent、Prompt 与 RAG。',
    note: '指南 · 路径 · 案例',
    action: '开始学习',
    icon: BookOpen,
    tone: 'bg-sky-50 text-sky-700',
    href: '/learn',
  },
  {
    title: '智能体开发',
    description: '配置模型、提示词、工具和知识库，搭建自己的智能体。',
    note: '创建 · 配置 · 调试',
    action: '进入开发端',
    icon: FolderKanban,
    tone: 'bg-primary/10 text-primary',
    href: '/develop/agents',
  },
  {
    title: '智能体广场',
    description: '浏览公开智能体，了解不同场景下的能力和用法。',
    note: '发现 · 浏览 · 试用',
    action: '打开广场',
    icon: Compass,
    tone: 'bg-indigo-50 text-indigo-700',
    href: '/square',
  },
]

export function HomePage() {
  const navigate = useNavigate()
  const authStatus = useAuthStore((state) => state.status)
  const agentCount = useAgentStore((state) => state.agent_list.filter((agent) => !agent.archived).length)
  const isSignedIn = authStatus === 'authenticated'

  return (
    <PlatformShell>
      <main className="min-h-screen px-5 py-6 sm:px-8 sm:py-9 lg:px-10">
        <div className="mx-auto flex w-full max-w-[1400px] flex-col gap-6 lg:gap-8">
          <header className="flex items-center justify-between gap-4">
            <div>
              <p className="text-sm font-medium text-primary">AgentForge 智能体搭建辅助实践平台</p>
              <h1 className="mt-1 text-2xl font-semibold tracking-tight sm:text-3xl">欢迎回来，开始你的智能体实践</h1>
            </div>
            <div className="flex shrink-0 items-center gap-2">
              <Badge variant={isSignedIn ? 'success' : 'neutral'}>{isSignedIn ? '已登录' : '访客模式'}</Badge>
              {!isSignedIn ? <Button type="button" variant="secondary" size="sm" onClick={() => navigate('/login')}>登录</Button> : null}
            </div>
          </header>

          <section className="relative isolate overflow-hidden rounded-token-xl border border-primary/10 bg-gradient-to-br from-white via-white to-blue-50/80 p-6 shadow-token-sm sm:p-8 lg:p-10">
            <div aria-hidden="true" className="pointer-events-none absolute -right-16 -top-28 -z-10 h-80 w-80 rounded-full bg-blue-100/55 blur-3xl" />
            <div className="flex flex-col items-center justify-between gap-7 sm:flex-row sm:gap-5">
              <div className="max-w-2xl">
                <Badge variant="info" className="bg-white/80"><Sparkles size={13} className="mr-1.5" />从学习到实践</Badge>
                <h2 className="mt-5 text-3xl font-semibold tracking-tight text-text-main sm:text-4xl">让每个想法，都能成为智能体</h2>
                <p className="mt-3 max-w-xl text-sm leading-7 text-text-sub sm:text-base">从学习智能体知识，到搭建自己的智能体，再到浏览和体验公开智能体。</p>
                <div className="mt-6 flex flex-wrap gap-3">
                  <Button type="button" onClick={() => navigate('/learn')}>探索学习中心 <ArrowRight size={15} /></Button>
                  <Button type="button" variant="secondary" onClick={() => navigate(isSignedIn ? '/develop/agents' : '/login')}>搭建智能体 <Bot size={15} /></Button>
                </div>
              </div>
              <div className="flex w-full shrink-0 items-center justify-center sm:w-[190px] lg:w-[225px]">
                <img src="/brand/agentforge-logo.png" alt="AgentForge 智能体搭建辅助实践平台" className="h-auto w-36 object-contain drop-shadow-[0_12px_18px_rgba(37,99,235,0.12)] sm:w-44 lg:w-52" />
              </div>
            </div>
          </section>

          <section aria-labelledby="platform-entries">
            <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
              <div>
                <h2 id="platform-entries" className="text-lg font-semibold">你的工作空间</h2>
                <p className="mt-1 text-sm text-text-sub">沿着“学 → 做 → 用”，找到下一步。</p>
              </div>
              {isSignedIn ? <Badge variant="info">{agentCount} 个智能体</Badge> : null}
            </div>
            <div className="grid gap-4 lg:grid-cols-3">
              {destinations.map(({ title, description, note, action, icon: Icon, tone, href }) => {
                const destination = href === '/develop/agents' && !isSignedIn ? '/login' : href
                return (
                  <button
                    key={title}
                    type="button"
                    onClick={() => navigate(destination)}
                    className="group flex min-h-[220px] flex-col rounded-token-lg border border-border bg-surface p-5 text-left shadow-token-sm transition duration-200 hover:-translate-y-0.5 hover:border-primary/25 hover:shadow-token-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 sm:p-6"
                  >
                    <span className={`inline-flex h-11 w-11 items-center justify-center rounded-token-md ${tone}`}><Icon size={20} strokeWidth={1.8} /></span>
                    <h3 className="mt-4 text-lg font-semibold">{title}</h3>
                    <p className="mt-2 max-w-sm flex-1 text-sm leading-6 text-text-sub">{description}</p>
                    <div className="mt-5 flex items-center justify-between border-t border-border/80 pt-4">
                      <span className="text-xs text-text-muted">{note}</span>
                      <span className="inline-flex items-center gap-1.5 text-sm font-semibold text-primary">{action}<ExternalLink size={14} className="transition-transform group-hover:translate-x-0.5" /></span>
                    </div>
                  </button>
                )
              })}
            </div>
          </section>

          <footer className="flex flex-wrap items-center justify-between gap-2 border-t border-border/80 pt-4 text-xs text-text-muted">
            <span className="inline-flex items-center gap-2"><Blocks size={14} className="text-primary" />一个空间，连接学习、搭建与体验</span>
            <span>AgentForge</span>
          </footer>
        </div>
      </main>
    </PlatformShell>
  )
}
