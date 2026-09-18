import type { ExecutionStatus } from '../../../../features/execution/execution.types'
import type { BrowserLinkItem, CodeChangeItem, OpenFileTab } from '../../../../features/ui-shell/workspaceTabs.types'

export interface TimelineArtifactFile {
  id: string
  title: string
  path: string
  summary?: string | null
  additions?: number | null
  deletions?: number | null
}

export type TimelineItem =
  | {
      id: string
      type: 'status'
      status: ExecutionStatus
    }
  | {
      id: string
      type: 'thought'
      stepIndex: number
      thought: string
      defaultExpanded: boolean
    }
  | {
      id: string
      type: 'action'
      stepIndex: number
      toolId: string
      argsSummary: string
      status: 'running' | 'success' | 'error'
    }
  | {
      id: string
      type: 'observation'
      stepIndex: number
      ok: boolean
      summary: string
      rawContent: unknown
      error: Record<string, unknown> | null
      links: BrowserLinkItem[]
      files: TimelineArtifactFile[]
    }
  | {
      id: string
      type: 'artifact'
      files: TimelineArtifactFile[]
      rawCount: number
    }
  | {
      id: string
      type: 'final_answer'
      content: string
    }
  | {
      id: string
      type: 'error'
      title: string
      message: string
      source?: string | null
      code?: string | null
      stepIndex?: number | null
    }

export interface TimelineJumpHandlers {
  openFile: (file: Omit<OpenFileTab, 'id' | 'title'> & Partial<Pick<OpenFileTab, 'id' | 'title'>>) => void
  selectBrowserLink: (link: BrowserLinkItem) => void
  addCodeChange: (item: Omit<CodeChangeItem, 'id' | 'title'> & Partial<Pick<CodeChangeItem, 'id' | 'title'>>) => void
  focusReactStep: (stepIndex: number | null) => void
  pinFinalAnswer: (content: string) => void
}
