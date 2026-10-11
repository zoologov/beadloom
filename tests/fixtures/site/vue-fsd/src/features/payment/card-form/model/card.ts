import { reactive } from 'vue'

const details = reactive({ holder: '', number: '' })

export function useCardDetails() {
  return details
}
