# RFC: BDL-076 — The architecture graph viewer, made a working tool for the team and for adopters

> **Status:** Approved
> **Created:** 2026-09-30

---

## Overview

The architecture and landscape viewers become one viewer core, `GraphViewer`, with two modes. The
core owns the toolbar, navigation, full screen, the side panel and the selection model:
neighbourhood by depth and direction, and impact. The data file it reads grows to carry what the
node card needs. Node pages embed the same viewer focused on their node. In slice 2 the whole portal
scaffold moves into the wheel, and `beadloom docs site` writes it for any project. Playwright
drives the built portal in CI.

## Motivation

### Problem

See the PRD. The root causes were measured by explore (`axes.md`, Supplement B) and each maps to a
fix below.

### Solution

Keep the stack — VitePress 1.6.4, Cytoscape.js 3.34.1, cytoscape-elk over ELK 0.12 — because every
defect is a configuration or a missing feature, not a limit of the libraries. Rebuild the viewer
component around a shared core, extend the data file, and ship the scaffold.

## Technical Context

### Constraints

- **The viewer is JavaScript and `beadloom impact` cannot read it.** Scope, tests and review have to
  name the `.vue`/`.js` files explicitly (Supplement A of `axes.md`).
- **Cytoscape parses only literal colours** — names, hex, rgb, hsl (`cytoscape.esm.mjs:475-477`).
  Every theme colour must be resolved from the CSS variables at runtime and re-applied when the
  VitePress theme switches.
- **The site is static.** Everything the card shows is computed at `docs site` time into
  `public/*.data.json`. Nothing queries the index from the browser.
- **The data file is a contract between the Python generator and the JS viewer.** It gets
  `schema_version: 2`, a test on the Python side for the keys, and a check in the viewer that
  refuses an unknown version with a visible message rather than a blank canvas.
- **The graph's view is not the code's view.** Impact mode says so in its UI.
- **Adopters' layers are theirs.** The palette and the lanes derive from the project's declared
  layer rule. They are not keyed to `service/application/domain/infra`.
- **Node 22** is what CI and Pages use. The scaffold's `package.json` declares `engines.node`
  (`>=20`), and the locked dependency set stays exact.

### Affected Areas

`site/.vitepress/theme/**` (the viewer and its composables), `src/beadloom/application/`
(`architecture_view.py`, `landscape_view.py`, `site_pages.py`, `site.py`, the `site_*` modules),
`src/beadloom/services/commands/docs.py`, `.github/workflows/{ci,deploy-site}.yml`, packaging
(`pyproject.toml`, slice 2), the site's SPEC and guide, and new browser tests.

## Axes

Explore derived five sections from `site.py`, `docs_site`, `architecture_view.py`, `site_pages.py`,
`landscape_view.py` and `graph/c4.py` (`axes.md`, verbatim there). The rulings below are per node
and apply to every row of that node across the sections.

> **Derived by:** `beadloom impact` over six targets (see `axes.md`)
> **Seed:** `each_graph_file`, `flow_signature`, `write_yaml_atomic` (effects `reads-a-yaml-directory`, `serialises-yaml`); the three view modules have no seed
> **Unresolved:** the viewer itself (JavaScript, node `vitepress-site`), the workflows, packaging — Supplement A

| Axis | Node | Sites | Owns unread | In scope | Why |
|---|---|---|---|---|---|
| branches | site-generation | `site.py` — `generate_site`, `_lint_violation_refs`, the renderers | none | **yes** | Writes the data files and pages; carries findings (today a boolean); slice 2 writes the scaffold. |
| callers + branches | application | `architecture_view.py`, `site_pages.py`, `landscape_view.py`, `site_landscape.py`, `site_nav.py` | none | **yes** | The data file's builder, the node page's diagram section, the landscape data. |
| — (not derived) | vitepress-site | `site/.vitepress/theme/**`, `site/package.json`, `site/.vitepress/config.mjs` | 22 files | **yes** | The viewer. Slice 2 moves its scaffold into the wheel. |
| callers + branches | cli-commands | `commands/docs.py` — `docs_site` | none | **yes** | Slice 2: the command that writes the scaffold, and its options. |
| callers | c4-diagrams | `graph/c4.py` | none | no | Node pages stop calling it; `architecture-diagram.md` and `beadloom graph` keep it unchanged. |
| callers | contracts, federation | `graph/contracts.py:325`, `federation/export.py:46` | none | no | Callers of the landscape data; the landscape mode reads the same data. |
| callers | ai-techwriter | `ai_techwriter/runner.py:110` | 2 | no | Reads the architecture view for its own prompt; the keys it reads are kept. |
| co-writers | agent-prime, doc-generator, doc-sync, graph-layout, reindex, graph-loader, cli-commands (`index_ops`) | YAML writers reached through the shared sink | none | no | Blast radius of the YAML sink, not of the viewer. |
| callers | agentic-flow-setup, ai-techwriter-setup, role-adapters, tui | callers of the shared writer | 4 (`tui/styles/*.tcss`) | no | Same sink; the TUI stylesheets are unrelated. |
| — (A0 measurement) | import-resolver | `graph/import_resolver.py:153-155` (relative imports skipped), `:737-765` (walk-up to a scan path) | none | **yes** | Owner, 2026-09-30: `beadloom-hjr1`, `beadloom-g9fb` — the viewer's graph for a JS/TS adopter depends on it. |
| — (A0 measurement) | code-indexer | `context_oracle/code_indexer.py:246-264` (no `.vue` parser); `application/reindex/models.py:69` | none | **yes** | Owner, 2026-09-30: `beadloom-tmxa` — extract `<script>`/`<script setup>` with its line offset and feed the existing JS/TS parser. |
| — (not derived) | debt-report | `debt_report/scoring.py:53` `compute_top_offenders`, `models.py:79` `NodeDebt` | none | **yes (read only)** | The card's debt comes from here. The generator reads it; the debt report does not change. |
| — (not derived) | — | `.github/workflows/ci.yml` (`site-build`), `deploy-site.yml` | — | **yes** | A browser-test job; slice 2's deploy through `docs site`. |
| — (not derived) | — | `pyproject.toml` packaging | — | **yes (slice 2)** | The scaffold ships as package data. |

## Proposed Solution

### Approach

**First: beadloom reads JS/TS/Vue honestly (owner, 2026-09-30).**
- *Relative imports (`beadloom-hjr1`).* In `import_resolver`, a relative JS/TS specifier (`./x`,
  `../y/z`) is resolved against the importing file's directory. Extension and index resolution
  (`.js`, `.ts`, `.jsx`, `.tsx`, `.vue`, `.mjs`, `/index.*`) is applied, and the result is mapped to
  the node whose `source:` most specifically covers that file, by the same rule ownership uses.
  An import that resolves to no file is reported as unresolved, not dropped silently.
- *The walk-up (`beadloom-g9fb`).* A Python import that cannot be resolved is never prefixed with
  a scan path of another language, and the walk-up stops at the scan path's own root. A test with a
  mixed Python + JS repository asserts that the edge count equals the edges the imports name.
- *`.vue` (`beadloom-tmxa`).* The indexer extracts `<script>` and `<script setup>` blocks, choosing
  `lang="ts"` or JS, and parses them with the existing tree-sitter JS/TS parser. Symbol lines are
  offset to their place in the `.vue` file. The template and style are not indexed. `export const`
  and dynamic `import()` in JS/TS are read too.
- *A0 step 2* then brings `site/.vitepress/theme` into the graph, split into nodes.

**The shared core (`GraphViewer.vue` plus composables)**

- **Layout of the viewer's own space**: a toolbar at the top, the canvas, and a side panel that is
  collapsible. The element that goes full screen is the whole space, so the toolbar and the card
  come with it. The CSS fallback, for when the Fullscreen API is refused, covers the same element.
- **Navigation.**
  - `autoungrabify: true` by default: nodes cannot be dragged.
  - Compound parents are `pannable`, so pressing inside a domain box pans.
  - `boxSelectionEnabled: false`.
  - A toolbar toggle, "Arrange", re-enables node dragging for someone who wants to move nodes.
  - Buttons for zoom in, zoom out, fit and "centre on selection".
  - Keyboard: `+`, `-`, `0` to fit, `f` for full screen, `Esc` to clear the selection.
- **Colour resolution.** A composable reads the theme tokens through `getComputedStyle` on the
  viewer's root, converts them to rgb, builds the Cytoscape stylesheet, and rebuilds it when
  VitePress toggles dark mode. A browser test asserts that no rendered edge or node resolves to
  Cytoscape's fallback colour.
- **Edges.**
  - Direction reads from the target arrow plus a lighter source end.
  - `depends_on` is solid, `uses` dotted, `consumes`/`produces` dashed with their own colours.
  - Violations are red, thicker and dashed.
  - `part_of` stays as nesting and is not drawn as a line; the legend is generated from the edge
    kinds actually present, so it cannot list one that is not drawn.
  - Edge labels appear on hover and for the selected node's edges.
  - `curve-style: bezier` for cross-lane edges, with taxi kept inside a lane. The final choice is
    measured on this repository's graph in the browser.
- **Filters.**
  - The visible set is computed as a set of node ids, then ancestors of visible nodes are added
    back. Hiding a parent never hides a visible child.
  - Kind, domain (the full subtree, not only direct children), layer, violations, and a text search.
  - The state is serialised to the URL query (`?focus=&depth=&dir=&mode=&kind=…`), so a view can be
    linked.
- **Selection model.**
  - *Neighbourhood*: a breadth-first walk from the selected node over `depends_on`/`uses`/
    `consumes`/`produces`, with depth 1–5 or "all" and direction in/out/both. The set is shown and
    the rest dimmed; a toggle hides the rest instead.
  - *Impact*: the incoming walk without a depth limit, with distance recorded per node and drawn as
    rings (colour by distance). Risk marks come from the node data (no bound tests, stale docs,
    open findings). The panel summarises the count, domains, services, layer boundaries crossed
    and a list of the risky nodes, and states "graph view — not a reading of the code", with the
    `beadloom why`/`beadloom impact` commands to copy.
- **Side panel (the card).**
  - Every field the PRD names.
  - Edges are grouped by kind and direction, and a click on one moves the selection.
  - "Open page", "copy `beadloom ctx <ref>`" and "copy `beadloom why <ref>`".
- **Props**: `mode` (`architecture`/`landscape`), `focus`, `depth`, `direction`, `height`. The URL
  query overrides the props. Node pages pass `focus`.
- **Landscape** becomes the core's second mode, keeping its own filters (protocol, verdict, hide
  healthy) in the toolbar slot the mode provides.

**The data file, `architecture.data.json` `schema_version: 2`**

Each node gains the following:

- `source`;
- `lifecycle` and `tags`;
- `docs`: a list of `{path, status}` from `sync_state`, instead of one aggregate, with the aggregate
  kept as well;
- `tests`: `{files, count, placement}` from the BDL-074 binding;
- `symbols`: public names, capped at 50 with a count of the rest;
- `activity` from `nodes.extra`;
- `debt` from `NodeDebt`;
- `findings`: `{rule, severity, message}` from the lint run, instead of the boolean, with
  `lint_clean` kept;
- `url` for every kind. `component` and `site` pages under `other/` get their link, and
  `DiagramViewer`'s base-path rewrite gains `/other/`.

Edges gain `consumes`/`produces`. `touches_code` stays out, because it points at files, not nodes.
Top level gains `generated_at`, the `beadloom` version, the project name and the declared layers
(name, rank and order), from which the viewer builds its palette.

**Node pages**

`render_node_page` replaces the `## Diagram` Mermaid block with
`<ClientOnly><GraphViewer mode="architecture" focus="<ref>" :depth="1" /></ClientOnly>`, at a page
height of 60vh with its own full-screen button. The Mermaid C4 view stays on
`architecture-diagram.md` for readers without JavaScript.

**Browser tests (Playwright)**

- Tests live under `site/e2e/` and run against `vitepress build` output served by
  `vitepress preview`.
- In test mode the viewer exposes a read-only handle on `window.__beadloomViewer`: the visible ids,
  the selection, positions, and resolved colours. The tests assert state, not pixels.
- Cases, one per PRD goal:
  - a pan inside a domain box leaves every node position unchanged;
  - the filters;
  - neighbourhood depth and direction;
  - impact rings and the summary;
  - full screen contains the toolbar and the panel;
  - a node page opens focused;
  - the URL state round-trips;
  - no colour resolves to the fallback.
- A new CI job, `site-e2e`, installs Chromium and runs them after `site-build`. It is not required
  until it has run clean on ten pull requests.

**Slice 2 — the portal for adopters**

- **The scaffold moves into the wheel.** The theme, the components, the composables,
  `package.json`, `package-lock.json`, `config.mjs` and `e2e/` go to
  `src/beadloom/site_scaffold/` as package data.
- **`beadloom docs site` writes the scaffold** next to the content.
  - Every scaffold file carries a generated marker and is rewritten when the installed version
    differs.
  - A project override directory, `.beadloom/site/`, is copied last, so an adopter can add a page or
    a style without editing generated files.
- **Identity comes from `.beadloom/config.yml` `site:`**: `title`, `description`, `base` and
  `repo_url`, with defaults of the project directory's name, `/` and `git remote get-url origin`.
  Nothing names Beadloom unless the project is Beadloom.
- **The dashboard's ai-techwriter panel** mounts only when `.beadloom/ai_techwriter_runs.json`
  exists.
- **`beadloom docs site --pages-workflow`** writes `.github/workflows/<name>.yml`, which builds and
  deploys to GitHub Pages with Node 22.
- **This repository uses the same path.** `site/`'s tracked scaffold files are removed and
  gitignored, `deploy-site.yml` and `site-build` run `docs site` then build, and `.beadloom/config.yml`
  gains our `site:` block.
- **Fixtures** are one small project per claimed stack (Python, Go, JS/TS, Java, Kotlin, Swift),
  under `tests/fixtures/site/`. An integration test runs `init` → `docs site` → `npm ci` →
  `vitepress build` for each; it is marked slow and runs in the `site-e2e` job. The browser tests
  run on two of them, Go and TS, besides this repository.

### Changes

| File / Module | Change |
|---|---|
| `site/.vitepress/theme/components/GraphViewer.vue` (new), `useViewerStyle.js`, `useSelection.js`, `useFilters.js` (new) | the shared core |
| `ArchitectureMap.vue`, `LandscapeMap.vue` | thin wrappers over the core, or removed in favour of props |
| `architectureTheme.js`, `landscapeTheme.js` | tokens, not literal CSS vars; per-kind edge styles |
| `architecture_view.py` | `schema_version: 2`; the node fields; edge kinds; layers at top level |
| `site.py` | findings with rule/message; the debt and tests passed to the view; slice 2: writes the scaffold |
| `site_pages.py` | the node page embeds the viewer; `url` for every kind |
| `site/e2e/**`, `.github/workflows/ci.yml` | browser tests; the `site-e2e` job |
| slice 2: `src/beadloom/site_scaffold/**`, `pyproject.toml`, `commands/docs.py`, `deploy-site.yml`, `.gitignore`, `.beadloom/config.yml` | the scaffold in the wheel; `--pages-workflow`; our own site through the same path |

### API Changes

- **`architecture.data.json` goes from `schema_version` 1 to 2.** This is additive for any reader of
  v1 keys: every v1 key is kept.
- **`beadloom docs site`** gains the scaffold output, `--pages-workflow`, and the `site:` config
  block. This happens in slice 2, and the release notes name it.

## Alternatives Considered

### Option A: replace Cytoscape (e.g. with Sigma.js, React Flow or D3)
Rejected. Every defect traces to configuration, as measured, and a rewrite adds risk without adding
a capability we need. It is revisited only if the neighbourhood or impact walk is too slow on a
large adopter graph; the browser tests will time it.

### Option B: keep the Mermaid mini-diagram on node pages
Rejected by the owner: the focused main viewer is the requirement.

### Option C: ship the theme as an npm package
Rejected by the owner: the theme ships in the wheel, with one version.

### Option D: precompute code-level `impact` for the viewer
Deferred to `beadloom-ikj6`; the build's cost has to be measured first.

## Risks

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| ELK layout slow or messy on a large adopter graph | Medium | Unusable viewer | Browser tests time the layout on the largest fixture; a "collapse domains" control; the layout runs in a worker (already `web-worker`) |
| Colour tokens differ between VitePress versions | Low | Grey edges again | The fallback-colour browser test fails loudly |
| Browser tests are flaky in CI | Medium | Noise | State assertions via the test handle, not pixels; non-required until clean on ten PRs |
| Slice 2 overwrites an adopter's hand edits | Medium | Lost work | The generated marker plus the `.beadloom/site/` override directory; a file without the marker is never overwritten and is reported |
| The data file grows large (symbols, docs lists) | Low | Slow first paint | Symbols capped; measured on this repository and on the largest fixture |

## Open Questions

- [ ] The exact edge curve style (bezier or taxi, per lane): decided by measuring it in the browser
      on this repository's graph during slice 1.
