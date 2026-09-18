import { EmptyState } from '../components/feedback/EmptyState'
import { PageContainer } from '../components/layout/PageContainer'

export function NotFoundPage() {
  return (
    <PageContainer>
      <EmptyState title="页面不存在" description="当前路由不在页面映射中。" />
    </PageContainer>
  )
}
