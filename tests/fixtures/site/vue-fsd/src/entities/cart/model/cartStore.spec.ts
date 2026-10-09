import { createPinia, setActivePinia } from 'pinia'
import { expect, it } from 'vitest'

import { useCartStore } from './cartStore'

it('counts what was added', () => {
  setActivePinia(createPinia())
  const cart = useCartStore()
  cart.add('heron-at-dawn')
  expect(cart.count).toBe(1)
})
