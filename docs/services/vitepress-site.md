# VitePress site — the committed theme

The `vitepress-site` node is the VitePress theme committed under `site/.vitepress/theme/`. It
renders the data that `beadloom docs site` writes: the node pages, `architecture.data.json`,
`landscape.data.json` and `dashboard.data.json`. The node consumes the `site-data` contract, and
the root service `beadloom` produces it. How the generator works is described in
[the VitePress site guide](../guides/vitepress-site.md); this page describes the theme.

## What is scanned

`site/.vitepress/theme` is a scan path in `.beadloom/config.yml` (BDL-076 A0). The rest of
`site/` is not scanned: it is generated output, the VitePress cache and `node_modules`.
`site/.vitepress/config.mjs`, `site/package.json` and `site/scripts/` are committed and belong to
this node through its `source: site/`, but they are outside the scan path.

What the index reads from the theme requires the `languages` extra, which provides the
TypeScript grammar:

- **`.js` files:** functions, `export const` values and imports, including `import()`.
- **`.vue` files:** a `component` symbol named after the file, plus the symbols and imports of
  each `<script>` or `<script setup>` block at their lines in the `.vue` file. The template and
  the style are not read.
- **Relative imports** resolve to the file they name. Every theme file belongs to this one node,
  so they add no `depends_on` edge. Package imports (`vue`, `vitepress`, `cytoscape`) resolve to
  no node.

Without the `languages` extra, a reindex hashes the theme files and records no symbol and no
import from them. It prints no warning, because the warning fires only when a reindex finds no
symbol at all.

## Files today

| File | Role |
|------|------|
| `index.js` | The theme entry. It extends the default theme and registers the components below. |
| `custom.css` | Styles of the diagram viewer's controls and framing. |
| `architectureTheme.js` | Colours, geometry and the ELK layout options of the architecture graph. |
| `landscapeTheme.js` | Colours and geometry of the landscape map. |
| `components/ArchitectureMap.vue` | The interactive architecture graph (Cytoscape and ELK). |
| `components/LandscapeMap.vue` | The interactive landscape map of contracts. |
| `components/DiagramViewer.vue` | Pan, zoom and full screen over the Mermaid diagrams of every page. |
| `components/AlertBanner.vue` | Dashboard: the critical-first banner. |
| `components/StatusCards.vue` | Dashboard: the status cards. |
| `components/HealthGauges.vue` | Dashboard: the health gauges. |
| `components/CategoryChart.vue` | Dashboard: debt by category and lint findings by severity. |
| `components/TrendCharts.vue` | Dashboard: the recorded trends of lint, debt, coverage and sync. |
| `components/Recommendations.vue` | Dashboard: the recommendations panel. |
| `components/AiTechwriterActivity.vue` | Dashboard: the AI tech-writer's runs. |
| `composables/useArchitectureData.js` | Loads `architecture.data.json`. |
| `composables/useLandscapeData.js` | Loads `landscape.data.json`. |
| `composables/useDashboardData.js` | Loads `dashboard.data.json`. |
| `composables/useEcharts.js` | Loads ECharts in the browser only and resolves its theme. |

## What the tools show

- **`beadloom ctx vitepress-site`** lists no theme symbol yet. `ctx` attaches a symbol to a node
  through a `beadloom:` annotation, and the theme files carry none. The annotations arrive with
  the node split described below.
- **`beadloom sync-check`** holds this page to the scanned theme files. A change to a script
  block's symbols is reported as `symbols_changed`, and any other edit as `hash_changed`.
- **`beadloom impact`** on a theme file answers only the boundary section, because its code axes
  read Python (`beadloom-j1ke`).

## Browser tests

The Playwright tests will live under `site/e2e/` and bind to this node through its `tests:` list.
`.beadloom/config.yml` declares `site/e2e` as a test root and names the `playwright` pattern group.
Until the folder exists, the root is recorded as absent and nothing is bound.

## Planned split

BDL-076 A2 restructures the theme into Feature-Sliced Design layers (`app`, `pages`, `widgets`,
`features`, `entities`, `shared`). The node is then split into one node per slice, each with its
own document, and the FSD import direction is declared as a layer rule. This page covers the
theme as it is before that split.
