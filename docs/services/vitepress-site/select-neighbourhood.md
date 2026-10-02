# Select neighbourhood (component)

A slice of the `features` layer of the VitePress site's Feature-Sliced layout. The layout and the
layer rule are described in [the site's page](../vitepress-site.md).

**Source:** `src/beadloom/site_scaffold/.vitepress/theme/features/select-neighbourhood/`

---

## Overview

A selected node's neighbourhood: the nodes a walk from it reaches along the drawn edges, and the
edges it walked. The toolbar's controls set three values, and the viewer owns them:

- **Depth:** 1 to 5 steps, or `all` for no limit. The value is a string, because it lives in the
  URL, and `depthLimit` reads a value it does not know as the nearest choice rather than failing.
- **Direction:** `out` follows the arrows, `in` goes against them, `both` is the union of the two
  walks. "Both" does not turn round at every step: a turning walk would reach the other dependents
  of every shared dependency, and at depth 2 that is nearly the whole graph.
- **Hide the rest:** hide what the walk leaves out instead of dimming it. The containers of what
  it reached stay either way.

The default is one step in both directions, with the rest dimmed. The walk follows every kind the
viewer draws as a line, `depends_on`, `uses`, `consumes` and `produces`, and each node carries its
fewest steps from the selection.

## Public API

- `neighbourhoodOf(focus, adjacency, { depth, dir })` returns `{ distances, edges }`: each node's
  distance from `focus`, and the keys of the edges walked. `adjacency` is `adjacencyOf`'s
  `{ out, in }`.
- `NEIGHBOURHOOD_DEFAULTS`, `DEPTH_CHOICES`, `DIRECTION_CHOICES`, `MAX_DEPTH`, `ALL_DEPTHS`,
  `depthLimit(value)`.
- `NeighbourhoodControls` (Vue component): props `depth`, `dir` and `hide`; event
  `change(key, value)`.

## Depends on

- `site-shared`, for `breadthFirst`.

## Tests

`src/beadloom/site_scaffold/e2e/neighbourhood.spec.js`: depth 2 outgoing shows the node, what
it reaches in two steps and those edges, with the rest dimmed; incoming shows what reaches it;
`all` walks without a limit; "Hide the rest" hides what is left out and keeps its containers;
clearing the selection shows the whole graph again.
