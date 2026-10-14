import { getJson } from '@/shared/api'
import { metresToKm } from '@/shared/lib'
import type { Waypoint } from '@/entities/waypoint/@x/trail'

export interface Trail {
  id: string
  name: string
  lengthKm: number
  waypoints: Waypoint[]
}

export function trailById(id: string): Trail {
  return { id, name: id, lengthKm: metresToKm(getJson(`/trails/${id}`).length), waypoints: [] }
}

export function useTrail(id: string): Trail {
  return trailById(id)
}

export function useTrails(): Trail[] {
  return [trailById('ridge-loop')]
}
