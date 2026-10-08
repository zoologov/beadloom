# URL state (component)

A slice of the `features` layer of the VitePress site's Feature-Sliced layout. The layout and the
layer rule are described in [the site's page](../vitepress-site.md).

**Source:** `src/beadloom/site_scaffold/.vitepress/theme/features/url-state/`

---

## Overview

A view's state read from and written to the page's query string. It is read once, when the viewer
is set up, and every change is written back with `history.replaceState`, keeping the history
VitePress stores. Only values that differ from their defaults are written, so an untouched view
keeps a clean URL, and parameters the state does not own are kept. A boolean is written as `1`
or `0`. An empty value whose default is not empty is written empty: on a node page the selection's
default is the page's node, so a cleared selection is written as `focus=`, and a reload does not
bring the node back.

The graph viewer's keys:

- the filters of its mode: `kind`, `domain`, `layer`, `violations` and `q` on the architecture;
  `protocol`, `verdict` and `problems` on the landscape;
- `focus` (the selected node), `depth` (`1` to `5` or `all`), `dir` (`out`, `in` or `both`),
  `hide` (hide rather than dim what the walk leaves out) and `view` (`impact`, or the
  neighbourhood by default).

The data mode is not a key: it is the page's.

Where more than one layer rule is drawn, `layer` carries the layer's label, the rule's name and
the layer's (`site-fsd-layers: widgets`), never the rule's title, so a link stays good when a
title is reworded. A link naming a bare layer is read by the graph viewer as that layer and
rewritten to the label (BDL-080 S1f, `site-filter-graph`).

## Public API

- `readQuery(search, defaults)` and `writeQuery(search, state, defaults)`.
- `useUrlState(defaults)` returns a reactive state object bound to the URL.

## Depends on

- `site-shared`.

## Tests

`src/beadloom/site_scaffold/e2e/url-state.spec.js`: a linked view opens in the state its query
names; a query cannot switch the architecture page to another data mode; a change in the toolbar
is written to the URL and survives a reload; and since BDL-080 a link naming a layer by its bare
name opens on that layer where two or more rules are drawn, and a bare name two rules share opens
on the first rule's layer by name.
