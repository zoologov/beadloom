import { trailById } from '@/entities/trail'

export function startHike(trailId: string) {
  return { trail: trailById(trailId), startedAt: Date.now() }
}
