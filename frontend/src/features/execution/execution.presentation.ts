import type { ExecutionStatus, ExecutionStepLog } from './execution.types'

export interface LiveExecutionStage {
  label: string
  description: string
}

export function getLiveExecutionStage(status: ExecutionStatus, stepLogs: ExecutionStepLog[]): LiveExecutionStage | null {
  if (status !== 'PENDING' && status !== 'RUNNING') {
    return null
  }

  const latest = stepLogs[stepLogs.length - 1] ?? null
  if (latest === null) {
    return {
      label: '正在思考中',
      description: '已收到你的消息，正在整理上下文、历史对话和可用能力。',
    }
  }

  if (latest.phase === 'intent_classification') {
    return {
      label: '识别意图中',
      description: '正在判断本轮是否需要知识库、工具或用户确认。',
    }
  }
  if (latest.phase === 'pre_policy_gate') {
    return {
      label: '应用策略中',
      description: '正在根据意图收窄知识库检索方式和本轮可用工具。',
    }
  }
  if (latest.phase === 'knowledge_retrieval') {
    return {
      label: '查找知识库中',
      description: '正在根据你的问题检索候选知识片段，后续会判断相关性再决定是否使用。',
    }
  }
  if (latest.phase === 'retrieval_policy_gate') {
    return {
      label: '校验证据中',
      description: '正在判断检索结果是否足以支撑回答。',
    }
  }
  if (latest.phase === 'model_call') {
    return {
      label: '思考中',
      description: '正在调用模型分析问题并决定下一步动作。',
    }
  }
  if (latest.phase === 'tool_policy_gate') {
    return {
      label: '校验工具策略中',
      description: '正在检查工具调用是否符合绑定、风险和确认要求。',
    }
  }
  if (latest.phase === 'tool_call') {
    return {
      label: '调用工具中',
      description: '模型已经决定调用工具，正在等待工具执行。',
    }
  }
  if (latest.phase === 'observation') {
    return {
      label: '处理工具结果中',
      description: '正在读取工具返回结果并继续推理。',
    }
  }
  if (latest.phase === 'final_answer_policy_gate') {
    return {
      label: '校验最终答复中',
      description: '正在确认最终答复满足证据引用和工具声明约束。',
    }
  }
  return {
    label: '整理回答中',
    description: '正在生成最终答复。',
  }
}

export function getAssistantPlaceholder(status: ExecutionStatus, stepLogs: ExecutionStepLog[]): string {
  const stage = getLiveExecutionStage(status, stepLogs)
  if (stage !== null) {
    return `${stage.label}，请稍候。`
  }
  return '模型正在思考和组织回复，请稍候。'
}
