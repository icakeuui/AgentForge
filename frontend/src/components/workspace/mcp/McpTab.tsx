import { Plug } from 'lucide-react'

import { MarketplaceCatalog } from './MarketplaceCatalog'

export function McpTab() {
  return (
    <div className="h-full overflow-auto rounded-token-lg border border-border bg-bg-soft/40 p-4">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 text-sm font-semibold text-text-main">
            <Plug size={15} className="text-text-muted" />
            MCP / 工具市场
          </div>
          <p className="mt-1 text-xs text-text-muted">
            当前读取真实目录；安装、测试配置与绑定按钮保持受控状态。
          </p>
        </div>
      </div>
      <MarketplaceCatalog />
    </div>
  )
}
