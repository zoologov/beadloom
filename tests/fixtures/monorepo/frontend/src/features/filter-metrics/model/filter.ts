import { onTarget, type Metric } from '@/entities/metric'

// The metrics the dashboard shows when the reader asks for the ones below their target.
export function belowTarget(metrics: Metric[]): Metric[] {
  return metrics.filter((metric) => !onTarget(metric))
}
