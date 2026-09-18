export type ExecutionStatus = 'IDLE' | 'PENDING' | 'RUNNING' | 'SUCCEEDED' | 'FAILED' | 'TERMINATED'
export type PreviewPhase = 'empty' | 'planning' | 'building' | 'booting' | 'ready' | 'failed' | 'deployed'
export type DeploymentStatus = 'IDLE' | 'PENDING' | 'SUCCEEDED' | 'FAILED'

export interface ConversationMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  execution_id: string | null
  status?: ExecutionStatus
  source?: 'chat' | 'opening' | 'activity'
  knowledge_badge?: string | null
}

export interface ExecutionStep {
  step_index: number
  thought?: string | null
  action: {
    tool_id: string
    arguments: Record<string, unknown>
  } | null
  observation: {
    ok: boolean
    content: unknown
    error: Record<string, unknown> | null
  } | null
}

export type ExecutionStepLogPhase =
  | 'intent_classification'
  | 'pre_policy_gate'
  | 'knowledge_retrieval'
  | 'retrieval_policy_gate'
  | 'model_call'
  | 'tool_policy_gate'
  | 'tool_call'
  | 'observation'
  | 'final_answer_policy_gate'
  | 'final_answer'

export interface ExecutionStepLog {
  execution_id: string
  step_index: number
  phase: ExecutionStepLogPhase
  tool_id: string | null
  status: 'success' | 'error'
  payload: Record<string, unknown>
  timestamp: string
}

export interface ExecutionSnapshot {
  execution_id: string
  status: Exclude<ExecutionStatus, 'IDLE'>
  final_answer: string | null
  error_code: string | null
  error_source: string | null
  error_details: Record<string, unknown> | null
  error_message: string | null
  react_steps: ExecutionStep[]
  step_logs: ExecutionStepLog[]
  artifacts?: unknown[]
  termination_reason: string | null
  total_token_usage: number | null
  preview_phase?: PreviewPhase | null
  preview_url?: string | null
  deployment_status?: DeploymentStatus | null
  deployed_url?: string | null
  last_user_input?: string | null
}

export interface ExecutionRuntimeState {
  current_execution_id: string | null
  is_execution_starting: boolean
  status: ExecutionStatus
  final_answer: string | null
  error_code: string | null
  error_source: string | null
  error_details: Record<string, unknown> | null
  error_message: string | null
  react_steps: ExecutionStep[]
  step_logs: ExecutionStepLog[]
  artifacts: unknown[]
  termination_reason: string | null
  total_token_usage: number | null
  preview_phase: PreviewPhase | null
  preview_url: string | null
  deployment_status: DeploymentStatus
  deployed_url: string | null
  last_user_input: string | null
  conversation_messages: ConversationMessage[]
  conversation_messages_hidden: boolean
  conversation_cleared_execution_id: string | null
}

export interface ConversationSession extends ExecutionRuntimeState {
  id: string
  agent_id: string | null
  title: string
  created_at: number
  updated_at: number
}

export interface ExecutionStoreState extends ExecutionRuntimeState {
  conversation_agent_id: string | null
  conversation_sessions: ConversationSession[]
  active_conversation_id: string | null
  startExecution: (agent_id: string, input: string) => void
  updateExecution: (data: ExecutionSnapshot) => void
  markExecutionStoppedByUser: () => void
  finishExecution: () => void
  resetExecution: () => void
  clearConversationMessages: (agent_id?: string | null, opening_statement?: string | null) => void
  setOpeningMessage: (agent_id: string | null, opening_statement: string | null) => void
  createConversationSession: (agent_id?: string | null, opening_statement?: string | null) => string | null
  selectConversationSession: (session_id: string) => void
  deleteConversationSession: (session_id: string, agent_id?: string | null, opening_statement?: string | null) => void
  setPreviewPhase: (phase: PreviewPhase | null) => void
  setPreviewUrl: (url: string | null) => void
  setDeploymentState: (status: DeploymentStatus, deployedUrl?: string | null) => void
  setLastUserInput: (input: string | null) => void
}

export const IDLE_EXECUTION_STATE: ExecutionRuntimeState = {
  current_execution_id: null,
  is_execution_starting: false,
  status: 'IDLE',
  final_answer: null,
  error_code: null,
  error_source: null,
  error_details: null,
  error_message: null,
  react_steps: [],
  step_logs: [],
  artifacts: [],
  termination_reason: null,
  total_token_usage: null,
  preview_phase: null,
  preview_url: null,
  deployment_status: 'IDLE',
  deployed_url: null,
  last_user_input: null,
  conversation_messages: [],
  conversation_messages_hidden: false,
  conversation_cleared_execution_id: null,
}
