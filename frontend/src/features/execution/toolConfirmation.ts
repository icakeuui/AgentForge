import type { ConfirmedToolAction } from './execution.adapter'
import type { ExecutionStepLog } from './execution.types'
import { getBuiltinToolLabel } from '../tools/tools.catalog'

export interface PendingToolConfirmation {
  id: string
  tool_id: string
  tool_label: string
  action_summary: string
  arguments_hash: string
  arguments_summary: string | null
  mode: 'intent' | 'tool_call'
}

function readString(value: unknown): string | null {
  return typeof value === 'string' && value.trim().length > 0 ? value.trim() : null
}

function readRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === 'object' && value !== null ? (value as Record<string, unknown>) : null
}

function prePolicyConfirmation(log: ExecutionStepLog): PendingToolConfirmation | null {
  if (log.phase !== 'pre_policy_gate' || log.payload.requires_user_confirmation !== true) {
    return null
  }
  const blockedTools = Array.isArray(log.payload.blocked_tool_ids) ? log.payload.blocked_tool_ids : []
  const riskMetadata = Array.isArray(log.payload.tool_risk_metadata) ? log.payload.tool_risk_metadata : []
  const candidate = blockedTools
    .map((item) => readRecord(item))
    .filter((item): item is Record<string, unknown> => item !== null)
    .find((item) => {
      const toolId = readString(item.tool_id)
      const risk = riskMetadata
        .map((entry) => readRecord(entry))
        .find((entry) => entry !== null && readString(entry.tool_id) === toolId)
      return risk === undefined || risk === null || risk.requires_confirmation === true
    })
  const toolId = readString(candidate?.tool_id)
  if (toolId === null) {
    return null
  }
  return {
    id: `intent:${log.execution_id}:${toolId}`,
    tool_id: toolId,
    tool_label: getBuiltinToolLabel(toolId),
    action_summary: '允许本轮继续生成具体工具动作',
    arguments_hash: 'intent-confirmed',
    arguments_summary: null,
    mode: 'intent',
  }
}

function toolCallConfirmation(log: ExecutionStepLog): PendingToolConfirmation | null {
  if (log.phase !== 'tool_policy_gate' || log.status !== 'error') {
    return null
  }
  const reasonCode = readString(log.payload.reason_code)
  if (reasonCode !== 'TOOL_CONFIRMATION_REQUIRED') {
    return null
  }
  const toolId = readString(log.tool_id) ?? readString(log.payload.resolved_tool_id) ?? readString(readRecord(log.payload.input_summary)?.resolved_tool_id)
  const argumentsHash = readString(log.payload.arguments_hash)
  if (toolId === null || argumentsHash === null) {
    return null
  }
  const argumentsSummary = readString(log.payload.arguments_summary)
  return {
    id: `tool:${log.execution_id}:${log.step_index}:${toolId}:${argumentsHash}`,
    tool_id: toolId,
    tool_label: getBuiltinToolLabel(toolId),
    action_summary: '确认执行该工具调用',
    arguments_hash: argumentsHash,
    arguments_summary: argumentsSummary,
    mode: 'tool_call',
  }
}

export function findPendingToolConfirmation(stepLogs: ExecutionStepLog[]): PendingToolConfirmation | null {
  for (let index = stepLogs.length - 1; index >= 0; index -= 1) {
    const toolCall = toolCallConfirmation(stepLogs[index])
    if (toolCall !== null) {
      return toolCall
    }
  }
  for (let index = stepLogs.length - 1; index >= 0; index -= 1) {
    const prePolicy = prePolicyConfirmation(stepLogs[index])
    if (prePolicy !== null) {
      return prePolicy
    }
  }
  return null
}

export function toConfirmedToolAction(confirmation: PendingToolConfirmation): ConfirmedToolAction {
  return {
    tool_id: confirmation.tool_id,
    action_summary: confirmation.action_summary,
    arguments_hash: confirmation.arguments_hash,
    confirmed_at: new Date().toISOString(),
  }
}
