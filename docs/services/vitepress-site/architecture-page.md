# Architecture page (component)

A slice of the `pages` layer of the VitePress site's Feature-Sliced layout. The layout and the
layer rule are described in [the site's page](../vitepress-site.md).

**Source:** `site/.vitepress/theme/pages/architecture/`

---

## Overview

`ArchitectureMap`, the component the generated `architecture.md` and every node page mount inside
`<ClientOnly>`. It is a thin page over the graph viewer: it renders `GraphViewer` in architecture
mode and fills the viewer's `panel` slot with the node card of the selected node. The page
composes the two widgets, because a widget does not import another.

A node page mounts it as `<ArchitectureMap focus="<ref>" :depth="1" height="60vh" />`, in the
place the scoped Mermaid diagram had. The viewer opens with the page's node selected, its
neighbourhood marked and its card open, and the reader moves on from there with every control the
architecture page has. A node of any kind has a page, `other/` included.

## Public API

- `ArchitectureMap` (Vue component). Props: `focus`, `depth` and `height`, each passed to the
  viewer; without them the viewer's defaults apply.

## Depends on

- `site-graph-viewer`, `site-node-card` (widgets).

## Tests

`site/e2e/node-page.spec.js`: a node page opens focused on its node, every toolbar control works
from it, a cleared selection stays cleared after a reload, a page under `other/` opens the same
way, and full screen shows the tools, the card and the legend.
