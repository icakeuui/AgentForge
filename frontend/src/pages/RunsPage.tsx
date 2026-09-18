import { Play } from 'lucide-react'

import { Alert } from '../components/feedback/Alert'
import { LoadingSkeleton } from '../components/feedback/LoadingSkeleton'
import { PageContainer } from '../components/layout/PageContainer'
import { PageHeader } from '../components/layout/PageHeader'
import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'

export function RunsPage() {
  return (
    <PageContainer>
      <PageHeader
        title="执行运行"
        description="查看运行队列与执行状态。"
        statusSlot={<Badge variant="warning">暂未绑定运行时</Badge>}
        actions={
          <Button variant="secondary" leftIcon={<Play size={14} />}>
            触发运行
          </Button>
        }
      />

      <Alert variant="info" title="阶段说明">
        当前阶段暂未接入完整执行状态机与接口编排。
      </Alert>

      <Card title="运行队列" description="异步运行列表容器。">
        <LoadingSkeleton />
      </Card>
    </PageContainer>
  )
}
