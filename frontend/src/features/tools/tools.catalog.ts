import { Calculator, Search } from 'lucide-react'
import type { ComponentType } from 'react'

export interface BuiltinToolOption {
  id: string
  aliases: string[]
  name: string
  description: string
  icon: ComponentType<{ size?: number; className?: string }>
}

export const BUILTIN_TOOL_OPTIONS: BuiltinToolOption[] = [
  {
    id: 'websearch',
    aliases: ['websearch', 'web_search', 'builtin/websearch', 'builtin/web_search'],
    name: '网页搜索',
    description: '根据用户问题检索公开网页信息，并把标题、链接和摘要返回给模型。',
    icon: Search,
  },
  {
    id: 'calculate',
    aliases: ['calculate', 'caculate', 'builtin/calculate', 'builtin/caculate'],
    name: '运算',
    description: '安全计算基础四则运算和括号表达式，适合金额、比例、数量等确定性计算。',
    icon: Calculator,
  },
]

export function normalizeBuiltinToolId(toolId: string): string {
  const normalized = toolId.trim()
  const option = BUILTIN_TOOL_OPTIONS.find((item) => item.aliases.includes(normalized))
  return option?.id ?? normalized
}

export function getBuiltinToolLabel(toolId: string): string {
  const normalized = normalizeBuiltinToolId(toolId)
  return BUILTIN_TOOL_OPTIONS.find((item) => item.id === normalized)?.name ?? toolId
}
