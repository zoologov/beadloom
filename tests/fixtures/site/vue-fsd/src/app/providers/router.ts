import { createRouter, createWebHistory } from 'vue-router'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: () => import('@/pages/catalog') },
    { path: '/checkout', component: () => import('@/pages/checkout') },
  ],
})
