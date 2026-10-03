# PRD: BDL-077 — The viewer draws edges like a classic diagram

> **Status:** Draft
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
- [ ] No edge is indistinct: 0 edges more than half shared (today 22), and the mean shared share
      at most 3% (today 14.4%), on this repository's graph and the adopter-sized one.
- [ ] Edges are drawn as right-angled routes with arrowheads that enter a box on a side.
- [ ] Bridges show where a highlighted edge (selection, neighbourhood, impact, hover) crosses
      another edge, so the highlighted line can be followed.
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
- Bridges on every crossing at every zoom (measured: thousands per graph, up to 500 per screen;
  they read as texture).
- Changing ELK's layer assignment or node order.

## Open questions for the owner

These decide the user stories marked *pending*:

1. **Arrange (dragging a box).** A second ELK run puts the node back, so routes cannot follow a
   drag. Options: the moved node's edges become curves; routes are off while arranging; Arrange
   is removed.
2. **Edges from a node to its own container** (19 of 453). Cytoscape draws them as loops in any
   style. Options: keep loops; hide them; show them in the card only.
3. **Bridges**: only on highlighted edges (recommended) or on all edges above a zoom.
4. **The overview**: at the whole-graph fit ELK packs parallel edges under a pixel apart and
   they merge into grey bands. Whether this work item includes a probe of fewer edges in the
   overview (e.g. edges between containers merged into one line with a count when zoomed out).
5. **High-degree nodes**: ELK fans their edges into a staircase (about 60 steps from
   `cli-commands`). Whether this work item addresses the layout, or leaves it.

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

### US-2: Follow a highlighted line through crossings
**As** a team member tracing a dependency, **I want** bridges where the highlighted edges cross
other edges, **so that** I can follow one line across a busy area.

**Acceptance criteria:**
- [ ] With a node selected (neighbourhood or impact), each crossing of a highlighted edge with
      another drawn edge shows a bridge on the highlighted edge.
- [ ] With nothing highlighted, no bridges are drawn (*pending* question 3).
- [ ] Bridges follow the theme in light and dark, and no fallback colour is drawn.

### US-3: Keep every existing mode working
**As** a user of the viewer, **I want** filters, hide, neighbourhood, impact, node pages, URL
state and full screen to behave as before, **so that** nothing I rely on regresses.

**Acceptance criteria:**
- [ ] The existing 101 browser cases pass on this repository's portal, and the shipped suite
      passes on the six adopter fixtures.
- [ ] Hiding nodes leaves the remaining routes intact (no re-layout needed).

### US-4: Arrange still works (*pending* question 1)
**As** a user arranging the picture, **I want** a moved box's edges to stay attached in a way
I can read, **so that** arranging does not break the diagram.

### US-5: The page stays responsive during layout
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
      decisions on the pending questions.
