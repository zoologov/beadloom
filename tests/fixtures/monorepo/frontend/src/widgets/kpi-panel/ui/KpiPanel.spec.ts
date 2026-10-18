import { expect, it } from 'vitest'

import { kpiLine } from './KpiPanel'

it('marks a metric on target as met', () => {
  expect(kpiLine({ name: 'uploads', value: 12, target: 10 })).toBe('uploads 120% met')
})
