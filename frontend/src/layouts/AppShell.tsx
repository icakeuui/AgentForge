import { useCallback, useEffect, useState } from 'react'
import { Outlet } from 'react-router-dom'

import { useUiShellStore } from '../features/ui-shell/uiShell.store'
import { CopilotPanel } from '../components/workspace/layout/CopilotPanel'
import { WorkspaceRail } from '../components/workspace/layout/WorkspaceRail'
import { cn } from '../lib/cn'

export function AppShell() {
  const setLeftPanelWidth = useUiShellStore((state) => state.setLeftPanelWidth)
  const setRightPanelWidth = useUiShellStore((state) => state.setRightPanelWidth)

  const [isResizingLeft, setIsResizingLeft] = useState(false)
  const [isResizingRight, setIsResizingRight] = useState(false)
  const startResizingLeft = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    setIsResizingLeft(true)
  }, [])

  const startResizingRight = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    setIsResizingRight(true)
  }, [])

  const stopResizing = useCallback(() => {
    setIsResizingLeft(false)
    setIsResizingRight(false)
  }, [])

  const resize = useCallback(
    (e: MouseEvent) => {
      if (isResizingLeft) {
        setLeftPanelWidth(e.clientX)
      } else if (isResizingRight) {
        setRightPanelWidth(window.innerWidth - e.clientX)
      }
    },
    [isResizingLeft, isResizingRight, setLeftPanelWidth, setRightPanelWidth],
  )

  useEffect(() => {
    if (isResizingLeft || isResizingRight) {
      window.addEventListener('mousemove', resize)
      window.addEventListener('mouseup', stopResizing)
      document.body.style.cursor = 'col-resize'
      document.body.style.userSelect = 'none'
    } else {
      window.removeEventListener('mousemove', resize)
      window.removeEventListener('mouseup', stopResizing)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }

    return () => {
      window.removeEventListener('mousemove', resize)
      window.removeEventListener('mouseup', stopResizing)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }
  }, [isResizingLeft, isResizingRight, resize, stopResizing])

  return (
    <div className="flex h-screen w-screen flex-row overflow-hidden bg-bg text-text-main">
      <WorkspaceRail />

      <div
        className={cn(
          'group relative z-20 w-1 cursor-col-resize bg-transparent transition-colors hover:bg-primary/30',
          isResizingLeft && 'bg-primary/50',
        )}
        onMouseDown={startResizingLeft}
      >
        <div className="absolute inset-y-0 -left-1 -right-1" />
      </div>

      <div className="flex min-w-0 flex-1 flex-col">
        <main className="flex-1 overflow-hidden bg-bg relative animate-in fade-in duration-500">
          <Outlet />
        </main>
      </div>

      <div
        className={cn(
          'group relative z-20 w-1 cursor-col-resize bg-transparent transition-colors hover:bg-primary/30',
          isResizingRight && 'bg-primary/50',
        )}
        onMouseDown={startResizingRight}
      >
        <div className="absolute inset-y-0 -left-1 -right-1" />
      </div>
      <CopilotPanel />
    </div>
  )
}
