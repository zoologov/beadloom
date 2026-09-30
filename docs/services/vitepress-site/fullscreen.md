# Full screen (component)

A slice of the `features` layer of the VitePress site's Feature-Sliced layout. The layout and the
layer rule are described in [the site's page](../vitepress-site.md).

**Source:** `site/.vitepress/theme/features/fullscreen/`

---

## Overview

Full screen for one element through the Fullscreen API. When the API is missing or refuses, the
same element is pinned over the viewport by CSS, and `fallback` says so; the viewer marks its root
with `data-fullscreen-fallback="on"` then. The graph viewer hands it its whole space, so the toolbar,
the canvas and the panel go full screen together.

## Public API

- `useFullscreen(targetRef, { onChange })` returns `active`, `fallback`, `toggle()` and `exit()`.
- `FullscreenButton` (Vue component): prop `active`, event `toggle`.

## Depends on

- `site-shared`.
