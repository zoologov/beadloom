// beadloom:component=site-impact-view
// The distance rings of the impact mode: which theme tone marks each distance.
//
// The selected node is ring 0. Direct dependents are ring 1, their dependents
// ring 2, and so on; every distance from the last tone on shares it, so the
// palette stays short however deep the graph is. The tones are theme token
// names, resolved to literal colours by the viewer's stylesheet. They are the
// base colours rather than the semantic ones: VitePress defines `warning` as
// `yellow` and `danger` as `red`, so a palette naming both would draw two rings
// in one colour.

/** The selection's value for the impact mode; the other value is the neighbourhood. */
export const IMPACT_VIEW = "impact";

/** The tone of each ring, from the selected node outwards. */
export const RING_TONES = Object.freeze(["brand", "red", "yellow", "green", "purple", "gray"]);

/** The ring a distance is drawn in: its own below the last tone, the last tone beyond. */
export function ringOf(distance) {
  return Math.min(distance, RING_TONES.length - 1);
}
