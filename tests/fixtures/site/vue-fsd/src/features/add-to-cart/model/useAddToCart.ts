import { useCartStore } from '@/entities/cart'

export function useAddToCart() {
  const cart = useCartStore()
  return (slug: string) => cart.add(slug)
}
