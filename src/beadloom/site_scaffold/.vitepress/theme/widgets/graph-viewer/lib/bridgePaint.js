// beadloom:component=site-graph-viewer
// The paint a bridge takes: an edge's colour where it is crossed, what lies under the crossing, and the hop's size.
//
// A bridge is drawn over the canvas in three strokes: the highlighted line is
// erased around the crossing in the colour under it, the crossed line is drawn
// again through the gap, and a half circle in the highlighted line's colour
// hops over it. Each stroke takes the colour Cytoscape drew at that place:
//
// - An edge whose line fades towards its source is a linear gradient from its
//   source end to its target end; its colour at a point is the gradient's at the
//   point's projection on that line (`colourAlong`), as a canvas computes it.
// - Under a crossing lies the canvas's background with the tint of every box
//   around the point over it, the outermost first (`colourUnder`).
//
// The hop is as wide as both lines need to clear each other, and no wider than
// half the room between two parallel edges once the view is close enough to
// tell them apart; below `SMALLEST_HOP` pixels it is not drawn at all, since a
// hop no one can see costs a frame and shows nothing (`hopRadius`).
//
// Every function here is pure: colours and sizes in, a colour or a size out.

import { mixRgb } from "../../../shared/theme-tokens/index.js";

/** What a hop measures on screen, in pixels unless named otherwise. */
export const HOP = Object.freeze({
  /** The radius a hop takes once the view is close enough. */
  radius: 5,
  /** The radius in layout units it never exceeds: under half the 10 units ELK keeps between parallel edges. */
  radiusUnits: 4.5,
  /** The room left between the hop and the line it clears. */
  clearance: 1,
  /** The smallest radius a hop is drawn at. */
  smallest: 2,
});

/**
 * The colour of a gradient line from `start` to `end` at `point`: `stops` are
 * the colours, `positions` where each sits along the line, from 0 to 1. Before
 * the first stop the line has the first colour, after the last the last.
 */
export function colourAlong(stops, positions, start, end, point) {
  if (stops.length === 1) return stops[0];
  const dx = end.x - start.x;
  const dy = end.y - start.y;
  const length2 = dx * dx + dy * dy;
  const t = length2 ? ((point.x - start.x) * dx + (point.y - start.y) * dy) / length2 : 0;
  if (t <= positions[0]) return stops[0];
  for (let i = 1; i < stops.length; i += 1) {
    if (t > positions[i]) continue;
    const width = positions[i] - positions[i - 1];
    return width > 0 ? mixRgb(stops[i], stops[i - 1], (t - positions[i - 1]) / width) : stops[i];
  }
  return stops[stops.length - 1];
}

/**
 * The colour under a point: `background` with each of `tints` over it in order,
 * the outermost first; a tint is `{ colour, alpha }`.
 */
export function colourUnder(background, tints) {
  return tints.reduce((under, { colour, alpha }) => (alpha > 0 ? mixRgb(colour, under, Math.min(1, alpha)) : under), background);
}

/**
 * The radius of a hop at `zoom`, in pixels on screen, over a crossed line of
 * `crossedWidth` by a line of `width`, both in layout units: wide enough to
 * clear the crossed line, and `HOP.radius` once the view shows `HOP.radiusUnits`
 * as that much. Zero when it would be smaller than `HOP.smallest`.
 */
export function hopRadius(zoom, width, crossedWidth) {
  const clear = ((width + crossedWidth) / 2) * zoom + HOP.clearance;
  const radius = Math.max(clear, Math.min(HOP.radius, HOP.radiusUnits * zoom));
  return radius < HOP.smallest ? 0 : radius;
}
