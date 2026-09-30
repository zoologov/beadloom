# Landscape page (component)

A slice of the `pages` layer of the VitePress site's Feature-Sliced layout. The layout and the
layer rule are described in [the site's page](../vitepress-site.md).

**Source:** `site/.vitepress/theme/pages/landscape/`

---

## Overview

`LandscapeMap`, the component the generated `landscape.md` mounts: the interactive map of the
contracts between services, drawn with Cytoscape and ELK, with protocol and verdict filters and a
contract card. `lib/landscapeTheme.js` holds its colours, geometry and layout options.

It is not built on the graph viewer yet, and its stylesheet still hands Cytoscape `var(--vp-…)`
colours for the neutral chrome. Both change when the landscape becomes the viewer's second mode
(BDL-076 A4).

## Public API

- `LandscapeMap` (Vue component, no props).

## Depends on

- `site-landscape-data` (entities).
