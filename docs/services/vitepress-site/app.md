# App (component)

A slice of the `app` layer of the VitePress site's Feature-Sliced layout. The layout and the
layer rule are described in [the site's page](../vitepress-site.md).

**Source:** `site/.vitepress/theme/app/`

---

## Overview

The theme VitePress runs. It extends the default theme, mounts the Mermaid diagram viewer on every
page in the `doc-footer-before` slot, and registers by name the components the generated Markdown
mounts: `ArchitectureMap`, `LandscapeMap`, `DiagramViewer` and the seven dashboard panels. It holds
no behaviour of its own.

VitePress looks for `.vitepress/theme/index.js`. That file belongs to `vitepress-site` and only
re-exports this layer's default export.

## Public API

- `app/index.js` default export: the VitePress `Theme` object.

## Depends on

- `site-architecture-page`, `site-landscape-page` (pages).
- `site-dashboard`, `site-diagram-viewer` (widgets).
