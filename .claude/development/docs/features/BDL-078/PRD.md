# PRD: BDL-078 — The viewer looks finished, and five defects are fixed

> **Status:** Draft
> **Created:** 2026-10-04
> **Source:** the owner's look at the portals after BDL-077 (2026-10-04); diagnosis and prototype in `RND.md`.

---

## Problem

After BDL-077 the viewer is structurally right and visually rough. The owner's findings, each
reproduced with its cause (`RND.md`):

- **Overview line widths are unreadable.** Aggregated edges grow continuously to about 7 px while
  closed boxes are 40–60 px tall; lines merge into slabs, counts are painted over by later edges,
  and a title that does not fit is drawn across arrowheads.
- **Arrowheads on thick lines break**, most after a bend: Cytoscape scales a head sublinearly with
  width (about 2× a thick line), the last run before the box is often shorter than the head, and
  the corner is effectively square at that zoom.
- **Bridges look like crutches:** erased notches, solid arcs on dashed lines, adjacent hops
  chaining together.
- **Junction dots sit beside the line:** the dot is at the polyline's corner, the stroke is
  rounded past it; dots are full-colour on a line faded by its direction gradient; 612 dots on
  this graph.
- **The activity metric says "1 commit in 30 days, cold" almost everywhere** (85 of 130 nodes
  cold, 33 at zero): it counts commits with thresholds made for un-squashed history, does not roll
  children up into their box, and names zero and 1–4 commits alike.
- The overall look (double status borders, dashed containers, gradient edges, a label on every
  selected edge) reads as unfinished.

Five open defects ride along: `beadloom-nh7h`, `beadloom-stcx`, `beadloom-ytcg`, `beadloom-jcng`,
`beadloom-76mk`.

## Impact

The team judges the tool by this picture, and adopters get the same viewer. A metric that says
"cold" on every node teaches readers to ignore the card. The five defects each give a wrong answer
or a crash in a path adopters use (a dev server, a node id, a manifest change, flat Python tests).

## Goals

- [ ] The overview reads at a glance: one thin line weight, counts on pills that nothing paints
      over, no two arrowheads overlapping, parallel lines separated by a visible gap, every box
      title readable and inside or beside its box without covering marks.
- [ ] Every arrowhead is whole: a constant size on screen, with a straight run before its box at
      least as long as the head.
- [ ] A followed line (hover, a selection's walk) is visibly on top of what it crosses; there are
      no bridges.
- [ ] A branch merges into its trunk with a rounded join on the stroke; there are no junction
      dots and no mark off the stroke.
- [ ] The node, container, edge and legend styling is consistent in light and dark, with no
      fallback colour and contrast at WCAG AA for text.
- [ ] The activity line on the card distinguishes the project's busiest nodes from its quiet ones
      on a squash-merged history: on this repository at least four levels are populated, and a box
      reflects its children.
- [ ] Performance stays within BDL-077's bounds; the browser suite, including the adopter
      fixtures, passes.
- [ ] The five defects are fixed, each with a test seen failing first.

## Non-goals

- Changing the layout, the map's level rule, or the bundling rules of BDL-077.
- Replacing Cytoscape.
- New viewer features beyond zoom-to-selection.

## Owner's rulings (2026-10-04)

1. **Bridges are removed entirely.** A followed edge is drawn on top with a casing instead.
2. **Trunk junctions are rounded merges with no dots.**
3. **The direction gradient along an edge is dropped;** arrowheads carry direction.
4. **No thick lines at all:** every line has one thin weight; an aggregated edge's count is on
   its pill, not in its width.
5. **Node status is a corner mark.**
6. **Activity counts changed lines over 30 days, with levels relative to the project;** a box
   rolls up its children; zero is named as no change.
7. **Selecting a node at the overview zooms to its neighbourhood.**
8. **The overview itself must read better** — on the prototype's screenshots too, arrowheads and
   lines run into each other and lines get in each other's way. The approach is chosen by a
   probe with screenshots (variants in `RND.md`), then the owner picks.

## User Stories

### US-1: Read the overview
**As** a team member opening the architecture, **I want** thin lines that keep out of each
other's way, with their counts on pills, **so that** I can read which domains depend on which.

- [ ] At the whole-graph fit every line has the one thin weight; no count pill overlaps a box, a
      title or another pill; no two arrowheads overlap; parallel runs keep a visible gap.
- [ ] Every closed box's title is fully visible.

### US-2: Trust the marks
**As** a reader, **I want** arrowheads, joins and highlights drawn without artefacts, **so that**
the picture does not look broken.

- [ ] Every arrowhead has a straight run before its box at least as long as itself, and a constant
      screen size.
- [ ] Every branch joins its trunk on the drawn stroke with a rounded merge; no dot is drawn.
- [ ] A hovered or walked edge is drawn above every edge it crosses.

### US-3: A card whose activity means something
**As** a team member reading a node's card, **I want** activity that separates busy nodes from
quiet ones, **so that** I know where the change is.

- [ ] On this repository at least four activity levels are populated and a box's level reflects
      its children.
- [ ] A node with no change in the window says so in words that differ from a low level.

### US-4: The five defects
- [ ] `beadloom-nh7h`: an incremental index and a fresh reindex resolve every import identically.
- [ ] `beadloom-stcx`: the portal's pages load under `vitepress dev`, checked by the dev check.
- [ ] `beadloom-ytcg`: a node named `__proto__` (and other object-prototype names) is drawn.
- [ ] `beadloom-jcng`: changing only a manifest (`go.mod`, `go.work`, `Package.swift`, a JVM
      layout) re-resolves the imports it governs on an incremental reindex.
- [ ] `beadloom-76mk`: flat Python tests (`tests/test_<module>.py`) bind to the node they test
      after `init`, and `init` names the test files it could not bind.

## Acceptance Criteria (overall)

- [ ] The browser suite holds each visual rule above with a case seen failing first, on this
      portal and the adopter-sized graph.
- [ ] `beadloom ci` rc 0; the required checks and both advisory browser jobs green on the PR.
- [ ] The owner has looked at the viewer in a browser before the merge — non-behavioural: a
      judgement of the look.
