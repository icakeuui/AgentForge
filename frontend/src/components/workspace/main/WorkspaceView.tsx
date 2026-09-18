import { BuilderTabBar } from '../builder/BuilderTabBar'
import { BuilderTabContent } from '../builder/BuilderTabContent'
import { ContextHeader } from './ContextHeader'

export function WorkspaceView() {
  return (
    <div className="flex h-full min-w-0 flex-col bg-bg">
      <ContextHeader />
      <BuilderTabBar />

      <div className="flex min-h-0 flex-1 flex-col overflow-hidden bg-bg p-4 pt-3 md:p-6 md:pt-4">
        <BuilderTabContent />
      </div>
    </div>
  )
}
