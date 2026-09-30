# VitePress site — the committed theme

The `vitepress-site` node is the VitePress site committed under `site/`, with its theme under
`site/.vitepress/theme/`. It renders the data that `beadloom docs site` writes: the node pages,
`architecture.data.json`, `landscape.data.json` and `dashboard.data.json`. The node consumes the
`site-data` contract, and the root service `beadloom` produces it. How the generator works is described in
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
- **Relative imports** resolve to the file they name, and so to the slice that owns it: an import
  from one slice's file into another slice's `index.js` is a `depends_on` edge between the two
  slices. Package imports (`vue`, `vitepress`, `cytoscape`) resolve to no node.

Without the `languages` extra, a reindex hashes the theme files and records no symbol and no
import from them. It prints no warning, because the warning fires only when a reindex finds no
symbol at all.

## Layout: Feature-Sliced Design

Since BDL-076 A2 the theme follows Feature-Sliced Design. There are six layers, top to bottom, and
a layer imports only the layers below it. A slice is used only through its public `index.js`, and
it holds `ui`, `model`, `lib` or `api` segments as it needs them. Each slice is its own node,
`part_of` this one, with a short document under [`vitepress-site/`](vitepress-site/app.md).

| Layer | Slice (node) | What it is |
|-------|--------------|------------|
| `app` | [`site-app`](vitepress-site/app.md) | The theme: registers the pages and widgets the generated Markdown mounts. |
| `pages` | [`site-architecture-page`](vitepress-site/architecture-page.md) | `ArchitectureMap`: the graph viewer with the node card in its panel. |
| `pages` | [`site-landscape-page`](vitepress-site/landscape-page.md) | `LandscapeMap`: the map of contracts between services. |
| `widgets` | [`site-graph-viewer`](vitepress-site/graph-viewer.md) | The viewer core: toolbar, canvas and panel. |
| `widgets` | [`site-dashboard`](vitepress-site/dashboard.md) | The dashboard's panels. |
| `widgets` | [`site-diagram-viewer`](vitepress-site/diagram-viewer.md) | Pan, zoom and full screen over Mermaid diagrams. |
| `features` | [`site-filter-graph`](vitepress-site/filter-graph.md) | Which nodes the viewer shows. |
| `features` | [`site-navigate-graph`](vitepress-site/navigate-graph.md) | Pan, zoom, fit, centre and Arrange. |
| `features` | [`site-fullscreen`](vitepress-site/fullscreen.md) | Full screen with a CSS fallback. |
| `features` | [`site-url-state`](vitepress-site/url-state.md) | A view's state in the query string. |
| `entities` | [`site-architecture-data`](vitepress-site/architecture-data.md) | `architecture.data.json` and its schema version. |
| `entities` | [`site-landscape-data`](vitepress-site/landscape-data.md) | `landscape.data.json`. |
| `entities` | [`site-dashboard-data`](vitepress-site/dashboard-data.md) | `dashboard.data.json`. |
| `entities` | [`site-graph-node`](vitepress-site/graph-node.md) | A node's status, container and card. |
| `entities` | [`site-graph-edge`](vitepress-site/graph-edge.md) | Edge kinds, their styles and the legend. |
| `entities` | [`site-layer`](vitepress-site/layer.md) | The layers read from the data, and their colours. |
| `shared` | [`site-shared`](vitepress-site/shared.md) | Browser checks, JSON loading, tree walks, theme tokens, Cytoscape and ECharts. |

This node keeps what belongs to no slice: `theme/index.js`, the file VitePress looks for, which
re-exports the `app` layer; `site/.vitepress/config.mjs`; `site/package.json`; and `site/scripts/`.

**The layer rule.** `site-fsd-layers` in `.beadloom/_graph/rules.yml` declares the six layers by
the tags `fsd-app` to `fsd-shared`, at `error`. Each slice carries its layer as its own tag and no
node stands for a layer, so a dependency between two slices of one layer is reported as a
same-layer crossing, which is FSD's rule that slices of a layer do not know each other. `app` and
`shared` have segments rather than slices, so each is one node. The edges it judges are the
relative imports between theme files, which resolve to the files they name.

## What the tools show

- **`beadloom ctx <slice>`** lists the slice's symbols: every file of every slice carries a
  `// beadloom:component=<slice>` annotation. A slice annotates all of its files or none, because
  a node with some files annotated keeps sync pairs for those files only (`beadloom-oo4m`).
- **`beadloom sync-check`** holds each slice's document to that slice's files. A change to a
  script block's symbols is reported as `symbols_changed`, and any other edit as `hash_changed`.
- **`beadloom why <slice>`** follows the `depends_on` edges the imports between slices produce.
- **`beadloom impact`** on a theme file answers only the boundary section, because its code axes
  read Python (`beadloom-j1ke`).

## Browser tests

The Playwright tests live under `site/e2e/` and bind to this node through its `tests:` list.
`.beadloom/config.yml` declares `site/e2e` as a test root and names the `playwright` pattern group.
They drive the built portal: `site/e2e/support/serve.mjs` runs `vitepress build` and then
`vitepress preview`, after `beadloom docs site --out site` has written the content. Run them from
`site/` with `npm run test:e2e`, under the Node.js version the workflows pin: Playwright does not
run on the older releases the site build still accepts. The tests read the viewer's
state through its test handle, `window.__beadloomViewer`, which exists only under automation.
