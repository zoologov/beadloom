# Graph node (component)

A slice of the `entities` layer of the VitePress site's Feature-Sliced layout. The layout and the
layer rule are described in [the site's page](../vitepress-site.md).

**Source:** `src/beadloom/site_scaffold/.vitepress/theme/entities/graph-node/`

---

## Overview

A node of the architecture data file and what the viewer reads off it: its status, the risks a
change to it runs, and its container. The node card itself is the `site-node-card` widget.

- **Status.** One status per node, in this order: `violation` for a lint finding of severity
  `error`, `stale` for stale docs, `warned` for findings of any other severity. `NODE_STATUSES`
  gives each its theme tone, its mark and its legend text (BDL-078, owner's ruling 5): a status is
  a mark in the node's top right corner, `filled` for a violation (danger) and stale docs
  (warning), a `ring` for a warning, and never changes the border, which stays the layer's. A version 1 file
  carries only `lint_clean` and cannot tell an error from a warning, so a node it marks not clean
  is a violation.
- **Risks.** `risksOf(node)` names why a change to the node is risky, as the impact list shows it:
  no bound tests (`tests.count` is 0), stale docs (a doc whose pairs were compared and found out
  of date), docs not checked (a doc that is `unpaired`, `unverified` or `missing`), and open
  findings. A field a version 1 file does not carry is no risk.
- **Container.** A parent that is not a node of the file, or a node that names itself (the root
  service is `part_of` itself), is no container, because Cytoscape rejects a dangling or self
  parent. `containerOfKind` climbs to the nearest container of one kind, which the impact summary
  uses to name domains and services.

## Public API

- `NODE_STATUSES`, `statusOf(node)` returns `violation`, `stale`, `warned` or `null`;
  `statusesOf(nodes)`, `isFlagged(node)`.
- `RISKS`, `risksOf(node)` returns the risk phrases.
- `parentMapOf(nodes)` returns `{ id: parentId | null }`, a record without a prototype
  (`idRecord`, `site-shared`), so a node named `__proto__` or `constructor` is a key like any other
  (BDL-078 `beadloom-ytcg`); `containerOfKind(id, kind, nodeById, parents)`.
- `NodeStatusLegend` (Vue component): prop `statuses`, one sample per status drawn: a small card
  with a layer's border and the status's mark in its corner, filled or a ring.

How the canvas draws a node — a card in its layer's tone, corners at one radius on screen — is
the viewer's (`site-graph-viewer`, `lib/corners.js`, `lib/stylesheet.js`).

## Depends on

- `site-shared`, for the theme variables the legend samples use.
