import { Blocks, Bot, FileText, PlayCircle, type LucideIcon } from 'lucide-react'

import type { NavItem } from '../types/navigation'

export const NAV_ITEMS: NavItem[] = [
  { label: '智能体', to: '/develop/agents', icon: Bot },
  { label: '运行', to: '/develop/runs', icon: PlayCircle },
  { label: '工具市场', to: '/develop/marketplace', icon: Blocks },
  { label: '日志', to: '/develop/logs', icon: FileText },
]

export const DEFAULT_BREADCRUMB_MAP: Record<string, string> = {
  agents: '智能体',
  develop: '开发端',
  runs: '执行运行',
  marketplace: '工具市场',
  logs: '日志与记录',
}

export type IconType = LucideIcon
