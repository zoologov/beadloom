# CONTEXT: BDL-077 — The viewer draws edges like a classic diagram

> **Status:** Approved
> **Created:** 2026-10-03
> **Last updated:** 2026-10-03

---

## Goal

The architecture viewer draws ELK's orthogonal routes around every box, reads like a map at the
overview and opens detail where the user zooms, bundles a node's edges into a trunk and bus instead
of a staircase, and shows bridges where highlighted edges cross — from one ELK layout, so nothing
moves.

## Key Constraints

- **One ELK layout; levels, bundles and bridges are derived from it.** No re-layout per level, per
  selection or per filter; box displacement across levels is 0.
- **ELK runs in a Web Worker, elkjs 0.12.0 called directly;** `cytoscape-elk` is removed. Results in
  root coordinates (`elk.json.shapeCoords`/`edgeCoords: ROOT`).
- **Cytoscape 3.34.1 stays;** literal colours only; exact pins.
- **The data file does not change** (schema 2, every v1 key). Aggregation and levels are computed in
  the browser from `edges` and `part_of`. No Python node is in scope.
- **Feature-Sliced Design:** layers `app`, `pages`, `widgets`, `features`, `entities`, `shared`; a
  layer imports only below it; a slice only through its `index.js`; `site-fsd-layers` judges it.
- **Browser tests assert state through `window.__beadloomViewer`, not pixels;** every behaviour
  lands with a case seen failing first; the PRD's numbers are checked by a suite case on this
  repository's portal and an adopter fixture. Frame bounds are stated per environment (CI has no
  GPU).
- **No project vocabulary hard-coded** in anything that ships; the same canvas serves the
  landscape mode.
- **Commits and suites:** commit only your own files by explicit path under
  `bd merge-slot acquire/release --holder <bead-id>` (proceed only on exit 0); never pipe a command
  whose exit code is the answer; run long suites in the foreground. Restore
  `.beadloom/metrics_history.json` if a run rewrites it.
- **The owner looks at the viewer in a browser before the PR is merged;** merge on the owner's word.

## Code Standards

### Language and Environment

- JavaScript (ES modules) and Vue 3 SFCs for the viewer, no TypeScript; Python 3.10+ only where a
  self-check or the suite needs it.
- Node 22 (`$HOME/.nvm/versions/node/v22.9.0/bin` locally); npm with the committed lockfile; uv.

### Methodologies

| Methodology | Application |
|---|---|
| TDD | each behaviour with its Playwright case seen red first; pure functions (routes, bundles, levels, bridges) driven with crafted inputs |
| Clean Code | pure functions over ELK output in `lib/`, Cytoscape effects in `model/`; SRP, DRY, KISS |
| Architecture | FSD as above; `services -> application -> domains -> infrastructure` for any Python touched |

### Testing

- **Browser:** Playwright on `vitepress build` served by `vitepress preview`, Chromium; the shipped
  suite also on the six adopter fixtures (`site-adopters`).
- **Python:** pytest + pytest-cov where a self-check changes; coverage ≥ 80% on changed modules.

### Code Quality

- `uv run ruff check src/ tests/`, `uv run mypy src/`, `npm run docs:build`, the browser suite,
  `beadloom ci` rc 0.

### Restrictions

- No `console.log`; no global state beyond the documented test handle.
- No `Any`/`# type: ignore` without a reason; no bare `except:`; pathlib; `safe_load`.

## Architectural Decisions

| Date | Decision | Reason |
|---|---|---|
| 2026-10-03 | Keep Cytoscape; draw ELK's orthogonal routes (path A) | R&D: through-box 232 → 0, indistinct 22 → 0; JointJS core and maxGraph fail on this graph; own SVG is the fallback |
| 2026-10-03 | Arrange (dragging boxes) removed | Owner: routes never go stale |
| 2026-10-03 | Edges from a node to its own container stay loops | Owner |
| 2026-10-03 | Bridges only on highlighted edges (hover, neighbourhood, impact) | Owner; bridges on every crossing read as texture |
| 2026-10-03 | A map-like overview: levels derived from one layout, aggregated routes from member routes, open-what-is-in-view at N = 600 px (1.3× fit floor, 0.8 hysteresis), a selection opens its own ancestors, a walk opens its boxes | Owner rulings 4 and Q2; probe: displacement 0, overview 453 → 37 edges, frame 27 → 17 ms (125 → 17 at adopter size) |
| 2026-10-03 | Aggregated edges per unordered pair; weak ones hidden only above a budget of 100 drawn, at the smallest weight that fits, counted on the box, all drawn on hover/selection of the box | Owner Q1 with the coordinator's refinement |
| 2026-10-03 | Trunk + bus post-processed from ELK's sections (bus on every node, trunks at ≥ 20 drawn edges, hub-to-hub on the source's trunk) | Probe: `cli-commands` 36 steps / 70 lanes → 1 / 10; no node moves; ELK-side options rejected |
| 2026-10-03 | PRD goals restated: A2 counted against edges with no common endpoint; hub bound in channels and lanes, not pixel width | Owner Q3 |
| 2026-10-03 | Loops onto the root wrapper hidden at the overview | Owner Q4 |
| 2026-10-03 | The data file does not change | Everything needed is in `edges` and `part_of`; keeps Python out of scope |
| 2026-10-03 | The hub lane bound counts the lanes of the edges whose trunk or bus belongs to the node; edges another hub sends arrive on the sender's trunk in lanes of their own | Coordinator, after E3 measured that the literal reading conflicts with "hub-to-hub edges ride the source's trunk" at adopter size (18 hub sides over, busiest 50 vs 29) while every hub keeps one channel per side and direction; surfaced to the owner, who may overrule. |
| 2026-10-04 | **The reading above did not hold** — T measured that excluding edges another hub sends still leaves 15 sides over the bound and 10 nodes with two channels at adopter size, and a box with ≥ 20 drawn edges (`mcp-server`) is not bundled at all. The owner's bound (Q3) stands as written; the bundler is fixed to meet it (`beadloom-m6k7.3` boxes, `beadloom-m6k7.4` adopter-size leaves) before review. | T (`beadloom-lb1v`) contradicted E3's account with a measurement |
| 2026-10-04 | The owner's literal hub bound is met: boxes are bundled like leaves (`.3`); incoming trunks, edges in two trunks, bus port shifts and joins (`.4`) — every busy node on this portal and on three adopter-sized graph shapes within its bound with one channel per side and direction; no node moved | `beadloom-m6k7.3` `bde3684c`, `beadloom-m6k7.4` `1021f1b9`; a two-rank graph keeps one second channel (`beadloom-m6k7.5`, P2) |
| 2026-10-03 | Dimmed edges are drawn opaque in a colour faded towards the background, not at low opacity | E3: ten see-through edges on one trunk added up to about four-fifths strength |
| 2026-10-03 | An edge with a closed box as an end joins its pair's aggregated edge, even when both ends are drawn as themselves | E4: the data file now carries 25 edges declared between the boxes themselves; drawn as themselves they put a second line beside each pair's aggregated edge (61 drawn at the overview, 34 folded), against PRD US-2's "only top-level boxes and aggregated edges" |
| 2026-10-03 | A node a selection, a walk or the search reveals is drawn with its own edges: a revealed box is drawn open | E4: a closed box folds its own edges into aggregated ones, so a walk that reached a box lost its walked edges (5 neighbourhood and 3 node-page cases red) |
| 2026-10-03 | Impact and a neighbourhood the reader changed open the whole walk; the neutral neighbourhood (depth 1, both, dimmed) opens it too, unless the focus is a hub (20 drawn edges, the trunk degree) | E4: every selection carries a neighbourhood here, so RFC D4's "a hub's selection alone" can only mean the neutral one; PRD US-2 asks a selection to show its highlighted edges, which the hub's aggregated edges do |
| 2026-10-03 | Fit measures the shapes, not their labels | E4: a closed box's title keeps its size on screen, so in layout units it grows as the view zooms out; measured with labels, Fit pressed after zooming gave 0.05183 against 0.05224 at load |
| 2026-10-03 | The test handle takes one action, `revealNodes(ids)`; a case about the whole graph opens every box through it | E4: no reader gesture opens every box at once (only what is in view opens), and 47 cases read every node or edge; opening them keeps those cases' bars rather than reading the overview's 12 nodes |

## Related Files

Discover with `beadloom ctx vitepress-site`, `beadloom ctx site-graph-viewer` and `axes.md`
Supplement A.

## Current Phase

- **Phase:** Development
- **Current bead:** see ACTIVE.md
- **Blockers:** none
