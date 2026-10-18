// A tracked metric: its name, the value today and the target it is held against.
export interface Metric {
  name: string
  value: number
  target: number
}

export function onTarget(metric: Metric): boolean {
  return metric.value >= metric.target
}
