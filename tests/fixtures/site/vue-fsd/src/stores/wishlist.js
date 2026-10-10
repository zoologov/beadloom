import { defineStore } from 'pinia'

import { useProductStore } from '@/entities/product'

export const useWishlistStore = defineStore('wishlist', {
  state: () => ({ slugs: [] }),
  getters: {
    items: (state) => useProductStore().items.filter((p) => state.slugs.includes(p.slug)),
  },
})
