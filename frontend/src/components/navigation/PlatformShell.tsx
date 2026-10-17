import { BookOpen, Bot, Compass, Home, Settings } from 'lucide-react'
import type { ReactNode } from 'react'
import { NavLink } from 'react-router-dom'

import { cn } from '../../lib/cn'

const platformLinks = [
  { label: '首页', to: '/', icon: Home, end: true },
  { label: '学习中心', to: '/learn', icon: BookOpen },
  { label: '智能体开发', to: '/develop/agents', icon: Bot },
  { label: '智能体广场', to: '/square', icon: Compass },
  { label: '设置', to: '/develop/profile', icon: Settings },
]

function BrandMark({ className }: { className?: string }) {
  return (
    <span className={cn('relative inline-flex h-9 w-12 shrink-0 overflow-hidden', className)} aria-hidden="true">
      <img src="/brand/agentforge-logo.png" alt="" className="absolute left-[-1px] top-0 h-[58px] w-[58px] max-w-none object-contain" />
    </span>
  )
}

function PlatformNav({ mobile = false }: { mobile?: boolean }) {
  return (
    <nav aria-label="平台导航" className={mobile ? 'platform-nav-scroll flex gap-1 overflow-x-auto px-4 pb-3' : 'space-y-1 px-3'}>
      {platformLinks.map(({ label, to, icon: Icon, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          className={({ isActive }) => cn(
            'group flex shrink-0 items-center gap-3 rounded-token-md text-sm font-medium transition-colors duration-150',
            mobile ? 'px-3 py-2' : 'px-3 py-2.5',
            isActive
              ? 'bg-primary/10 text-primary'
              : 'text-text-sub hover:bg-bg-soft hover:text-text-main',
          )}
        >
          <Icon size={17} strokeWidth={1.8} />
          <span>{label}</span>
        </NavLink>
      ))}
    </nav>
  )
}

export function PlatformShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen overflow-x-hidden bg-bg text-text-main md:flex">
      <aside data-platform-sidebar="true" className="sticky top-0 hidden h-screen w-[238px] shrink-0 flex-col border-r border-border/80 bg-surface/95 py-5 md:flex">
        <NavLink to="/" aria-label="AgentForge 首页" className="mb-7 flex items-center gap-2 px-4">
          <BrandMark />
          <span className="text-[17px] font-bold tracking-[-0.04em] text-text-main">AgentForge</span>
        </NavLink>
        <p className="mb-3 px-5 text-[11px] font-semibold uppercase tracking-[0.12em] text-text-muted">工作空间</p>
        <PlatformNav />
        <div className="mt-auto px-4 pb-1">
          <div className="rounded-token-md border border-primary/10 bg-gradient-to-br from-blue-50 to-white p-3.5">
            <p className="text-xs font-semibold text-primary">学 · 做 · 用</p>
            <p className="mt-1 text-xs leading-5 text-text-muted">先学习，再搭建，最后浏览和体验</p>
          </div>
        </div>
      </aside>

      <div className="flex min-h-screen min-w-0 flex-1 flex-col">
        <div className="border-b border-border/80 bg-surface/95 md:hidden">
          <NavLink to="/" aria-label="AgentForge 首页" className="flex items-center gap-2 px-4 py-3">
            <BrandMark className="h-9 w-12" />
            <span className="text-base font-bold tracking-[-0.04em]">AgentForge</span>
          </NavLink>
          <PlatformNav mobile />
        </div>
        <div className="min-w-0 flex-1">{children}</div>
      </div>
    </div>
  )
}
