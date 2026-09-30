# Dashboard (component)

A slice of the `widgets` layer of the VitePress site's Feature-Sliced layout. The layout and the
layer rule are described in [the site's page](../vitepress-site.md).

**Source:** `site/.vitepress/theme/widgets/dashboard/`

---

## Overview

The panels the generated `dashboard.md` mounts by name, each reading `dashboard.data.json`:
`AlertBanner`, `StatusCards`, `HealthGauges`, `CategoryChart`, `TrendCharts`, `Recommendations` and
`AiTechwriterActivity`. The charts render with ECharts, loaded in the browser only.

## Public API

- The seven panels as Vue components, exported by name from `index.js`.

## Depends on

- `site-dashboard-data` (entities).
- `site-shared`, for ECharts.
