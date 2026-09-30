# Landscape data (component)

A slice of the `entities` layer of the VitePress site's Feature-Sliced layout. The layout and the
layer rule are described in [the site's page](../vitepress-site.md).

**Source:** `site/.vitepress/theme/entities/landscape-data/`

---

## Overview

The landscape data file, `landscape.data.json`, which `beadloom docs site` writes, fetched once per page load.

## Public API

- `useLandscapeData()` returns `{ data, error }`.

## Depends on

- `site-shared`.
