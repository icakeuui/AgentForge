import { TerminalSquare } from 'lucide-react'

import { PanelSection } from '../shared/PanelSection'
import { RichContentRenderer } from '../rich-content/RichContentRenderer'

interface AgentOutputPanelProps {
  final_answer: string | null
  isMaximized?: boolean
  onMaximize?: () => void
}

export function AgentOutputPanel({ final_answer, isMaximized, onMaximize }: AgentOutputPanelProps) {
  return (
    <PanelSection 
      title="最终输出" 
      icon={<TerminalSquare size={16} />} 
      className="flex-1"
      isMaximized={isMaximized}
      onMaximize={onMaximize}
    >
      {final_answer === null || final_answer.trim().length === 0 ? (
        <div className="flex h-full flex-col items-center justify-center p-6 text-center text-text-muted">
          <TerminalSquare size={40} className="mb-3 text-border" />
          <p className="text-sm font-medium text-text-main">暂无输出</p>
        </div>
      ) : (
        <div className="h-full p-4">
          <div className="h-full overflow-auto rounded-token-md border border-border bg-surface p-4">
            <RichContentRenderer content={final_answer} />
          </div>
        </div>
      )}
    </PanelSection>
  )
}
