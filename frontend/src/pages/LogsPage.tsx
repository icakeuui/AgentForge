import { LogConsole } from '../components/console/LogConsole'
import { Alert } from '../components/feedback/Alert'
import { PageContainer } from '../components/layout/PageContainer'
import { PageHeader } from '../components/layout/PageHeader'
import { Badge } from '../components/ui/Badge'
import { Card } from '../components/ui/Card'
import { useExecutionStore } from '../features/execution/execution.store'

const PHASE_LABEL: Record<string, string> = {
  intent_classification: '意图分类',
  pre_policy_gate: '前置策略',
  knowledge_retrieval: '知识库调用',
  retrieval_policy_gate: '检索策略',
  model_call: '模型调用',
  tool_policy_gate: '工具策略',
  tool_call: '工具使用',
  observation: '工具结果',
  final_answer_policy_gate: '答复策略',
  final_answer: '最终答复',
}

function summarizePayload(payload: Record<string, unknown>): string {
  const code = typeof payload.reason_code === 'string' ? payload.reason_code : typeof payload.violation_code === 'string' ? payload.violation_code : null
  const intent = typeof payload.intent_type === 'string' ? payload.intent_type : null
  const retrievalMode = typeof payload.retrieval_mode === 'string' ? payload.retrieval_mode : null
  const matchedCount = typeof payload.matched_count === 'number' ? payload.matched_count : null
  if (intent) return `intent=${intent}`
  if (retrievalMode) return `retrieval_mode=${retrievalMode}`
  if (matchedCount !== null) return `matched_count=${matchedCount}`
  if (code) return code
  return JSON.stringify(payload).slice(0, 160)
}

export function LogsPage() {
  const { current_execution_id, status, step_logs } = useExecutionStore()
  const lines =
    step_logs.length > 0
      ? step_logs.map((log) => ({
          level: log.status === 'error' ? ('error' as const) : ('success' as const),
          message: `[${PHASE_LABEL[log.phase] ?? log.phase}] step=${log.step_index} ${summarizePayload(log.payload)}`,
        }))
      : [{ level: 'info' as const, message: '[信息] 暂无执行日志，发起一次运行后会显示真实阶段记录' }]

  return (
    <PageContainer>
      <PageHeader
        title="日志与记录"
        description="展示最近一次运行的分类、策略、检索、工具与最终答复记录。"
        statusSlot={<Badge variant={status === 'FAILED' ? 'error' : current_execution_id ? 'success' : 'neutral'}>{current_execution_id ? status : '暂无运行'}</Badge>}
      />

      <Alert variant="info" title="执行审计">
        当前页面展示最近一次运行的真实 step logs；更细的 payload 可在 Builder 的运行日志页查看。
      </Alert>

      <Card title="日志控制台">
        <LogConsole lines={lines} />
      </Card>
    </PageContainer>
  )
}
