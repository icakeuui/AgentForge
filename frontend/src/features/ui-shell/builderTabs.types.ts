export type BuilderTabType =
  | 'preview'
  | 'new_tab'
  | 'agent_config'
  | 'skills'
  | 'knowledge'
  | 'run_logs'
  | 'workflow'
  | 'connector'
  | 'env_vars'
  | 'database'
  | 'object_storage'
  | 'versions'
  | 'analytics'
  | 'cloud_terminal'
  | 'cloud_editor'
  | 'version_control'
  | 'debug_console'

export type BuilderTabStatus = 'idle' | 'loading' | 'ready' | 'dirty' | 'error'

export interface BuilderTabState {
  status: BuilderTabStatus
  message?: string | null
}

export interface BuilderTab {
  id: string
  type: BuilderTabType
  title: string
  icon: string
  closable: boolean
  state: BuilderTabState
  createdAt: number
  resourceId?: string | null
  params?: Record<string, unknown> | null
}

export type BuilderCapabilityGroup = 'build_preview' | 'integration' | 'release_ops' | 'dev_tools'
export type BuilderCapabilityTier = 'P0' | 'P1'

export interface BuilderCapabilityMeta {
  type: BuilderTabType
  title: string
  description: string
  icon: string
  group: BuilderCapabilityGroup
  tier: BuilderCapabilityTier
  enabled: boolean
  singleton: boolean
  defaultClosable: boolean
}
