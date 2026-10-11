import { defineStore } from 'pinia'

import type { Product } from '@/entities/product/@x/cart'
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
    addProduct(product: Product) {
      this.slugs.push(product.slug)
      this.total += product.price
    },
  },
})
