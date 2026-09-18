export type MainTabId =
  | 'documents'
  | 'terminal'
  | 'browser'
  | 'code-changes'
  | 'agent'
  | 'mcp'
  | 'canvas'
  | 'react-flow'

export interface OpenFileTab {
  id: string
  title: string
  path: string
  kind: 'file' | 'artifact' | 'change' | 'reference'
  previewText?: string | null
  source?: string | null
}

export interface BrowserLinkItem {
  id: string
  title: string
  url: string
  snippet?: string | null
  source?: string | null
}

export interface TerminalCommandItem {
  id: string
  command: string
  title?: string | null
  source?: string | null
}

export interface CodeChangeItem {
  id: string
  title: string
  path?: string | null
  summary?: string | null
  additions?: number | null
  deletions?: number | null
  source?: string | null
}

export interface CanvasPinItem {
  id: string
  type: 'answer' | 'file' | 'link' | 'step' | 'note'
  title: string
  summary?: string | null
  target?: WorkspaceJumpTarget | null
}

export type WorkspaceJumpTarget =
  | { type: 'tab'; tab: MainTabId }
  | { type: 'file'; file: Omit<OpenFileTab, 'id' | 'title'> & Partial<Pick<OpenFileTab, 'id' | 'title'>> }
  | { type: 'browser'; link: Omit<BrowserLinkItem, 'id' | 'title'> & Partial<Pick<BrowserLinkItem, 'id' | 'title'>> }
  | { type: 'terminal'; command: Omit<TerminalCommandItem, 'id'> & Partial<Pick<TerminalCommandItem, 'id'>> }
  | { type: 'code-change'; item?: Omit<CodeChangeItem, 'id' | 'title'> & Partial<Pick<CodeChangeItem, 'id' | 'title'>> }
  | { type: 'canvas'; pin?: Omit<CanvasPinItem, 'id' | 'title'> & Partial<Pick<CanvasPinItem, 'id' | 'title'>> }
  | { type: 'react-flow'; stepIndex?: number | null }
  | { type: 'agent' }
  | { type: 'mcp' }

export const MAIN_TAB_LABELS: Record<MainTabId, string> = {
  documents: '文档',
  terminal: '终端',
  browser: '浏览器',
  'code-changes': '代码变更',
  agent: '智能体',
  mcp: 'MCP',
  canvas: '画布',
  'react-flow': '执行流程',
}
