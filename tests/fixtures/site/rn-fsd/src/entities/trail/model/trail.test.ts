import { trailById } from './trail'

test('a trail keeps its id', () => {
  expect(trailById('ridge-loop').id).toBe('ridge-loop')
})
