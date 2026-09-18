import type { PropsWithChildren } from 'react'

import { cn } from '../../lib/cn'

type PageContainerProps = PropsWithChildren<{ className?: string }>

export function PageContainer({ className, children }: PageContainerProps) {
  return <section className={cn('mx-auto w-full max-w-[1280px] space-y-6', className)}>{children}</section>
}
