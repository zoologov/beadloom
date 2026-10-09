# Node card (component)

A slice of the `widgets` layer of the VitePress site's Feature-Sliced layout. The layout and the
layer rule are described in [the site's page](../vitepress-site.md).

**Source:** `src/beadloom/site_scaffold/.vitepress/theme/widgets/node-card/`

---

## Overview

`NodeCard`, the architecture card: everything the data file says about one node. The
architecture page puts it in the viewer's panel for the selected node. The landscape has a card of
its own, the service card of `site-landscape-page`.

In order, the card shows:

- the node's id and summary; its kind, lifecycle and tags;
- its layer, and whether the layer is the node's own tag or inherited through `part_of`. Where
  the data file names every layer rule (BDL-080), the card also names the rule that places the
  node, by its title where it declares one: `widgets (FSD architecture, its own tag)` on this
  repository, `<layer> (rule <name>, inherited through part_of)` for an untitled rule. A one-rule
  project names its rule too. "Its own tag" is read from the node's `tags`, which the data file
  writes as the node declares them, also outside a scoped rule's scope;
- its source, linked to the address the data file gives in `source_url`, and as plain text when
  the file gives none;
- its activity and its debt with the reasons. Since BDL-078 the activity line states changed
  lines in 30 days and the level, which is relative to the project: `412 lines changed in 30
  days, hot`, `1 line changed in 30 days, cool` in the singular, and in words for the two levels
  with no change in the window, `no change in 30 days, quiet` and `no change in 90 days, dormant`.
  A data file written before lines were counted carries commits only and is said in commits
  (`3 commits in 30 days, warm`); a node with no recorded activity says "not recorded", as on a
  shallow clone that does not reach back 90 days. A level the card does not know is shown as
  text;
- its docs, each with its status and a link to the published copy when there is one;
- its bound tests: the count, the files counted, the placement of each, and the files bound to
  the node itself;
- its public symbols, the first 50 with the number left out;
- its edges grouped by kind and direction, a violation marked, and a click on the other end
  selects that node;
- its rule findings with their severity;
- for a box, when the viewer passes `parents`, an **Inside** section (`data-card-field=contents`,
  BDL-078 `beadloom-btkd.7`): how many nodes it holds at any depth, and its edges out to and in
  from each node its lines reach, with their counts (`boxEdgesOf`, `site-graph-edges`);
- a link to the node's page, and `beadloom ctx <ref>` and `beadloom why <ref>` to copy.

A field the data file holds nothing for says "none". A field a version 1 file does not carry at
all says "not recorded", because the two are different answers.

## Public API

- `NodeCard` (Vue component). Props: `node`, `edges`, `layers`, `parents` (each node's box,
  `{ id: parent | null }`; `null`, the default, shows no Inside section). Events: `select(id)`,
  `close`.

## Depends on

- `site-graph-edges`, `site-layers` (entities).
- `site-shared`, for `shellQuote` and `CopyCommand`.

## Tests

`src/beadloom/site_scaffold/e2e/card.spec.js`: every field the data file holds, "none" where it
holds nothing, the layer's origin and its rule by title or name, every edge kind by direction with a click that moves the
selection, the commands copied, the symbol cap, every doc and test file by name, a source
linked per forge, and a source without a link when the file gives none; the activity line in
lines, in commits for an older file, in the singular for one, and in words for `quiet` and
`dormant`.
