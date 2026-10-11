export interface Waypoint {
  name: string
  km: number
}

export function waypointsOf(trailId: string): Waypoint[] {
  return [{ name: `${trailId} start`, km: 0 }]
}
