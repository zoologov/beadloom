# VitePress site — the portal scaffold

The `vitepress-site` node is the portal scaffold the package ships, under
`src/beadloom/site_scaffold/`, with its theme under `src/beadloom/site_scaffold/.vitepress/theme/`.
`beadloom docs site` writes it into the portal directory beside the content it generates, and it
renders that content: the node pages, `architecture.data.json`, `landscape.data.json` and
`dashboard.data.json`. The node consumes the `site-data` contract, and the root service
`beadloom` produces it. How the generator works and how a project publishes its portal are
described in [the VitePress site guide](../guides/vitepress-site.md); this page describes the
scaffold.

Since BDL-076 B1 the scaffold is package data, so every project gets the same theme from the
installed beadloom, and `site/` in this repository is output only: `/site/` is ignored, and
`docs site --out site` writes this repository's portal the way it writes an adopter's.

## What is scanned

The scaffold lies under `src`, this repository's scan path, so its `.js`, `.mjs` and `.vue` files
are read with the rest of the source. `.vitepress/config.mjs`, `.vitepress/generated.mjs`,
`package.json`, `package-lock.json` and `scripts/` belong to this node through its
`source: src/beadloom/site_scaffold/`.

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
| `pages` | [`site-architecture-page`](vitepress-site/architecture-page.md) | `ArchitectureMap`: the viewer in architecture mode with the node card, on the architecture page and every node page. |
| `pages` | [`site-landscape-page`](vitepress-site/landscape-page.md) | `LandscapeMap`: the viewer in landscape mode with the service card. |
| `widgets` | [`site-graph-viewer`](vitepress-site/graph-viewer.md) | The viewer core: toolbar, canvas, panel and legend, in two data modes. |
| `widgets` | [`site-node-card`](vitepress-site/node-card.md) | The architecture card: everything the data file says about one node. |
| `widgets` | [`site-dashboard`](vitepress-site/dashboard.md) | The dashboard's panels. |
| `widgets` | [`site-diagram-viewer`](vitepress-site/diagram-viewer.md) | Pan, zoom and full screen over Mermaid diagrams. |
| `features` | [`site-filter-graph`](vitepress-site/filter-graph.md) | Which nodes the viewer shows: the architecture's filters and the landscape's. |
| `features` | [`site-select-neighbourhood`](vitepress-site/select-neighbourhood.md) | A selected node's neighbourhood: depth, direction, dim or hide. |
| `features` | [`site-impact-view`](vitepress-site/impact-view.md) | The impact mode: everything that depends on the selected node, and its summary. |
| `features` | [`site-navigate-graph`](vitepress-site/navigate-graph.md) | Pan, zoom, fit, centre and Arrange. |
| `features` | [`site-fullscreen`](vitepress-site/fullscreen.md) | Full screen with a CSS fallback. |
| `features` | [`site-url-state`](vitepress-site/url-state.md) | A view's state in the query string. |
| `entities` | [`site-architecture-data`](vitepress-site/architecture-data.md) | `architecture.data.json` and its schema version. |
| `entities` | [`site-landscape-data`](vitepress-site/landscape-data.md) | `landscape.data.json`, its contracts' health, and which are verified. |
| `entities` | [`site-dashboard-data`](vitepress-site/dashboard-data.md) | `dashboard.data.json`. |
| `entities` | [`site-graph-node`](vitepress-site/graph-node.md) | A node's status, its risks and its container. |
| `entities` | [`site-graph-edge`](vitepress-site/graph-edge.md) | Edge kinds, their styles, the legend, and which edges a walk follows. |
| `entities` | [`site-layer`](vitepress-site/layer.md) | The declared layers, and their colours. |
| `shared` | [`site-shared`](vitepress-site/shared.md) | Browser checks, JSON loading, tree walks, shell quoting, theme tokens, Cytoscape, ECharts and the copy button. |

This node keeps what belongs to no slice: `theme/index.js`, the file VitePress looks for, which
re-exports the `app` layer; `.vitepress/config.mjs`, which reads the identity and the nav
`docs site` generates (`site.generated.mjs`, `config.generated.mjs`); `.vitepress/generated.mjs`,
whose `importGenerated(url)` loads a generated module as `{}` with a warning when it is not there
yet and throws any other load error; `package.json` (`engines.node: >=22`, every dependency
pinned exactly but `web-worker`) with its lockfile; and `scripts/`.

**The layer rule.** `site-fsd-layers` in `.beadloom/_graph/rules.yml` declares the six layers by
the tags `fsd-app` to `fsd-shared`, at `error`. Each slice carries its layer as its own tag and no
node stands for a layer, so a dependency between two slices of one layer is reported as a
same-layer crossing, which is FSD's rule that slices of a layer do not know each other. `app` and
`shared` have segments rather than slices, so each is one node. The edges it judges are the
relative imports between theme files, which resolve to the files they name.

## What the tools show

- **`beadloom ctx <slice>`** lists the slice's symbols: every file of every slice carries a
  `// beadloom:component=<slice>` annotation. A slice annotates all of its files or none, because
  a node with some files annotated keeps sync pairs for those files only (`beadloom-oo4m`). The
  annotations bind the source to this repository's graph and do not ship: `docs site` writes each
  file without its annotation-only lines (`beadloom-ujzb.18`).
- **`beadloom sync-check`** holds each slice's document to that slice's files. A change to a
  script block's symbols is reported as `symbols_changed`, and any other edit as `hash_changed`.
- **`beadloom why <slice>`** follows the `depends_on` edges the imports between slices produce.
- **`beadloom impact`** on a theme file answers only the boundary section, because its code axes
  read Python (`beadloom-j1ke`).

## Browser tests

The Playwright tests live under `src/beadloom/site_scaffold/e2e/` and ship with the scaffold, so a
portal written by `docs site` carries them in its `e2e/`. `.beadloom/config.yml` declares
`src/beadloom/site_scaffold/e2e` as a test root and names the `playwright` pattern group. This
node declares the whole directory, and each spec is also declared in the `tests:` list of the one
slice it drives, which is where it binds: a test file binds to one node, and a node does not
inherit its ancestors' tests. The eighteen specs bind to sixteen slices. No spec drives
`site-app`, `site-dashboard`, `site-dashboard-data` or `site-landscape-data`, so those four report
no bound tests.

The tests drive the built portal: `e2e/support/serve.mjs` runs `vitepress build` and then
`vitepress preview`, and refuses to start before `beadloom docs site` has written the content.
Run them from the portal directory with `npm run test:e2e`, on `Node.js 22` or later, after
`npx playwright install chromium`. The base path is read from the generated
`site.generated.mjs`, or from `BEADLOOM_E2E_BASE`. The tests read the viewer's state through its
test handle, `window.__beadloomViewer`, which exists only under automation.

**Any project's graph** (`beadloom-ujzb.17`, `.20`). A case chooses its subject from the data the
portal serves, never by a node id of this repository. A case written about a shape the served
graph does not hold, such as two declared layers, a domain two levels deep or a contract between
two services, calls `requireShape` (`e2e/support/shape.js`) and is skipped with the reason
`this portal's graph lacks what the case needs: <shape>`. With `BEADLOOM_E2E_NO_SKIP=1` such a
case fails instead, naming the shape. No case skips in any other way, which a self-check holds.
Measured on the six adopter fixtures under `tests/fixtures/site/` when the shape skips were
introduced (`beadloom-ujzb.17`, on macOS with `Node.js 22`), all 101 cases ran or skipped by
shape: python 75 passed and 26 skipped, go 88 and 13, typescript 94 and 7, java 78 and 23, kotlin
74 and 27, swift 74 and 27.

**In CI.** The advisory `site-e2e` job runs the suite on this repository's portal after
`site-build`, with `BEADLOOM_E2E_NO_SKIP=1`, so every case runs here: 101 of 101. It is not a
required check. The `site-adopters` workflow builds the six fixtures and runs the suite on each,
on pull requests that change what it tests, weekly on `main` and on demand. What it tests is its
`paths:` filter, and a self-check holds that filter to every file the slow tests read and every
`src/beadloom` file their `init`, `reindex` and `docs site` steps enter, traced on each fixture in
a fresh interpreter (`beadloom-ujzb.24`).
