import { useRef } from 'react'

export function useHikeTimer() {
  const started = useRef(0)
  return { start: () => (started.current = Date.now()) }
}
