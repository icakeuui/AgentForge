import { Link2 } from 'lucide-react'

import { PageContainer } from '../components/layout/PageContainer'
import { PageHeader } from '../components/layout/PageHeader'
import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { MarketplaceCatalog } from '../components/workspace/mcp/MarketplaceCatalog'

export function MarketplacePage() {
  return (
    <PageContainer>
      <PageHeader
        title="工具市场"
        description="工具目录页面，后续可接入安装与绑定流程。"
        statusSlot={<Badge variant="neutral">目录框架</Badge>}
        actions={
          <Button variant="secondary" leftIcon={<Link2 size={14} />}>
            管理绑定
          </Button>
        }
      />

      <Card title="工具目录" description="真实读取工具市场扩展；安装与绑定动作仍遵循分层权限。">
        <MarketplaceCatalog />
      </Card>
    </PageContainer>
  )
}
