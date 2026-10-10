# App (component)

A slice of the `app` layer of the VitePress site's Feature-Sliced layout. The layout and the
layer rule are described in [the site's page](../vitepress-site.md).

**Source:** `src/beadloom/site_scaffold/.vitepress/theme/app/`

---

## Overview

The theme VitePress runs. It extends the default theme, mounts the Mermaid diagram viewer on every
page in the `doc-footer-before` slot and the "Powered by Beadloom" footer in the `layout-bottom`
slot, and registers by name the components the generated Markdown
mounts: `ArchitectureMap`, `LandscapeMap`, `DiagramViewer` and the seven dashboard panels. It holds
no behaviour of its own.

`app/styles/nav-logo.css` (BDL-080 S4e) is the theme's one global stylesheet of its own. It
paints the nav logo VitePress draws in the text's colour when `.vitepress/config.mjs` marked it
`data-monochrome`, which it does for an SVG logo drawn in `currentColor`: the image's own drawing
gets no room, the box is filled with `currentColor` and masked by the file, at 32 by 32 pixels.
An image cannot inherit the page's colour, and such a logo would be black on the dark theme.

VitePress looks for `.vitepress/theme/index.js`. That file belongs to `vitepress-site` and only
re-exports this layer's default export.

## Public API

- `app/index.js` default export: the VitePress `Theme` object.

## Depends on

- `site-architecture-page`, `site-landscape-page` (pages).
- `site-dashboard`, `site-diagram-viewer`, `site-powered-by` (widgets).
