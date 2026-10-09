import { View } from 'react-native'

import { TrailCard, useTrail } from '@/entities/trail'
import { StartHikeButton } from '~/src/features/start-hike'

export function TrailScreen({ id }: { id: string }) {
  const trail = useTrail(id)
  return (
    <View>
      <TrailCard trail={trail} />
      <StartHikeButton trailId={id} />
    </View>
  )
}
