# Diagram viewer (component)

A slice of the `widgets` layer of the VitePress site's Feature-Sliced layout. The layout and the
layer rule are described in [the site's page](../vitepress-site.md).

**Source:** `site/.vitepress/theme/widgets/diagram-viewer/`

---

## Overview

`DiagramViewer` enhances every Mermaid SVG a page renders with pan, wheel zoom, reset and full
screen (svg-pan-zoom and the Fullscreen API). It renders no markup of its own. It also rewrites a
diagram's click targets under the site's base path. `ui/diagram-viewer.css` styles the frame and its
controls and is imported by the slice's `index.js`.

## Public API

- `DiagramViewer` (Vue component, no props).

## Depends on

- `site-shared`.
