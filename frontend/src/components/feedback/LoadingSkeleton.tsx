export function LoadingSkeleton() {
  return (
    <div className="space-y-3 rounded-token-lg border border-border bg-surface p-4">
      <div className="h-4 w-1/3 animate-pulse rounded bg-bg-soft" />
      <div className="h-3 w-full animate-pulse rounded bg-bg-soft" />
      <div className="h-3 w-2/3 animate-pulse rounded bg-bg-soft" />
    </div>
  )
}
