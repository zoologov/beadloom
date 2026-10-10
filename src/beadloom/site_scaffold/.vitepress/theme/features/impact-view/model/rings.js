// beadloom:component=site-impact-view
// The distance rings of the impact mode: which ring each distance is drawn in.
//
// The selected node is ring 0. Direct dependents are ring 1, their dependents
// ring 2, and so on; every distance from the last tone on shares it, so the
// palette stays short however deep the graph is. The tones are theme token
// names (`shared/theme-tokens`, `RING_TONES`), resolved to literal colours by the
// viewer's stylesheet.

import { RING_TONES } from "../../../shared/theme-tokens/index.js";

/** The selection's value for the impact mode; the other value is the neighbourhood. */
export const IMPACT_VIEW = "impact";

/** The ring a distance is drawn in: its own below the last tone, the last tone beyond. */
export function ringOf(distance) {
  return Math.min(distance, RING_TONES.length - 1);
}
