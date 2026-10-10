import { getJson } from '@/shared/api'
import { metresToKm } from '@/shared/lib'

export interface Trail {
  id: string
  name: string
  lengthKm: number
}

export function trailById(id: string): Trail {
  return { id, name: id, lengthKm: metresToKm(getJson(`/trails/${id}`).length) }
}

export function useTrail(id: string): Trail {
  return trailById(id)
}

export function useTrails(): Trail[] {
  return [trailById('ridge-loop')]
}
