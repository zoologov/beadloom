# Architecture data (component)

A slice of the `entities` layer of the VitePress site's Feature-Sliced layout. The layout and the
layer rule are described in [the site's page](../vitepress-site.md).

**Source:** `site/.vitepress/theme/entities/architecture-data/`

---

## Overview

The architecture data file, `architecture.data.json`, which `beadloom docs site` writes. The viewer
reads the keys of schema version 1 only; version 2 keeps every one of them, so both are accepted. A
file with any other `schema_version` is refused, and the viewer shows the reason instead of an empty
canvas.

Version 2 adds the node card, which no slice reads yet: `source`, `lifecycle`, `tags`, `docs`,
`tests`, `public_symbols`, `activity`, `findings` and `debt`. `tests` is
`{files, file_count, count, placement}`. `files` lists only the test files bound to the node
itself; a file whose owner the graph does not hold stays listed where it is counted.
`file_count`, `count` and `placement` are taken over the node and its `part_of` descendants, so a
container states its parts' numbers without repeating their paths (BDL-076 K4). The full contract
is in the [Site Generation SPEC](../../domains/application/features/site-generation/SPEC.md).

## Public API

- `useArchitectureData()` returns `{ data, error }`.
- `SUPPORTED_SCHEMA_VERSIONS`, `checkSchemaVersion(json)`.

## Depends on

- `site-shared`.
