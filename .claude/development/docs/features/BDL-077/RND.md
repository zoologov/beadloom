# R&D: BDL-077 — edges around blocks, bridges, and the renderer

> **Bead:** `beadloom-rcnz` · **Measured:** 2026-10-03 · **Where:** two scratch prototypes, nothing in the repository
> **Machine:** Darwin arm64 (M1 Max), Node 22.9.0, Chromium 1243 (Playwright 1.63.0), GPU and software raster

## Graphs

- **This repository:** `architecture.data.json` at `5aeaf18c` — 130 nodes, 453 drawn edges, 12 compounds, depth 3.
- **Adopter-sized (synthetic, seeded):** path A 445 nodes / 1,300 edges / 41 compounds; path B 400 / 1,300 / 37. Proportions taken from ours: 58% of edges down the layers, 30% within a rank, ~40% inside one parent, ~20% ending on a compound, 2.5–5.5% to the node's own ancestor, hubs (top degree 239).

## The metric

BDL-076 A2's edge-sharing measure: the share of an edge's middle within 4 layout units of another drawn edge, and the number of edges more than half shared. Path B found A2's script and reproduced its figure (22 edges); path B's numbers are the comparable ones. Path A re-implemented it from the description (bezier baseline 0.314 / 82); its ordering of variants matches, its absolute values do not.

## Results

| | Cytoscape bezier (today) | Cytoscape + ELK routes (A) | Own SVG from ELK (B) | JointJS 4.3.3 manhattan | maxGraph 0.24 |
|---|---|---|---|---|---|
| Mean shared (A2) | 14.4% / 5.2% | 2.2% / 1.1% (A's metric: 0.079 vs 0.314) | 2.2% / 1.1% | 51% / 16% | 57% / 18% |
| Edges >½ shared | 22 / 17 | 0 / 0 | 0 / 0 | 241 / 125 | 274 / 144 |
| Edges through a box they don't connect | 232 / 678 | 0 routed (8 / 43 compound loops) | 0 / 0 | 184 / 481 | 254 / 647 |
| Crossings | 9,407 / 54,409 | 6,295 / 52,498 | 6,295 / 52,498 | — | — |
| Router gave up | — | — | — | 59% / 59% | ~all |
| Draw after layout | in layout | +10 ms / +28 ms | 4 / 9 ms (10 / 43 with jumps) | 3.0 s / 12 s | 49 / 117 ms |
| Frame, pan at fit, full screen (GPU), mean/p95 | 16.8 / 63 | ≈ today | 16.7 / 49 | 16.7 / 48 (ELK vertices) | 35 / 186 |
| Frame at zoom 1 | 16.7 | ≈ today | 16.7 | 16.7 | 34 |
| Bridges | none | overlay canvas; 7,580 / 92,025 found in 29 / 208 ms (A's count) | own; 10 / 43 ms | `jumpover`: 0.6 s / 4.5 s per selection (O(E²), recomputed per model batch) | not in core |
| Licence | MIT | MIT | ours | MPL-2.0 | Apache-2.0, pre-1.0 |
| Library gzip | 141 KB (+cytoscape-elk with nested ELK: 586 KB total) | 141 KB (ELK direct) | ~1 KB own | 130 KB | 110 KB |

ELK layout, identical in every variant: 0.44–0.50 s here, 2.0–2.8 s at adopter size, on the main thread.

Without a GPU (software raster, as in CI) path A's frames on the adopter-sized graph at zoom 1: 121 ms ortho vs 54 ms bezier.

## Path A details (Cytoscape + ELK routes)

- Routes drawn with `curve-style: segments`/`round-segments`, `edge-distances: endpoints`, manual endpoints and per-edge weights/distances: within 0.05 units of ELK's here, 0.2 at adopter size; all axis-aligned; survive `cy.style()` (theme switch).
- ELK's compound boxes are up to ~500 units larger than Cytoscape's; matched with `min-width`/`min-height` per compound, deepest first (2.5-unit residual).
- Filters and hide need no re-route: routes avoid every box (after hiding the domains lane, 218 edges visible, sharing 0.081).
- Labels: on all 434 routed edges the label point lies on the path; 97% rotated with their segment; `round-segments` gives rounded corners.
- Bridges: an overlay canvas redrawn on Cytoscape's `render` event; zoom-gated (from 0.44) costs 0–1.9 ms per frame; every bridge at 5 px costs up to 59.5 ms p95 at adopter size; 0 visible at the page fit (0.052); 945 / 1,767 in one full-screen window at zoom 1.
- Not solved: edges to a node's own ancestor are always compound loops (19 / 72); Arrange — after a drag 69 of 70 edges lose right angles, semi-interactive ELK takes 308 ms / 2.3 s and moves the node back, interactive ELK throws with `INCLUDE_CHILDREN`; workable fallback: the moved node's edges become bezier (38–103 ms; through-box 8 → 53). Neighbourhood with hide keeps full-graph detours (path 1.25× / 2.2× Manhattan).
- Ports: `FIXED_SIDE` on compounds crashes ELK 0.12; side-midpoint ports bring back trunks (0.112 / 15, 10,827 crossings); `mergeEdges` changes little.
- Cost: no new dependency (drop `cytoscape-elk`, call elkjs directly); ~600–800 lines + ~300 test lines, 3–4 dev days; slices: `shared/cytoscape` (ELK runner, worker), `widgets/graph-viewer` (routes, overlay, stylesheet, test-handle readers `edgeRoutes()`, `jumps()`), `features/navigate-graph` (Arrange policy).

## Path B details

- **JointJS core 4.3.3 (MPL-2.0):** in the core — routers manhattan/metro/orthogonal/rightAngle, `jumpover`, embedding, ports, highlighters, paper transforms and wheel/pinch events, SVG only. Pan/zoom ourselves (~40 lines); PaperScroller/Navigator are JointJS+. No layout in the core; ELK positions + routes as vertices work. Licence: the wheel ships only `package.json` and the lock, the adopter's `npm ci` installs it; their published site carries minified MPL code (MPL §3.2: source available and notice); patches to JointJS files would be MPL (a reading, not legal advice). Restyling through the model is 622 ms / 4.5 s; through addClass highlighters 16 ms.
- **Own SVG from ELK:** ~70 lines of drawing + ~1.2 KB jumps; render in ms; CSS-class theming; needs our own pan/zoom/pinch, hover, level of detail and drag (~600–900 lines). Page-size fit view 29–41 ms per frame vs Cytoscape's 16.7.
- **maxGraph 0.24 (Apache-2.0):** redraws on every pan (186 ms p95 at adopter size); no jumps in the core (draw.io's `updateLineJumps` is in draw.io, ~250 lines, Apache-2.0); manhattan breaks with containers; pre-1.0.
- Not measured: libavoid-js (LGPL WASM, beta), Sprotty (EPL-2.0), AntV G6, Vue Flow; commercial yFiles, GoJS, JointJS+ excluded.

## Side findings

- `site_scaffold`'s lock resolves `cytoscape-elk` 2.3.0 to a nested elkjs 0.9.3; the pinned 0.12.0 is probably unused by the viewer (`beadloom-f2we`).
- ELK fans a hub's edges into a ~60-step staircase (`cli-commands`): a layout matter.
- Compound padding is set at the root only; a compound's title can sit under its first node.

## Artefacts

Prototypes, drivers, raw results and 70 screenshots are in the session scratchpad (`rnd/harness`, `rnd/B`, `rnd/shots`); the owner's report links the key screenshots.

## Probe: the map-like overview (2026-10-03)

- **Derived levels (chosen):** one ELK layout; collapsed boxes keep their ELK size, children removed (`cy.remove`/`restore`); aggregated route = medoid of the members' routes clipped between the two boxes. Box displacement 0 at every level and switch order, both graphs. Overview here: 12 boxes, 37 drawn edges (35 aggregated carrying 277 + 2), A2 0.001 / 0, 52 crossings; adopter-sized: 34 boxes, 443 drawn (376 aggregated), 12,223 crossings. Clips 1,065 / 0 failed, 3–6 ms. Switch 5–11 ms cold, ≤ 4 ms warm (14–20 / ≤ 12 at adopter size). Overview frame p50 16.7 ms (27.3 today) here, 16.5 ms (125.5 today) at adopter size.
- **ELK on the collapsed graph with positions handed in:** boxes move up to 6,940 units (30,264 at adopter size); interactive strategies move every box, throw with `INCLUDE_CHILDREN`, or time out; `fixed` routes nothing. Rejected.
- **Own router (A* + nudging):** 1.9 s / 20 s at adopter size, segments nudged into boxes. Rejected.
- **cytoscape-expand-collapse 4.1.1:** unmaintained, shrinks boxes (up to 1,885 units), bezier meta-edges. Rejected.
- **Level rule:** per-box "open what is in view" (parent open, overlaps the viewport, zoom past 1.3× fit, larger side ≥ N px; closes below 0.8 N): ≤ 0.2 ms per frame, switch 1.7–6 ms. Depth-by-zoom degenerates (L2 already draws 447 of 453). A selection opening its neighbours' boxes degenerates for a hub (`cli-commands` → 406 edges); open only its own ancestors.

## Probe: the staircase (2026-10-03)

- **Trunk + bus post-processed from ELK's sections (chosen):** `cli-commands` steps 36 → 1, lanes at 150 units 70 → 10, hub ink 57.6k → 7.2k; A2 against edges with no common endpoint 0.020 / 0 (unchanged); through-box 0; crossings +10.6%; no node moves; +8 ms (100–230 ms at adopter size before a spatial index). Bus on every node + trunks on degree ≥ 20: excess steps over the graph 403 → 76, nodes with > 5 steps 41 → 1.
- **ELK-side options:** `mergeEdges` (any form), FREE / three-sided ports, port alignment, priorities, own partition — no effect or a deeper staircase; `layerConstraint FIRST` throws; hyperedge ports collapse the fan but move all 130 nodes and add 13–56% crossings. Rejected (PRD non-goal on layout changes).
- **elkjs 0.9.3 vs 0.12:** identical layouts and routes; 0.9.3 ignores `shapeCoords`/`edgeCoords` (relative coordinates).
