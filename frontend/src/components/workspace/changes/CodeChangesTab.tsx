import { FileDiff } from 'lucide-react'

import { useWorkspaceTabsStore } from '../../../features/ui-shell/workspaceTabs.store'
import type { CodeChangeItem } from '../../../features/ui-shell/workspaceTabs.types'
import { Button } from '../../ui/Button'

interface CodeChangesTabProps {
  artifacts?: unknown[]
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function fileTitle(path: string): string {
  const parts = path.split(/[\\/]/).filter(Boolean)
  return parts.at(-1) ?? path
}

function extractArtifactChanges(artifacts: unknown[] | undefined): CodeChangeItem[] {
  if (!Array.isArray(artifacts)) {
    return []
  }

  return artifacts.flatMap((artifact, index) => {
    if (!isRecord(artifact)) {
      return []
    }
    const path = artifact.path ?? artifact.file_path ?? artifact.filename
    if (typeof path !== 'string' || path.trim().length === 0) {
      return []
    }
    const additions = typeof artifact.additions === 'number' ? artifact.additions : null
    const deletions = typeof artifact.deletions === 'number' ? artifact.deletions : null
    const summary = typeof artifact.summary === 'string' ? artifact.summary : typeof artifact.description === 'string' ? artifact.description : null

    return [
      {
        id: `artifact-change:${index}:${path}`,
        title: fileTitle(path),
        path,
        summary,
        additions,
        deletions,
        source: 'artifacts',
      },
    ]
  })
}

function mergeChanges(primary: CodeChangeItem[], secondary: CodeChangeItem[]): CodeChangeItem[] {
  const seen = new Set<string>()
  return [...primary, ...secondary].filter((item) => {
    const key = item.path ?? item.id
    if (seen.has(key)) {
      return false
    }
    seen.add(key)
    return true
  })
}

export function CodeChangesTab({ artifacts }: CodeChangesTabProps) {
  const storedItems = useWorkspaceTabsStore((state) => state.codeChanges.items)
  const activeItemId = useWorkspaceTabsStore((state) => state.codeChanges.activeItemId)
  const openFile = useWorkspaceTabsStore((state) => state.openFile)
  const items = mergeChanges(storedItems, extractArtifactChanges(artifacts))

  if (items.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center rounded-token-lg border border-dashed border-border bg-surface p-6 text-center">
        <FileDiff size={34} className="mb-3 text-border" />
        <p className="text-sm font-medium text-text-main">暂无可展示的变更摘要</p>
        <p className="mt-1 max-w-md text-xs leading-relaxed text-text-muted">
          需要 artifacts 或可识别的文件动作后才会出现列表；没有 +/- 字段时会明确标注未提供。
        </p>
      </div>
    )
  }

  return (
    <div className="h-full overflow-auto rounded-token-lg border border-border bg-surface p-4 shadow-token-sm">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-text-main">变更摘要</h2>
        <span className="text-xs text-text-muted">{items.length} 个文件</span>
      </div>
      <div className="space-y-3">
        {items.map((item) => {
          const isActive = item.id === activeItemId
          return (
            <article
              key={item.id}
              className={`rounded-token-md border p-3 ${isActive ? 'border-primary bg-info-soft' : 'border-border bg-bg-soft/50'}`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <h3 className="truncate text-sm font-semibold text-text-main">{item.title}</h3>
                  {item.path ? <p className="mt-1 truncate font-mono text-xs text-text-muted">{item.path}</p> : null}
                </div>
                {item.path ? (
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => openFile({ path: item.path ?? '', kind: 'change', source: '代码变更' })}
                  >
                    打开
                  </Button>
                ) : null}
              </div>
              {item.summary ? <p className="mt-2 text-xs leading-relaxed text-text-sub">{item.summary}</p> : null}
              <div className="mt-2 text-xs text-text-muted">
                行数统计：
                {item.additions === null && item.deletions === null
                  ? '未提供'
                  : `+${item.additions ?? 0} / -${item.deletions ?? 0}`}
              </div>
            </article>
          )
        })}
      </div>
    </div>
  )
}
