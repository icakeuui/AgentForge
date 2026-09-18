import { useExecutionStore } from '../../../features/execution/execution.store'
import { useWorkspaceTabsStore } from '../../../features/ui-shell/workspaceTabs.store'
import { AgentTab } from '../agent/AgentTab'
import { BrowserTab } from '../browser/BrowserTab'
import { CanvasTab } from '../canvas/CanvasTab'
import { CodeChangesTab } from '../changes/CodeChangesTab'
import { DocumentsTab } from '../documents/DocumentsTab'
import { McpTab } from '../mcp/McpTab'
import { ReActFlowTab } from '../react-flow/ReActFlowTab'
import { TerminalTab } from '../terminal/TerminalTab'

export function WorkspaceTabContent() {
  const activeMainTab = useWorkspaceTabsStore((state) => state.activeMainTab)
  const artifacts = useExecutionStore((state) => state.artifacts)

  if (activeMainTab === 'documents') {
    return <DocumentsTab />
  }
  if (activeMainTab === 'terminal') {
    return <TerminalTab />
  }
  if (activeMainTab === 'browser') {
    return <BrowserTab />
  }
  if (activeMainTab === 'code-changes') {
    return <CodeChangesTab artifacts={artifacts} />
  }
  if (activeMainTab === 'mcp') {
    return <McpTab />
  }
  if (activeMainTab === 'canvas') {
    return <CanvasTab />
  }
  if (activeMainTab === 'react-flow') {
    return <ReActFlowTab />
  }
  return <AgentTab />
}
