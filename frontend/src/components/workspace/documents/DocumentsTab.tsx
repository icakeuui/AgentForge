import { Copy, FileText } from 'lucide-react'
import { useState } from 'react'

import { useWorkspaceTabsStore } from '../../../features/ui-shell/workspaceTabs.store'
import { Button } from '../../ui/Button'
import { DocumentsFileTabs } from './DocumentsFileTabs'

export function DocumentsTab() {
  const openFiles = useWorkspaceTabsStore((state) => state.documents.openFiles)
  const activeFileId = useWorkspaceTabsStore((state) => state.documents.activeFileId)
  const [copied, setCopied] = useState(false)
  const activeFile = openFiles.find((file) => file.id === activeFileId) ?? null

  const copyPath = async () => {
    if (!activeFile || typeof navigator === 'undefined') {
      return
    }
    await navigator.clipboard.writeText(activeFile.path)
    setCopied(true)
    setTimeout(() => setCopied(false), 1600)
  }

  if (openFiles.length === 0) {
    return (
      <div className="flex h-full items-center justify-center rounded-token-lg border border-dashed border-border bg-surface text-sm text-text-muted">
        尚未打开文件
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-token-lg border border-border bg-surface shadow-token-sm">
      <DocumentsFileTabs openFiles={openFiles} activeFileId={activeFileId} />
      {activeFile ? (
        <div className="flex min-h-0 flex-1 flex-col">
          <div className="flex shrink-0 items-center justify-between border-b border-border px-4 py-3">
            <div className="min-w-0">
              <div className="flex items-center gap-2 text-sm font-semibold text-text-main">
                <FileText size={15} className="text-text-muted" />
                <span className="truncate">{activeFile.title}</span>
              </div>
              <p className="mt-1 truncate font-mono text-xs text-text-muted">{activeFile.path}</p>
            </div>
            <Button variant="ghost" size="sm" leftIcon={<Copy size={13} />} onClick={copyPath}>
              {copied ? '已复制' : '复制路径'}
            </Button>
          </div>
          <div className="min-h-0 flex-1 overflow-auto bg-bg-soft/40 p-4">
            {activeFile.previewText && activeFile.previewText.trim().length > 0 ? (
              <pre className="min-h-full whitespace-pre-wrap rounded-token-md border border-border bg-surface p-4 font-mono text-xs leading-relaxed text-text-main">
                {activeFile.previewText}
              </pre>
            ) : (
              <div className="flex h-full min-h-56 flex-col items-center justify-center rounded-token-md border border-dashed border-border bg-surface p-6 text-center">
                <FileText size={32} className="mb-3 text-border" />
                <p className="text-sm font-medium text-text-main">当前仅展示引用（内容待接线）</p>
                <p className="mt-1 max-w-md text-xs leading-relaxed text-text-muted">
                  文档标签已经接管打开对象与二级 tabs；真实文件读取或编辑器能力会作为后续 gated 能力接入。
                </p>
              </div>
            )}
          </div>
        </div>
      ) : null}
    </div>
  )
}
