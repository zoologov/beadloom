import { Text } from 'react-native'

import { Badge } from '@/shared/ui'

export function TrailCard({ trail }) {
  return (
    <Text>
      {trail.name} <Badge text={`${trail.lengthKm} km`} />
    </Text>
  )
}
