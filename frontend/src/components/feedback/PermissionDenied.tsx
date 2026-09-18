import { Lock } from 'lucide-react'

import { Alert } from './Alert'

export function PermissionDenied() {
  return (
    <Alert variant="warning" title="需要权限">
      <span className="inline-flex items-center gap-2">
        <Lock size={14} />
        你没有当前范围的足够权限。
      </span>
    </Alert>
  )
}
