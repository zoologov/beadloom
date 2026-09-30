# Node card (component)

A slice of the `widgets` layer of the VitePress site's Feature-Sliced layout. The layout and the
layer rule are described in [the site's page](../vitepress-site.md).

**Source:** `site/.vitepress/theme/widgets/node-card/`

---

## Overview

`NodeCard`, the architecture card: everything the data file says about one node. The
architecture page puts it in the viewer's panel for the selected node. The landscape has a card of
its own, the service card of `site-landscape-page`.

In order, the card shows:

- the node's id and summary; its kind, lifecycle and tags;
- its layer, and whether the layer is the node's own tag or inherited through `part_of`;
- its source, linked to the address the data file gives in `source_url`, and as plain text when
  the file gives none;
- its activity (commits in 30 days and the level) and its debt with the reasons;
- its docs, each with its status and a link to the published copy when there is one;
- its bound tests: the count, the files counted, the placement of each, and the files bound to
  the node itself;
- its public symbols, the first 50 with the number left out;
- its edges grouped by kind and direction, a violation marked, and a click on the other end
  selects that node;
- its rule findings with their severity;
- a link to the node's page, and `beadloom ctx <ref>` and `beadloom why <ref>` to copy.

A field the data file holds nothing for says "none". A field a version 1 file does not carry at
all says "not recorded", because the two are different answers.

## Public API

- `NodeCard` (Vue component). Props: `node`, `edges`, `layers`. Events: `select(id)`, `close`.

## Depends on

- `site-graph-edge`, `site-layer` (entities).
- `site-shared`, for `shellQuote` and `CopyCommand`.

## Tests

`site/e2e/card.spec.js`: every field the data file holds, "none" where it holds nothing, the
layer's origin, every edge kind by direction with a click that moves the selection, the commands
copied, the symbol cap, every doc and test file by name, a source linked per forge, and a source
without a link when the file gives none.
