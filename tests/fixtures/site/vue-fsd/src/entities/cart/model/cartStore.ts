import { defineStore } from 'pinia'

import { formatMoney } from '@/shared/lib'

export const useCartStore = defineStore('cart', {
  state: () => ({ slugs: [] as string[], total: 0 }),
  getters: {
    count: (state) => state.slugs.length,
    label: (state) => formatMoney(state.total),
  },
  actions: {
    add(slug: string) {
      this.slugs.push(slug)
    },
  },
})
