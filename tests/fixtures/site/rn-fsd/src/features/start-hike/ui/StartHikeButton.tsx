import TrailHaptics from '@modules/trail-haptics'

import { Button } from '@/shared/ui'

import { useHikeTimer } from '../hooks/useHikeTimer'
import { startHike } from '../model/hike'

export function StartHikeButton({ trailId }: { trailId: string }) {
  const timer = useHikeTimer()
  return (
    <Button
      title="Start hike"
      onPress={() => {
        TrailHaptics.pulse()
        timer.start()
        startHike(trailId)
      }}
    />
  )
}
