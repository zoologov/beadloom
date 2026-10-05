# R&D: BDL-078 — the viewer's look and the activity metric

> **Measured:** 2026-10-04, on main `2f65cbd9`; prototype and 64 screenshots in the session scratchpad (`v078/`); the owner's report links the key ones.

Paths relative to `src/beadloom/site_scaffold/.vitepress/theme/widgets/graph-viewer/`.

| Problem | Cause (file:line) | Prototype |
|---|---|---|
| Overview widths | `lib/mapMarks.js:33-35` width = 1.5 + 1.1·log2(count) px, up to 6.7–7.5 px against 40–60 px boxes; full-strength colour (`lib/stylesheet.js:315-317`); count is a Cytoscape label painted over by later edges (`:318-322`); title all-or-nothing at 14 px (`mapMarks.js` `titleFits`) | three steps 1.5 / 2.5 / 3.5 px for 1–3 / 4–15 / 16+; neutral colour; counts as pills on an overlay with collision avoidance; titles try 14 / 12.5 / 11 / 10 px, then outside on a plate |
| Arrowheads | Cytoscape head = max((width·13.37)^0.9, 29)·arrow-scale — sublinear, about 2× a thick line (`stylesheet.js:218`); medoid routes guarantee no straight run before the box (`lib/aggregateRoutes.js:166-177`), measured 16–24 px; corner radius 6 units = 0.3 px at fit (`stylesheet.js:69`, `:185`) | `arrow-scale` per edge inverting the formula (8 / 9.5 / 11 px on screen); last cross-run moved back for a straight end (needs the box check `crossesABox`); 7 px screen-space radius on aggregated corners |
| Bridges | `model/bridgeOverlay.js:207-232` three strokes: erase with an "under" colour (notches), solid butt redraw, solid arc ≤ 5 px even on dashed lines; hop cap 4.5 units vs 10-unit lanes → chains (`lib/bridgePaint.js:25-33`, `:70-74`) | removed; a followed edge drawn on top, full strength, slightly wider, with a background casing (`line-outline-width`); production draws casings then lines in two passes on the overlay (per-edge outlines cut 2 px slits at T-joins) |
| Junction dots | dot at the polyline corner (`lib/junctions.js:115-121`, `model/bundleOverlay.js:60`, radius 3.6) while the corner is rounded by 6 (`stylesheet.js:184-185`) → the stroke passes ~2.5 units inside; dot takes the strongest edge's full colour on a line faded to 35% at its source (`stylesheet.js:75`, `:203-204`); 612 dots | junction corners square via per-corner `segment-radii`; no dot at a T-join, a dot only at a four-way junction; solid line colour |
| Look | double status border, dashed 3 px containers, gradient edges, a kind label on every selected edge | card nodes with a 1.5 px layer-tone border and a corner status mark; containers 1 px solid, 6–10% tint, header inside; solid edge colours (imports neutral ~40% ink, other kinds 82% tone, violation full danger); label on hover only |

## Activity

`infrastructure/git_activity.py:167-289` counts distinct commits per node and agrees with `git log` (three nodes compared; a window off-by-one at `:164`, `delta.days <= 30`). The metric does not fit a squash-merged history: of 69 commits in 30 days, 39 are one unsquashed branch touching only the viewer; for 42 of the 51 "1 commit" nodes that commit is one of three sweeping squashes. Thresholds (`:35-55`: hot > 20, warm 5–20) assume un-squashed history; attribution is leaf-only (`:58-78`: the `infrastructure` box shows 0, its folder has 7); zero-in-30 with some in 90 is named "cold" like 1–4. Distribution here: 85 nodes cold with 1–4, 33 at zero, 9 warm, 0 hot. Not causes: shallow history, the BDL-076 path moves.

## How other tools handle it (from knowledge, not verified in this session)

Thin uniform or two-to-three-step line weights; counts and labels as chips with a background; arrowheads sized independently of stroke width; highlight-and-dim with the followed edge raised instead of line jumps (jumps exist in draw.io and yFiles; yFiles is the reference for hub dots on square joins).

## Probe: a readable overview (2026-10-04)

Diagnosis confirmed on the first prototype (V0): medoid lanes 0.8 px apart at the fit; 12 overlapping arrowhead pairs here, 174 at adopter size; 13 of 34 lines under a title plate.

| This repository (34 lines) | head overlaps | min gap px | crowded px | crossings | length px | through box | under a title | routing |
|---|---|---|---|---|---|---|---|---|
| V0 prototype | 12 | 0.8 | 4,108 | 55 | 11,120 | 3 | 13 | – |
| V1 tidy medoids (ports spread, nudged) | 0 | 0.8 | 3,614 | 64 | 10,953 | 0 | 13 | 0.3 ms |
| V2 overview router | 0 | 7.1 | 0 | 50 | 8,623 | 0 | 0 | 18 ms |
| V3 direct curves | 9 | 0.8 | 974 | 79 | 7,282 | 8 | 5 | 0.6 ms |
| **V5 = V2 + calm by default** (chosen) | 0 | 7.1 | 0 | 50 | 8,623 | 0 | 0 | 18 ms |

Adopter-sized (36 boxes, 100 lines): V0 174 head overlaps; V1 38; V2/V5 2 (one line fell back to its medoid), routing 100 ms; V3 109. The router works on a grid of tracks about 8 px apart, boxes and outside titles as obstacles, a straight run into each box, bends, crossings and running beside another line priced; lines into one box may share their last run and one arrowhead. Boxes never move.

Open: with one box open every variant is poor (about 100 lines from small nodes to closed boxes) → owner's ruling 9. The adopter-sized "fit" does not fit (zoom clamps at 0.02; boxes about 35×10 px) → deferred (ruling 11). A top-level leaf node has no readable title at the overview → in scope.

## Probe: an open box stays calm (V6, 2026-10-04)

Rules: an edge is drawn between siblings at the lowest box holding both ends, as itself only when both ends are those children and neither is a box; a pair between top-level ends always keeps the overview plan's route and port, open or closed; a node's outward edges are a "+N" chip at rest and appear on hover or selection (to a closed box: one line; to an open one: the edge on its ELK route), on top with a casing; a walk draws only its own edges as themselves; own lines at a leaf share an arriving and a leaving port (one head).

| State (this repository) | lines in view | head overlaps | min gap, box-level px | crowded px | max heads per side | re-plan / redraw ms |
|---|---|---|---|---|---|---|
| one box open, V5 | 114 | 10 | 0.8 | 28,740 | 13 | 5.4 / 8.1 |
| one box open, V6 | 43 | 0 | 22.8 | 1,222 | 3 | 0.3 / 1.9 |
| two boxes open, V5 → V6 | 204 → 110 | 28 → 0 | 0.8 → 14.1 | 42,746 → 1,846 | 14 → 3 | — |

Adopter-sized, one box open: head overlaps 29 → 0, crowded 11,416 → 388. A full hover: median 8.6 ms here, 9.8 ms at adopter size. Opening a box moves no box-level line or pill.

Still poor in the probe: inner wiring at the 600 px opening threshold (nodes about 55×12 px) → ruling 12; arrows ending where an outside title plate was → lines must end on the box border, the plate only an obstacle; a hub's own lines get a double head (use the node's bus port); the faded box-level line stays under a hovered node's own lines.
