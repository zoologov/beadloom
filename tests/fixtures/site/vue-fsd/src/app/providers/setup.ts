import { createPinia } from 'pinia'
import { createApp, type Component } from 'vue'

import { router } from './router'

export function createMarketApp(root: Component) {
  return createApp(root).use(createPinia()).use(router)
}
