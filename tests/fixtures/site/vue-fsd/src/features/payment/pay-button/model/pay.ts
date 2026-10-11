import { useCardDetails } from '@/features/payment/card-form'

export function pay(): string {
  const card = useCardDetails()
  return `paid by ${card.holder}`
}
