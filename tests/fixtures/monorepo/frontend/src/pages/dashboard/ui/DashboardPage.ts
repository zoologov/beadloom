import type { Metric } from '@/entities/metric'
import { belowTarget } from '@/features/filter-metrics'
import { kpiLine } from '@/widgets/kpi-panel'

// The dashboard: one panel line per tracked metric, or per metric below its target.
export function dashboard(metrics: Metric[], onlyBelow = false): string[] {
  return (onlyBelow ? belowTarget(metrics) : metrics).map(kpiLine)
}
