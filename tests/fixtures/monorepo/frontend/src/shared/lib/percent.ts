// A ratio as a whole percentage, for every panel that shows one.
export function percent(part: number, whole: number): string {
  return whole === 0 ? '0%' : `${Math.round((part / whole) * 100)}%`
}
