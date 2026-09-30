# URL state (component)

A slice of the `features` layer of the VitePress site's Feature-Sliced layout. The layout and the
layer rule are described in [the site's page](../vitepress-site.md).

**Source:** `site/.vitepress/theme/features/url-state/`

---

## Overview

A view's state read from and written to the page's query string. It is read once, when the viewer
is set up, and every change is written back with `history.replaceState`, keeping the history
VitePress stores. Only values that differ from their defaults are written, so an untouched view
keeps a clean URL, and parameters the state does not own are kept.

The graph viewer's keys are `kind`, `domain`, `layer`, `violations`, `q`, `focus`, `depth`, `dir`
and `mode`.

## Public API

- `readQuery(search, defaults)` and `writeQuery(search, state, defaults)`.
- `useUrlState(defaults)` returns a reactive state object bound to the URL.

## Depends on

- `site-shared`.
