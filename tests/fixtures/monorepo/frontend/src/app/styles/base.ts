// The colour a panel line is drawn in, by whether its metric meets its target.
export function metricColour(met: boolean): string {
  return met ? 'var(--ok)' : 'var(--warn)'
}
