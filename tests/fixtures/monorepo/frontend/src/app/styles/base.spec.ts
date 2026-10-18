import { expect, it } from 'vitest'

import { onTarget } from '@/entities/metric'

import { metricColour } from './base'

it('draws a metric below its target in the warning colour', () => {
  const below = onTarget({ name: 'uploads', value: 3, target: 10 })
  expect(metricColour(below)).toBe('var(--warn)')
})
