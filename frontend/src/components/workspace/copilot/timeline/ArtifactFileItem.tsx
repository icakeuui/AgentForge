import { FileText } from 'lucide-react'

import type { TimelineArtifactFile } from './timeline.types'
import { Button } from '../../../ui/Button'

interface ArtifactFileItemProps {
  file: TimelineArtifactFile
  onOpenFile: (file: TimelineArtifactFile) => void
  onOpenCodeChange: (file: TimelineArtifactFile) => void
}

export function ArtifactFileItem({ file, onOpenFile, onOpenCodeChange }: ArtifactFileItemProps) {
  const hasDiff = typeof file.additions === 'number' || typeof file.deletions === 'number'

  return (
    <article className="rounded-token-sm border border-border bg-bg-soft/50 p-2">
      <div className="flex items-center gap-2">
        <FileText size={13} className="text-text-muted" />
        <span className="truncate text-xs font-medium text-text-main">{file.title}</span>
      </div>
      <p className="mt-1 truncate font-mono text-[11px] text-text-muted">{file.path}</p>
      {file.summary ? <p className="mt-1 line-clamp-2 text-[11px] text-text-sub">{file.summary}</p> : null}
      <p className="mt-1 text-[11px] text-text-muted">
        行数统计：{hasDiff ? `+${file.additions ?? 0} / -${file.deletions ?? 0}` : '未提供'}
      </p>
      <div className="mt-1.5 flex items-center gap-1">
        <Button size="sm" variant="ghost" className="h-6 px-2 text-[11px]" onClick={() => onOpenFile(file)}>
          打开文档
        </Button>
        <Button size="sm" variant="ghost" className="h-6 px-2 text-[11px]" onClick={() => onOpenCodeChange(file)}>
          代码变更
        </Button>
      </div>
    </article>
  )
}
