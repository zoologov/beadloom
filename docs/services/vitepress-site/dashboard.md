# Dashboard (component)

A slice of the `widgets` layer of the VitePress site's Feature-Sliced layout. The layout and the
layer rule are described in [the site's page](../vitepress-site.md).

**Source:** `src/beadloom/site_scaffold/.vitepress/theme/widgets/dashboard/`

---

## Overview

The panels the generated `dashboard.md` mounts by name, each reading `dashboard.data.json`, in
the page's order: `AlertBanner`, `StatusCards`, `RuleFindings`, `PageMap`, `HealthGauges`,
`CategoryChart`, `TrendCharts`, `AiTechwriterActivity` and `Recommendations`. The charts render
with ECharts, loaded in the browser only. The page mounts `AiTechwriterActivity` only when the
data file's `ai_techwriter.recorded` is `true`, that is when the project has an AI tech-writer
run record, so a project without one shows no empty panel.

The two panels after the cards name the populations the cards' numbers were counted over
(BDL-080 S4a):

- **`RuleFindings`** reads `lint` and says lint's totals with the two populations they hold, as
  the node card says them: `This project: 0 errors, 69 warnings — 33 on 27 nodes, 36 on none.`
  on this repository's portal (BDL-080 S4g). The findings on nodes are the totals less the
  node-less ones. Below it, `N findings are bound to no node:` and each one with its rule,
  severity, message and `file:line` where it names one, or `0 findings are bound to no node.`
  A node's own findings are on its card, not here.
- **`PageMap`** reads `pages` and says how many pages the `docs site` run wrote, with the
  language of each About page: `beadloom docs site wrote 297 pages; the About page in en
  (index.md), ru (ru/index.md).` on this repository's portal, `1 page` in the singular. Then
  one collapsible list per section in the sidebar's order (`about`, `dashboard`,
  `architecture`, `nodes`, `landscape`, `docs`), a section the run wrote nothing for at 0. A
  file the project places under `.beadloom/site/` is on the portal and is not counted, so the
  sentence names the run, not the portal: until BDL-080 S4h (`beadloom-af99.16`, the S4
  review's N1) it read `This portal has N pages`.

A data file written before BDL-080 carries neither key in that shape, and neither panel is
shown.

## Public API

- The nine panels as Vue components, exported by name from `index.js`.

## Depends on

- `site-dashboard-data` (entities).
- `site-shared`, for ECharts.

## Tests

`src/beadloom/site_scaffold/e2e/dashboard.spec.js` (BDL-080 S4a, S4g, S4h): Rule findings says the
project's totals and lists every finding bound to no node; it says so when none is; this
portal's own Rule findings are the ones its data file holds; Pages names every page the run
wrote, by section, and the language of each About page, in a sentence that names the run and
not the portal; Pages says one page in the singular (S4h); a data file written before the two
panels shows neither.
