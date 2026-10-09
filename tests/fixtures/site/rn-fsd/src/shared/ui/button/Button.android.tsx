import { Pressable, Text } from 'react-native'

export function Button({ title, onPress }: { title: string; onPress: () => void }) {
  return (
    <Pressable android_ripple={{ color: '#2f5d3a' }} onPress={onPress}>
      <Text>{title}</Text>
    </Pressable>
  )
}
