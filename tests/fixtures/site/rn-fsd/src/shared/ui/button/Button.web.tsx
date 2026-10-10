export function Button({ title, onPress }: { title: string; onPress: () => void }) {
  return (
    <button type="button" onClick={onPress}>
      {title}
    </button>
  )
}
