# Architecture page (component)

A slice of the `pages` layer of the VitePress site's Feature-Sliced layout. The layout and the
layer rule are described in [the site's page](../vitepress-site.md).

**Source:** `site/.vitepress/theme/pages/architecture/`

---

## Overview

`ArchitectureMap`, the component the generated `architecture.md` mounts inside `<ClientOnly>`. It
is a thin page over the graph viewer: it renders `GraphViewer` in architecture mode and fills the
viewer's `panel` slot with the node card of the selected node. The page composes the card, so a
richer card can replace it without the viewer changing.

## Public API

- `ArchitectureMap` (Vue component, no props).

## Depends on

- `site-graph-viewer` (widgets).
- `site-graph-node` (entities), for `NodeCard`.
