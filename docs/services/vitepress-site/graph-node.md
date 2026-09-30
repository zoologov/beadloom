# Graph node (component)

A slice of the `entities` layer of the VitePress site's Feature-Sliced layout. The layout and the
layer rule are described in [the site's page](../vitepress-site.md).

**Source:** `site/.vitepress/theme/entities/graph-node/`

---

## Overview

A node of the architecture data file and what the viewer reads off it: its status (a lint finding,
or stale docs), its container, and its card. A container that is not a node of the file, or a node
that names itself (the root service is `part_of` itself), is no container, because Cytoscape rejects
a dangling or self parent.

## Public API

- `statusOf(node)` returns `violation`, `stale` or `null`; `isFlagged(node)`.
- `parentMapOf(nodes)` returns `{ id: parentId | null }`.
- `NodeCard` (Vue component): props `node` and `layerName`; events `select(id)` and `close`.

## Depends on

- Nothing inside the site.
