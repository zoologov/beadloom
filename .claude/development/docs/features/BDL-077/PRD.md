# PRD: BDL-077 — The viewer draws edges like a classic diagram

> **Status:** Done
> **Created:** 2026-10-03
> **Source:** owner's ask on 2026-09-30 after BDL-076 PR 1 (`beadloom-rcnz`); measured in R&D on 2026-10-03 (`RND.md` in this folder).

---

## Problem

The architecture viewer draws every edge as a Cytoscape curve from the centre of one box to the
centre of the other. Measured on this repository's graph (130 nodes, 453 drawn edges):

- 232 of 453 edges (51%) pass through a box they do not connect; 678 of 1,300 on an
  adopter-sized graph.
- 14.4% of an edge's middle lies within 4 layout units of another edge, and 22 edges are more
  than half shared with another (the BDL-076 A2 metric, reproduced exactly).
- 9,407 edge crossings, with no way to follow one line through a crossing.

The owner wants edges that route around blocks, bridges where edges cross, and a look closer to
classic diagrams (draw.io, Visio).

ELK already computes orthogonal routes around every box on each layout (`edgeRouting:
ORTHOGONAL`); `cytoscape-elk` keeps only node positions and discards them.

## Impact

- **The team** reads dependencies in the viewer for estimates and reviews; lines through boxes
  and indistinct parallel curves make "who depends on whom" a guess once more than a handful of
  edges are on screen.
- **Adopters** get the same viewer through `beadloom docs site`; their graphs are larger (the
  adopter-sized measurement is 3x ours) and degrade faster.
- Without a change the viewer stays usable mainly through the neighbourhood and impact modes,
  and the overview stays a picture rather than a diagram.

## Goals

- [ ] No drawn edge passes through a box it does not connect (today 232 of 453), except edges
      from a node to its own container, which are a stated decision.
- [ ] No edge is indistinct: counted against edges with no common endpoint (an edge shares its
      trunk with its siblings by design), 0 edges more than half shared (today 22) and the mean
      shared share at most 3% (today 14.4%), on this repository's graph and the adopter-sized one.
      *(Amended by the owner with the RFC, Q3.)*
- [ ] Edges are drawn as right-angled routes with arrowheads that enter a box on a side.
- [ ] Bridges show where a highlighted edge (selection, neighbourhood, impact, hover) crosses
      another edge, so the highlighted line can be followed; no bridges on other edges.
- [ ] The whole-graph view shows top-level boxes and aggregated edges, one per pair of boxes
      (37 instead of 453 on this repository's graph; at most 100 on any graph, weaker ones
      counted on their box), and zooming in opens boxes level by level down to every node and
      routed edge, without the layout jumping between levels.
- [ ] No node's edges form a staircase: a node with 20 or more drawn edges leaves each side in one
      channel per direction, and its edges cross a line 150 units from it in no more lanes than
      the number of top-level boxes they lead to, plus one per edge into its own box
      (`cli-commands`: at most 11; today 70). *(Amended by the owner with the RFC, Q3.)*
- [ ] The viewer stays as fast as today: frame time at the whole-graph fit and at zoom 1 no
      worse than today's on both graphs; first render at most 15% slower.
- [ ] The page stays responsive while ELK lays out (0.5 s here, 2.7 s at adopter size today, on
      the main thread).
- [ ] Filters, hide, neighbourhood, impact, node pages, URL state and full screen keep working,
      and the 101 browser cases pass, extended for the new behaviour.

## Non-goals

- Replacing Cytoscape (measured: JointJS core and maxGraph fail on our graph; drawing SVG
  ourselves stays the fallback if path A stalls).
- Editing the diagram with live re-routing.
- Ports pinned to fixed points on a side (Visio-style); ELK 0.12 crashes on them with
  compounds, and they bring back shared trunks.
- Arrange (dragging boxes): removed by the owner's ruling.
- Bridges on every crossing at every zoom (measured: thousands per graph, up to 500 per screen;
  they read as texture).
- Changing ELK's layer assignment or node order.

## Owner's rulings (2026-10-03)

1. **Arrange is removed.** Boxes are not draggable; routes never go stale.
2. **Edges from a node to its own container stay loops**, as today (19 of 453).
3. **Bridges only on highlighted edges**: neighbourhood, impact, hover.
4. **The overview works like a map** (semantic zoom): zoomed out, fewer and larger things —
   top-level boxes and aggregated edges between them; zooming in, boxes open and detail fills
   in, down to every node and every routed edge. Fewer edges on screen also keeps bridges few.
5. **The staircase from high-degree nodes is solved in this work item**; the approach is chosen
   by measurement in the RFC (candidates below).

Measured for ruling 4 on this repository's graph: at the domain level (12 top-level boxes) the
453 drawn edges become 41 aggregated edges (the heaviest carries 30), and 165 edges stay inside
a domain until it is opened. `cli-commands`, the largest fan (70 edges), becomes 10 aggregated
edges at that level.

Candidates for ruling 5, to be measured in the RFC: aggregation at the overview (ruling 4
already turns the 70-edge fan into 10); ELK edge merging for a node above a fan-out threshold,
so its edges share one trunk and branch near their targets (a bus); ports spread over more than
one side of the hub; and lower ELK priority for a composition root's edges, so they stop pulling
the layout.

## User Stories

### US-1: Follow a dependency without lines through boxes
**As** a team member reading the architecture, **I want** every edge to run around the boxes
it does not connect, at right angles, **so that** I can see which box an edge leaves and which
it enters.

**Acceptance criteria** (browser cases; names fixed in the RFC):
- [ ] On this repository's graph, no drawn edge's route crosses a box it does not connect,
      except the declared exception for edges to a node's own container.
- [ ] Every routed edge is drawn as axis-aligned segments that match ELK's route.
- [ ] Every routed edge ends with an arrowhead on a side of its target box.
- [ ] The A2 metric on the drawn routes: 0 edges more than half shared.

### US-2: Read the overview like a map
**As** a team member opening the architecture, **I want** the whole-graph view to show the
top-level boxes and one aggregated edge per pair of boxes, and more detail as I zoom in,
**so that** the overview is readable and detail appears where I look.

**Acceptance criteria:**
- [ ] At the whole-graph fit only top-level boxes and aggregated edges are drawn, each
      aggregated edge showing how many edges it carries.
- [ ] Zooming into a box opens it and draws its children and their edges; the boxes do not move
      between levels.
- [ ] Selecting a node (search, URL, card link, neighbourhood, impact, node page) opens every
      box needed to show it and its highlighted edges, whatever the zoom.

### US-3: Follow a highlighted line through crossings
**As** a team member tracing a dependency, **I want** bridges where the highlighted edges cross
other edges, **so that** I can follow one line across a busy area.

**Acceptance criteria:**
- [ ] With a node selected (neighbourhood or impact), each crossing of a highlighted edge with
      another drawn edge shows a bridge on the highlighted edge.
- [ ] With nothing highlighted, no bridges are drawn.
- [ ] Bridges follow the theme in light and dark, and no fallback colour is drawn.

### US-4: Keep every existing mode working
**As** a user of the viewer, **I want** filters, hide, neighbourhood, impact, node pages, URL
state and full screen to behave as before, **so that** nothing I rely on regresses.

**Acceptance criteria:**
- [ ] The existing 101 browser cases pass on this repository's portal, and the shipped suite
      passes on the six adopter fixtures.
- [ ] Hiding nodes leaves the remaining routes intact (no re-layout needed).
- [ ] Boxes cannot be dragged; the Arrange control is gone.

### US-5: No staircase from a high-degree node
**As** a team member reading a hub such as `cli-commands`, **I want** its many edges drawn as
a compact bundle, **so that** one node does not take half the screen.

**Acceptance criteria:**
- [ ] On this repository's graph, `cli-commands`'s edges at full detail fit within the bound
      the RFC sets, and stay distinguishable by the A2 metric.

### US-6: The page stays responsive during layout
**As** a user opening a large architecture, **I want** the page to respond while the layout
is computed, **so that** a 3x graph does not freeze the tab for seconds.

**Acceptance criteria:**
- [ ] ELK runs off the main thread; the toolbar responds during layout on the adopter-sized
      graph.

## Acceptance Criteria (overall)

- [ ] The numbers in Goals hold on this repository's graph and on the adopter-sized graph,
      measured by a check in the suite (not by hand).
- [ ] The viewer uses the elkjs version the package pins (today `cytoscape-elk` pulls a nested
      0.9.3; `beadloom-f2we`) — non-behavioural: a dependency fact, checked by a self-check.
- [ ] Frame-time and first-render bounds hold in the CI browser run — non-behavioural where CI
      has no GPU: the bound is stated per environment.
- [ ] Docs: the viewer's slice pages and the portal guide describe the routes, bridges and the
      owner's rulings (no Arrange, loops, bridges on highlighted edges, the map-like overview).
