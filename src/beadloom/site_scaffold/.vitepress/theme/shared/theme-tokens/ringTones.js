// beadloom:component=site-shared
// The tones of the impact mode's distance rings, by theme token name.
//
// The selected node is ring 0, its direct dependents ring 1, and so on; every
// distance from the last tone on shares it (`features/impact-view`, `ringOf`). The
// tones are the base colours rather than the semantic ones: VitePress defines
// `warning` as `yellow` and `danger` as `red`, so a palette naming both would draw
// two rings in one colour. They are resolved to literal colours by the viewer's
// stylesheet and by the impact summary's legend, which both read them here.

/** The tone of each ring, from the selected node outwards. */
export const RING_TONES = Object.freeze(["brand", "red", "yellow", "green", "purple", "gray"]);
