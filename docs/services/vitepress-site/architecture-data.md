# Architecture data (component)

A slice of the `entities` layer of the VitePress site's Feature-Sliced layout. The layout and the
layer rule are described in [the site's page](../vitepress-site.md).

**Source:** `site/.vitepress/theme/entities/architecture-data/`

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
knows no forge. Nothing else from the git remote is in the file. `activity` carries only
`commits_30d` and `level`. `tests` is `{files, file_count, count, placement}`: `files` lists only
the test files bound to the node itself, and the counts are taken over the node and its `part_of`
descendants.

A field a version 1 file does not carry is shown as "not recorded" and is never a risk. The full
contract is in the
[Site Generation SPEC](../../domains/application/features/site-generation/SPEC.md#the-architecture-data-file-schema-version-2).

## Public API

- `useArchitectureData()` returns `{ data, error }`.
- `SUPPORTED_SCHEMA_VERSIONS`, `checkSchemaVersion(json)`.

## Depends on

- `site-shared`.

## Tests

`site/e2e/data-version.spec.js`: a data file of an unknown schema version is refused with a
visible message.
