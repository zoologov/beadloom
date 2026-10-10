# Dashboard data (component)

A slice of the `entities` layer of the VitePress site's Feature-Sliced layout. The layout and the
layer rule are described in [the site's page](../vitepress-site.md).

**Source:** `src/beadloom/site_scaffold/.vitepress/theme/entities/dashboard-data/`

---

## Overview

The dashboard data file, `dashboard.data.json`, which `beadloom docs site` writes. Every
dashboard panel shares one fetch.

Since BDL-080 S4a the file carries two more things, which the `RuleFindings` and `PageMap`
panels of `site-dashboard` read:

- `lint.nodes_with_findings` and `lint.nodeless`, beside the `lint` section's totals: how many
  nodes carry a finding, and each finding bound to no node as `{rule, severity, message, file,
  line}`. The shape is the one the architecture data file's top-level `lint` has, from the same
  projection (`lint_reach_of`);
- the top-level `pages`: `{count, sections, languages}`. `sections` lists every section in the
  sidebar's order (`about`, `dashboard`, `architecture`, `nodes`, `landscape`, `docs`), each
  `{name, count, pages}` with the Markdown pages the run wrote under it, by path, a section with
  none at 0. `languages` is `[{language, page}]`, one per About page (`en` for `index.md`, `ru`
  for `ru/index.md`). The generator writes this file after the published documentation, so the
  map names every page it wrote. A file the project adds under `.beadloom/site/` is not counted.

This repository's portal, measured on 2026-10-10 by S4T: 297 pages (about 2, dashboard 1,
architecture 2, nodes 139, landscape 2, docs 151), en and ru. The file is not on the public API
list ([public-api.md](../../guides/public-api.md)), so its keys carry no promise. The full
contract is in the
[Site Generation SPEC](../../domains/application/features/site-generation/SPEC.md).

## Public API

- `useDashboardData()` returns `{ data, error }`.

## Depends on

- `site-shared`.
