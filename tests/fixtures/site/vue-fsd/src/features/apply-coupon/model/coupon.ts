import { useCartStore } from '@/entities/cart'
import { useAddToCart } from '@/features/add-to-cart'
import { formatMoney } from '@/shared/lib'

export function applyCoupon(code: string) {
  const cart = useCartStore()
  useAddToCart()
  return `${code}: ${formatMoney(cart.total)}`
}
