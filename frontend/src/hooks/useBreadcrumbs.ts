import { useMemo } from 'react'
import { useLocation } from 'react-router-dom'

import { DEFAULT_BREADCRUMB_MAP } from '../shared/navigation'

export function useBreadcrumbs() {
  const { pathname } = useLocation()

  return useMemo(() => {
    const segments = pathname.split('/').filter(Boolean)
    if (!segments.length) {
      return ['Home']
    }
    return ['Home', ...segments.map((segment) => DEFAULT_BREADCRUMB_MAP[segment] ?? segment)]
  }, [pathname])
}
