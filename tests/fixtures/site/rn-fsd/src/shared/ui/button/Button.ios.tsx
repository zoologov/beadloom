import { Button as NativeButton } from 'react-native'

export function Button(props: { title: string; onPress: () => void }) {
  return <NativeButton {...props} color="#2f5d3a" />
}
