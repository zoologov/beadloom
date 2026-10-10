import { useTrails } from '@/entities/trail'

export function LegacyMapScreen() {
  return useTrails().map((trail) => trail.name)
}
