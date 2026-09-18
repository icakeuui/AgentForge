import { useState } from 'react'

import { Table } from '../components/data/Table'
import { PermissionDenied } from '../components/feedback/PermissionDenied'
import { PageContainer } from '../components/layout/PageContainer'
import { PageHeader } from '../components/layout/PageHeader'
import { Drawer } from '../components/overlay/Drawer'
import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'

const quotaRows = [
  { metric: '每日运行次数', value: '0 / 1000', scope: '团队' },
  { metric: '令牌预算', value: '0 / 2M', scope: '团队' },
]

export function SettingsPage() {
  const [drawerOpen, setDrawerOpen] = useState(false)

  return (
    <PageContainer>
      <PageHeader
        title="系统设置"
        description="配置与额度页面当前为基础界面。"
        statusSlot={<Badge variant="neutral">暂未持久化</Badge>}
        actions={
          <Button variant="secondary" onClick={() => setDrawerOpen(true)}>
            打开设置抽屉
          </Button>
        }
      />

      <Card title="额度表格" description="系统额度数据展示区域。">
        <Table
          data={quotaRows}
          columns={[
            { key: 'metric', header: '指标' },
            { key: 'value', header: '用量' },
            { key: 'scope', header: '范围' },
          ]}
        />
      </Card>

      <PermissionDenied />

      <Drawer open={drawerOpen} onClose={() => setDrawerOpen(false)} title="设置抽屉">
        <p className="text-sm leading-relaxed text-text-muted">设置抽屉已就绪，详细表单稍后补充。</p>
      </Drawer>
    </PageContainer>
  )
}
