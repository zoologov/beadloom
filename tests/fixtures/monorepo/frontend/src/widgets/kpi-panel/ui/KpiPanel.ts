import { onTarget, type Metric } from '@/entities/metric'
import { percent } from '@/shared/lib'

// One metric as a panel line: its name, its share of the target and whether it is met.
export function kpiLine(metric: Metric): string {
  const mark = onTarget(metric) ? 'met' : 'below'
  return `${metric.name} ${percent(metric.value, metric.target)} ${mark}`
}
