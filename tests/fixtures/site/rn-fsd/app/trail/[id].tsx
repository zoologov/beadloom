import { useLocalSearchParams } from 'expo-router'

import { TrailScreen } from '@/pages/trail'

export default function TrailRoute() {
  const { id } = useLocalSearchParams<{ id: string }>()
  return <TrailScreen id={id} />
}
