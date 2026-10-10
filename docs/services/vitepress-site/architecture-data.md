# Architecture data (component)

A slice of the `entities` layer of the VitePress site's Feature-Sliced layout. The layout and the
layer rule are described in [the site's page](../vitepress-site.md).

**Source:** `src/beadloom/site_scaffold/.vitepress/theme/entities/architecture-data/`

---

## Overview

The architecture data file, `architecture.data.json`, which `beadloom docs site` writes. The
viewer accepts schema versions 1 and 2. A file with any other `schema_version` is refused, and the
viewer shows the reason instead of an empty canvas.

Version 2 keeps every key of version 1 and adds what the viewer now reads:

- at the top level, the declared `layers`, which name the legend, the Layer filter, the card and
  the impact summary;
- per node, the card: `source` and `source_url`, `lifecycle`, `tags`, `docs`, `tests`,
  `public_symbols`, `activity`, `findings` and `debt`. The node status reads the severity of each
  finding, and the impact mode reads `tests`, `docs` and `findings` for the risks.

`source_url` is the finished link to the node's source at the commit the site was generated from.
The generator decides it per forge and writes `""` for a host it does not recognise, so the viewer
knows no forge. Nothing else from the git remote is in the file.

Since BDL-080 S4c a commit no branch of `origin` holds is linked through a branch `origin`
holds, and the top-level `source_ref` says which revision the links name, present whenever the
file carries source links: `{commit, linked, pushed}`. `commit` is the full hash the site was
built from; `pushed` is `false` only when git says no branch of `origin` holds it; `linked` is
that hash, or the name of the branch on `origin` that stands in for it (the branch's upstream
when it is on `origin`, else `origin`'s branch of the same name, else `origin/HEAD`). Only
`origin` counts since BDL-080 S4h, because the links name `origin`'s address. The card shows
"built from an unpublished commit; links point at <linked>" under a source link when `pushed`
is `false`, with a hash cut to 12 characters. `activity` carries only `commits_30d`,
`lines_30d` and `level`. `tests` is `{files, file_count, count, placement}`: `files` lists only
the test files bound to the node itself, and the counts are taken over the node and its
`part_of` descendants.

Since BDL-080 S4a the file names the populations its counts were taken over:

- at the top level, `lint`: `{errors, warnings, nodes_with_findings, nodeless}`. `errors` and
  `warnings` are lint's own totals over every finding, `nodes_with_findings` is how many nodes
  carry at least one, and `nodeless` lists each finding bound to no node as
  `{rule, severity, message, file, line}` (`severity` `error` or `warn`; `file` `""` and `line`
  `null` when it names no place). Every finding is on a node or on none, so the findings on
  nodes are `errors + warnings` less `nodeless`, and the card derives that number rather than
  reading a key. The key is omitted when lint did not run;
- per node, on a box (a node another node is `part_of`), `debt.inside`:
  `{nodes, score, by_reason}`, the descendants that carry debt, the sum of their own scores, and
  per debt-report reason how many of them carry it. The box's own `score` and `reasons` are
  unchanged beside it, and a leaf has no `inside`.

On this repository's portal, measured on 2026-10-10, `lint` holds
`{"errors": 0, "warnings": 69, "nodes_with_findings": 27}` with 36 entries in `nodeless`, and 13
boxes carry `debt.inside`.

Since BDL-080 S1 the file carries every layer rule the project declares, still as schema 2,
because every key is added and none changes meaning for a project without `scope:`:

- at the top level, `layer_rules`: one entry per `layers` rule, ordered by name, each
  `{name, title, scope, edge_kind, layers}`. `title` is the rule's declared `title:` (`""` when
  none), which the viewer shows the rule by; the `name` stays its identifier in the URL.
  `scope` is the declared `scope:` or the container the rule is derived to stratify, `""` when
  there is none. Each layer is `{name, rank, tag, token}`, and `token` here is the layer's name;
- per node, `layer_rule` (the rule that places the node, `""` when none) and `layer_rule_rank`
  (its rank in that rule, `null` when no rule places it). The node's own tag places it first,
  then its nearest tagged `part_of` ancestor; at one distance the first rule by name wins;
- per `depends_on` edge, `violation` is `true` when ANY rule finds against the edge. The key is
  absent on an edge no rule judged, never `false`.

`layers`, `layer_order` and each node's `layer` and `layer_rank` still describe the first
`layers` rule by name, and since BDL-080 S1f they follow that rule's `scope:`: a node outside the
scope has `layer` `""` and `layer_rank` `null` even when it carries the rule's tag, and an edge
between two nodes no rule places carries no `violation` key. Without a `scope:` on the first
rule the original keys are what they were. A file without `layer_rules` is read through the
original keys, as before.

A field a version 1 file does not carry is shown as "not recorded" and is never a risk. The full
contract is in the
[Site Generation SPEC](../../domains/application/features/site-generation/SPEC.md#the-architecture-data-file-schema-version-2).

## Public API

- `useArchitectureData()` returns `{ data, error }`.
- `SUPPORTED_SCHEMA_VERSIONS`, `checkSchemaVersion(json)`.

## Depends on

- `site-shared`.

## Tests

`src/beadloom/site_scaffold/e2e/data-version.spec.js`: a data file of an unknown schema version
is refused with a visible message.
