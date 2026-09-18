import { ChevronsUpDown, LayoutGrid } from 'lucide-react'

export function WorkspaceSwitcher() {
  return (
    <button className="flex w-full items-center justify-between rounded-token-md bg-bg-soft px-3 py-2 text-sm text-text-main transition-colors hover:bg-border/50">
      <div className="flex items-center gap-2">
        <div className="flex h-6 w-6 items-center justify-center rounded-token-md bg-primary text-white">
          <LayoutGrid size={14} />
        </div>
        <span className="font-medium">Personal Space</span>
      </div>
      <ChevronsUpDown size={14} className="text-text-muted" />
    </button>
  )
}
