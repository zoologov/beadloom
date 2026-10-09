# Diagram viewer (component)

A slice of the `widgets` layer of the VitePress site's Feature-Sliced layout. The layout and the
layer rule are described in [the site's page](../vitepress-site.md).

**Source:** `src/beadloom/site_scaffold/.vitepress/theme/widgets/diagram-viewer/`

---

## Overview

`DiagramViewer` enhances every Mermaid SVG a page renders with pan, wheel zoom, reset and full
screen (svg-pan-zoom and the Fullscreen API). It renders no markup of its own. It also rewrites a
diagram's click targets under the site's base path: a target under `/services/`, `/domains/`,
`/features/`, `/other/` or `/docs/` is an in-site page. `ui/diagram-viewer.css` styles the frame
and its controls and is imported by the slice's `index.js`.

The Mermaid plugin renders a diagram again whenever an attribute of `<html>` changes, the theme
switch among them, and replaces the SVG inside the same container. The mark of an enhanced diagram
is therefore on the SVG, and a mutation observer enhances each new SVG. Before BDL-076 A4 the
mark sat on the container, and a re-rendered diagram lost its pan, its controls and its
base-aware click targets.

## Public API

- `DiagramViewer` (Vue component, no props).

## Depends on

- `site-shared`.

## Tests

`src/beadloom/site_scaffold/e2e/diagram-links.spec.js`: a landscape diagram link to a page
under `other/` carries the base path, and a diagram rendered again by a theme switch keeps its
links and its controls. Since BDL-080 S1d the first case does not need a node under `other/` in
the served landscape, which this repository no longer has: it moves one drawn node's click target
under `/other/` in the page's bundle and asserts that the link carries the base.
