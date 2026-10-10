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
  the file gives none. When the top-level `source_ref` says the portal was built from a commit
  no branch of `origin` holds (`pushed: false`, BDL-080 S4c), a note under the link
  (`data-card-field=source-ref`) says where the links point: `built from an unpublished commit;
  links point at main`, or the commit cut to 12 characters when no branch stands in. A pushed
  commit, or a file without `source_ref`, gets no note;
- its activity and its debt with the reasons. A box, a node whose `debt` carries `inside`
  (BDL-080 S4a), says its debt twice, its own score with its reasons and the debt inside it:
  the nodes inside it that carry debt, their scores summed, and per reason how many of them
  carry it. The `beadloom` box of this repository reads `own 0` and
  `inside 38.5 on 32 nodes: dormant 13, high_fan_out 10, oversized 8, undocumented 3`
  (measured on 2026-10-10 at
  `39b01cd9`, every document fresh). A leaf says its debt on one line, as before. Since BDL-078
  the activity line states changed lines in 30 days and the level, which is relative to the
  project: `412 lines changed in 30 days, hot`, `1 line changed in 30 days, cool` in the
  singular, and in words for the two levels with no change in the window, `no change in 30
  days, quiet` and `no change in 90 days, dormant`. A data file written before lines were
  counted carries commits only and is said in commits (`3 commits in 30 days, warm`); a node
  with no recorded activity says "not recorded", as on a shallow clone that does not reach back
  90 days. A level the card does not know is shown as text;
- its docs, each with its status and a link to the published copy when there is one;
- its bound tests: the count, the files counted, the placement of each, and the files bound to
  the node itself;
- its public symbols, the first 50 with the number left out;
- its edges grouped by kind and direction, a violation marked, and a click on the other end
  selects that node;
- its rule findings with their severity. Where the data file carries the top-level `lint`
  (BDL-080 S4a), the section names lint's reach over the whole project, so "none" is not read as
  "lint never ran": on this repository's portal, measured on 2026-10-10, a node without
  findings reads `none — this project: 0 errors, 69 warnings — 33 on 27 nodes, 36 on none`,
  and a node with findings carries the same line under its list. The totals are lint's own
  over every finding; the findings on nodes are the totals less the node-less ones (BDL-080
  S4g), since each finding is bound to one node or to none, and the data file carries no third
  number.
  `on none` is always said, `0 on none` included, so both populations are named on every
  portal. The card of the box that holds the whole project (`boxTreeOf`'s wrapper) also lists
  the findings bound to no node, `N findings bound to no node`, each with its rule, severity,
  message and `file:line` where it names one. No other card lists them;
- for a box, when the viewer passes `parents`, an **Inside** section
  (`data-card-field=contents`, BDL-078 `beadloom-btkd.7`): how many nodes it holds at any
  depth, and its edges out to and in from each node its lines reach, with their counts
  (`boxEdgesOf`, `site-graph-edges`), and since BDL-080 S4a the debt inside it when the data
  file carries `debt.inside`, on the `beadloom` box `debt 38.5 on 32 nodes: dormant 13, …`;
- a link to the node's page, and `beadloom ctx <ref>` and `beadloom why <ref>` to copy.

A field the data file holds nothing for says "none". A field a version 1 file does not carry at
all says "not recorded", because the two are different answers.

## Public API

- `NodeCard` (Vue component). Props: `node`, `edges`, `layers`, `parents` (each node's box,
  `{ id: parent | null }`; `null`, the default, shows no Inside section), `lint` (the data
  file's top-level `lint`; `null`, the default, says nothing about lint's reach and lists no
  node-less finding) and `sourceRef` (the data file's top-level `source_ref`; `null` shows no
  note under the source). `ArchitectureMap` passes `data.lint` and `data.source_ref`. Events:
  `select(id)`, `close`.

## Depends on

- `site-graph-edges`, `site-layers` (entities).
- `site-shared`, for `shellQuote` and `CopyCommand`.

## Tests

`src/beadloom/site_scaffold/e2e/card.spec.js`: every field the data file holds, "none" where it
holds nothing, the layer's origin and its rule by title or name, every edge kind by direction with a click that moves the
selection, the commands copied, the symbol cap, every doc and test file by name, a source
linked per forge, and a source without a link when the file gives none; the activity line in
lines, in commits for an older file, in the singular for one, and in words for `quiet` and
`dormant`. Since BDL-080 S4: the unpublished-commit note beside the source link, on a branch
and on a bare commit, and no note for a pushed commit or a file without `source_ref`; lint's
reach after `none` for three data shapes (this portal's; two findings on one node and none on
none; one finding on none), under a card's own findings, and as the data file states it; the
node-less list on the project box's card and on no leaf's; a box's own and inside debt in Debt
and in Inside, and a leaf's debt on one line.
