import { http } from '@/shared/api'

export interface Product {
  slug: string
  title: string
  price: number
}

export function fetchProducts(): Promise<Product[]> {
  return http<Product[]>('/products')
}
