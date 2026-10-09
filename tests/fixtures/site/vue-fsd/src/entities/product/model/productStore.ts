import { defineStore } from 'pinia'

import { fetchProducts, type Product } from '../api/productApi'

export const useProductStore = defineStore('product', {
  state: () => ({ items: [] as Product[] }),
  actions: {
    async load() {
      this.items = await fetchProducts()
    },
  },
})
