import { FlatList } from 'react-native'

import { TrailCard, useTrails } from '@/entities/trail'
import { Badge } from '@/shared/ui'

export function TrailList() {
  const trails = useTrails()
  return (
    <FlatList
      data={trails}
      ListHeaderComponent={<Badge text={`${trails.length} trails`} />}
      renderItem={({ item }) => <TrailCard trail={item} />}
    />
  )
}
