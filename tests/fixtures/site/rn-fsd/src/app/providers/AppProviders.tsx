import type { ReactNode } from 'react'

import { TrailClientProvider } from '@/shared/api'

export function AppProviders({ children }: { children: ReactNode }) {
  return <TrailClientProvider>{children}</TrailClientProvider>
}
