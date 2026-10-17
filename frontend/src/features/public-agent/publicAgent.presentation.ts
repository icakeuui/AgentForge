import type { PublicAgentProfile } from './publicAgent.adapter'

const SYSTEM_PROMPT_MARKERS = /你的目标|回答原则|表达风格|system\s*prompt|系统提示词|核心提示词|禁止[:：]|当用户/i

function safeShortText(value: string): string | null {
  const normalized = value.replace(/\s+/g, ' ').trim()
  if (normalized.length === 0 || normalized.length > 180 || SYSTEM_PROMPT_MARKERS.test(normalized)) return null
  return normalized
}

/** Avoid rendering long or structured system prompts in public discovery UI. */
export function publicAgentSummary(agent: Pick<PublicAgentProfile, 'description' | 'opening_statement'>): string {
  const description = safeShortText(agent.description)
  if (description !== null) return description
  if (agent.description.trim().length === 0) {
    return safeShortText(agent.opening_statement) ?? '公开智能体，可在详情页查看介绍并直接试用。'
  }
  return '公开智能体，可在详情页查看介绍并直接试用。'
}
