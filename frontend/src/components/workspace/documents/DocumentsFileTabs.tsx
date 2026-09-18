import { X } from 'lucide-react'

import type { OpenFileTab } from '../../../features/ui-shell/workspaceTabs.types'
import { useWorkspaceTabsStore } from '../../../features/ui-shell/workspaceTabs.store'
import { cn } from '../../../lib/cn'

interface DocumentsFileTabsProps {
  openFiles: OpenFileTab[]
  activeFileId: string | null
}

export function DocumentsFileTabs({ openFiles, activeFileId }: DocumentsFileTabsProps) {
  const openFile = useWorkspaceTabsStore((state) => state.openFile)
  const closeFile = useWorkspaceTabsStore((state) => state.closeFile)

  return (
    <div className="flex h-10 shrink-0 items-center gap-1 overflow-x-auto border-b border-border bg-bg-soft/60 px-2">
      {openFiles.map((file) => {
        const isActive = file.id === activeFileId
        return (
          <div
            key={file.id}
            className={cn(
              'group flex h-8 min-w-36 max-w-56 items-center justify-between rounded-token-md border px-2 text-xs transition-colors',
              isActive ? 'border-border bg-surface text-text-main shadow-token-sm' : 'border-transparent text-text-sub hover:bg-surface',
            )}
            title={file.path}
          >
            <button
              type="button"
              onClick={() => openFile(file)}
              className="min-w-0 flex-1 truncate text-left font-medium"
            >
              {file.title}
            </button>
            <button
              type="button"
              aria-label={`close ${file.title}`}
              onClick={() => closeFile(file.id)}
              className="ml-2 flex h-5 w-5 shrink-0 items-center justify-center rounded-token-md text-text-muted opacity-70 hover:bg-bg-soft hover:text-text-main group-hover:opacity-100"
            >
              <X size={12} />
            </button>
          </div>
        )
      })}
    </div>
  )
}
