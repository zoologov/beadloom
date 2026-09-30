# Dashboard data (component)

A slice of the `entities` layer of the VitePress site's Feature-Sliced layout. The layout and the
layer rule are described in [the site's page](../vitepress-site.md).

**Source:** `site/.vitepress/theme/entities/dashboard-data/`

---

## Overview

The dashboard data file, `dashboard.data.json`, which `beadloom docs site` writes. Every dashboard panel shares one fetch.

## Public API

- `useDashboardData()` returns `{ data, error }`.

## Depends on

- `site-shared`.
