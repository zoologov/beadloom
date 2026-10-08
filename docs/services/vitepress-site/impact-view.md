# Impact view (component)

A slice of the `features` layer of the VitePress site's Feature-Sliced layout. The layout and the
layer rule are described in [the site's page](../vitepress-site.md).

**Source:** `src/beadloom/site_scaffold/.vitepress/theme/features/impact-view/`

---

## Overview

The impact mode: everything a change to the selected node reaches, without a depth limit. The
toolbar's **Impact** button switches between it and the neighbourhood. The walk goes from the
selected node to what depends on it, then to what depends on those, and so on. Each reached node
is drawn in the ring of its fewest steps: the selection is ring 0, direct dependents ring 1, and
every distance from the last tone on shares that tone. Which end of an edge depends on the other
is the mode's table (`site-graph-edge`, `site-landscape-data`), so one walk serves both modes.

- **Architecture** (`lib/impact.js`). The walk goes backwards along `depends_on`, `uses` and
  `consumes`. The summary gives the count, the rings, the domains and services that hold the
  reached nodes, each layer boundary the walked edges cross with a count, and the risky nodes:
  no bound tests, stale docs, docs not checked, open findings. Since BDL-080 a boundary is keyed
  by layer, the pair (rule, rank), so two rules' ranks are never one boundary. Its `from` and
  `to` are the layers' captions, which name the rule by its title where more than one rule is
  drawn, and the boundaries are listed in the layers' order: every rule's top to bottom, the rules
  in the file's order. The commands to copy are
  `beadloom why <ref>` and, when the node has a source, `beadloom impact <source>`.
- **Landscape** (`lib/contractImpact.js`). The walk goes along each contract from its producer to
  its consumers, for every protocol, so a change reaches the consumers of what a service produces
  and never its producers. The summary gives the count, the rings, the contracts crossed, their
  protocols, the broken contracts on the path, and each reached service with a broken or
  unverified contract. The commands to copy are `beadloom why <ref>` and `beadloom ctx <ref>`:
  `impact` takes a path or a symbol, and a service on the map has neither.

Both summaries open with the statement that this is the graph's view and not a reading of the
code: the architecture follows edges from imports and declarations, the landscape the contracts
the reconciler recorded. A click on a node in the risk list selects it.

## Public API

- `impactOf(focus, dependents)` returns `{ distances, edges }`: each reached node by its fewest
  steps, and the edges walked.
- `impactSummary(focus, impact, { nodeById, parents, layers, edges })` and `DEPENDENCY_WALK`.
- `contractImpactSummary(focus, impact, { edges, contracts })` and `CONTRACT_WALK`.
- `IMPACT_VIEW`, `RING_TONES`, `ringOf(distance)`.
- `ImpactButton` (Vue component): prop `active`, event `toggle`.
- `ImpactSummary` (Vue component): props `summary` and `source`, event `select(id)`.

## Depends on

- `site-graph-node`, `site-graph-edge`, `site-layer`, `site-landscape-data` (entities).
- `site-shared`, for `breadthFirst`, `shellQuote`, the theme variables of the ring swatches and
  `CopyCommand`.

## Tests

`src/beadloom/site_scaffold/e2e/impact.spec.js` on the architecture: the rings and the summary,
each risky node marked and listed, the statement and the two commands, the rings drawn in real
colours and removed on leaving the mode, and each doc status listed as its risk.
`src/beadloom/site_scaffold/e2e/landscape-impact.spec.js` on the landscape: every service
reached however far, consumers and never producers, the contracts, protocols and broken ones on
the path, the services at risk, and, on the landscape the portal serves, a producer reaching
its consumer. The landscape cases grow the served landscape from a seeded contract, so five of
the six run on a project whose own landscape is empty; the sixth needs a contract the portal
serves and skips, naming that shape, where there is none.
