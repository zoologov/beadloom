import type { ReactNode } from 'react'

import { apiUrl } from '../config'

export function getJson(path: string): { length: number } {
  return { length: `${apiUrl}${path}`.length }
}

export function TrailClientProvider({ children }: { children: ReactNode }) {
  return <>{children}</>
}
