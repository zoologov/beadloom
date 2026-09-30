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

## Public API

- `useArchitectureData()` returns `{ data, error }`.
- `SUPPORTED_SCHEMA_VERSIONS`, `checkSchemaVersion(json)`.

## Depends on

- `site-shared`.
