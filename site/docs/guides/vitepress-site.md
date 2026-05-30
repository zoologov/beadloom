# VitePress Site Guide

> 📘 **reference** — overview/guide, not tied to a single code symbol.

`beadloom docs site` turns the indexed architecture graph into a **VitePress
knowledge base** — a published, versioned, URL-shareable source of truth for
humans *and* agents. It is the F4 "Living Knowledge Base + Visual Landscape"
deliverable of Strategy 3.

> **Beadloom produces, VitePress renders.** Beadloom emits a deterministic
> Markdown/config content tree (plus a `dashboard.data.json` data file);
> committed Vue/ECharts components and VitePress (a static site generator) render
> it client-side. There is no live server, no SaaS, and no LLM in this path —
> freshness comes from rebuilding on push, the same way `beadloom ci` keeps the
> graph honest.

> **Build green ≠ renders ok.** A generation-time Mermaid validity guard rejects
> the diagram bug classes that crash the browser render *during generation /
> pytest* — no green `vitepress build` can hide a broken page (see the guard
> section below).

## What it generates

```bash
beadloom docs site [--out DIR] [--federated FILE] [--project DIR]
```

Reading the graph **read-only**, the command writes the following under `--out`
(default `site/`). It NEVER writes into the source `docs/` tree.

| Output | Showcase | What it is |
|--------|----------|------------|
| `index.md` | — | **About** — the home page (`/`), generated from `README.md` with links rebased so they resolve on the site (see [Information architecture](#information-architecture)). Falls back to the architecture overview if no README. |
| `ru/index.md` | — | **About (RU)** — the `/ru/` page, generated from `README.ru.md` by the same transform. The bilingual entry is an in-page cross-link, NOT VitePress locales (see below). |
| `architecture.md` | Architecture | Architecture overview (`/architecture`): node counts, the top-level C4/Mermaid diagram, a health summary line. (This is the page that used to be `index.md`.) |
| `domains/<ref>.md`, `services/<ref>.md`, `features/<ref>.md` | Architecture | One page per node: summary, source, public symbols, `part_of`/`depends_on`/`uses` edges as links, linked docs, an embedded scoped C4/Mermaid diagram. |
| `dashboard.md` + `dashboard.data.json` | **A — metrics dashboard** | An interactive ECharts dashboard: a critical-first alert banner + status cards, gauges, category charts, honest trends, and a recommendations panel. |
| `landscape.md` | **B — 🌟 landscape map** | The contract graph as an interactive (pan/zoom/fullscreen) Mermaid diagram. |
| `docs/**` + `docs/index.md` | **C — published validated docs** | The real `docs/` tree, copied verbatim, with per-doc freshness/reference badges. `docs/index.md` is a descriptive Documentation **Overview** (intro + per-section descriptions), not a flat link wall. |
| `.vitepress/config.generated.mjs` | — | Nav/sidebar config imported by the committed scaffold. The top nav is empty; the left sidebar is a single ordered EN tree (see [Information architecture](#information-architecture)). |

### Showcase A — interactive ECharts metrics dashboard

Beadloom emits a deterministic data file (`dashboard.data.json`) and a thin
`dashboard.md` page; committed Vue/ECharts components render it interactively in
the browser. The page itself is **just a title, a short intro, and the component
mounts** — there is no verbose per-metric text dump (it was removed in F4.4) and
no `<noscript>` fallback. The widgets, reading the honest data file, are the
single presentation surface:

- **`AlertBanner`** + **`StatusCards`** — the **critical-first** UX, shown at the
  top. `alerts` are the attention-banner problems (BREAKING contracts lead, then
  DRIFT / lint errors / doctor errors, then stale-doc / high-debt warnings),
  shown IFF something is wrong (an empty list = the all-clear state). `status_cards`
  is one threshold-coloured card per metric group (`ok`/`warn`/`error`, the
  severity computed deterministically in Python — the front-end only paints it).
- **`HealthGauges`** — gauges for lint, debt, coverage %, and freshness %.
- **`CategoryChart`** — debt-by-category and lint-by-severity breakdowns.
- **`TrendCharts`** — line charts over the recorded `trends` series; with fewer
  than two recorded points it shows an honest "not enough history yet" empty
  state (no fabricated line).
- **`Recommendations`** — the prioritized, actionable `recommendations` list
  (one item per lint violation, BREAKING/DRIFT contract risks, stale docs, worst-
  debt nodes), severity-ordered, each row linking to the relevant page.

**Honest trends.** `trends` is the time-series recorded in the additive
`.beadloom/metrics_history.json` append-log (seeded day-one from the existing
`graph_snapshots` history). It carries ONLY real recorded points — sparse at
first, growing one point per `docs site` run — with NO interpolation and NO
fabricated samples; every timestamp is a stored value, never wall-clock `now()`.

**Honest by construction.** Every figure comes from the *same code path* as the
gate that owns it: `lint` (`graph/linter.lint`), debt (`debt_report`), docs
(`doc_sync` `sync_state`), `doctor` (`doctor.run_checks`), and — when `--federated`
is given — the `federate` output verbatim (a per-service edge-verdict +
contract-verdict rollup). The dashboard cannot show a number the gate disagrees
with — it is the gate, rendered. The widgets never invent a figure the
`dashboard.data.json` does not contain.

### The generation-time Mermaid guard

Every Mermaid diagram Beadloom emits (the top-level and per-node C4 diagrams, the
landscape map) is run through a structural validity guard
(`application/site_mermaid_guard.validate_mermaid`) **before the page is written**.
The guard is a targeted set of structural validators (not a full Mermaid parser)
covering the two F4 render bug classes:

1. **Reserved-id / charset** — a flowchart/`graph` node id that equals a reserved
   Mermaid keyword (e.g. a node literally named `graph`, which produced the
   "got GRAPH" parse crash) or uses an illegal charset.
2. **C4 Rel integrity** — a `Rel(a, b, …)` whose endpoint is not a declared
   diagram node (a Rel to the boundary/`System` root, which crashed `drawRels`).

A structurally broken diagram raises `MermaidValidationError` and **fails
generation (and pytest)** instead of shipping a page that crashes the browser —
closing the "build green ≠ renders ok" gap. The two F4 bugs were fixed at the
source (landscape ids are now prefixed `n_<sanitized>`; C4 emits a `Rel` only
between declared nodes, dropping — and logging — undrawable Rels safely, since
the relationship still lives in the graph and the landscape map), and the guard
keeps the bug classes from regressing.

### Interactive diagrams — pan / zoom / fullscreen

All rendered Mermaid SVGs get pan + wheel-zoom + reset (via `svg-pan-zoom`) and a
Fullscreen toggle, applied by a global `DiagramViewer` theme component that scans
each page (and re-scans on route change, since Mermaid renders async). It is
SSR-safe and renders no markup of its own, so a JS-disabled viewer still gets the
static diagram.

### Showcase B — 🌟 the cross-repo landscape map

`landscape.md` renders the **contract graph** as a **Mermaid** diagram (with
pan/zoom/fullscreen, like every diagram on the site):

- **Without `--federated` (default — the local contract graph):** the map is the
  *repo's own* contract reality, not its structural arch. It reads the local
  graph's `produces` / `consumes` edges, reconciles them by `contract_key` into
  `Contract`s, classifies each to a verdict, and renders one edge per
  producer→consumer coloured by that verdict. Beadloom's own site, for example,
  models `beadloom --produces--> vitepress-site` and `vitepress-site --consumes-->
  beadloom` (sharing the `site-data:site-bundle` contract), so the local map is a
  single **`beadloom → vitepress-site` CONFIRMED** edge. A repo with no contracts
  renders an empty map. (The structural `depends_on` / `uses` arch lives in the
  C4 overview, not here.)
- **With `--federated federated.json`** (a `beadloom federate` hub artifact):
  nodes are the satellite services and edges are the cross-repo contract links,
  each carrying the hub's verdict (`CONFIRMED` / `BREAKING` / `ORPHANED_CONSUMER`
  / `UNDECLARED_PRODUCER` / `EXTERNAL` / `DRIFT` / …) verbatim.

Edges are labelled by their verdict; a Mermaid `classDef` health overlay colours
nodes (green = healthy, red = broken, grey = external/expected) and broken edges
get a red `linkStyle`.

**Safe clicks (no 404s).** A node is clickable to its intra-repo page ONLY when a
page was actually generated for it (`existing_page_urls` maps page-bearing kinds —
`service` / `domain` / `feature` — to `/<dir>/<ref>`). A node with no page (a
`site` node, or a foreign federated repo) renders without a click, so the map
never links to a dead URL.

This is the *thin slice*: Mermaid only (clickable). A richer JS graph library
(Cytoscape / D3) is a follow-up — no schema bump was needed for the Mermaid map.

### Showcase C — published validated documentation

`publish_docs` copies the **real** `docs/**` tree into `site/docs/…`, preserving
structure, and injects a per-doc validation badge into the **copy only**:

- The badge status comes from the `doc_sync` engine via `check_sync` — the SAME
  code path `beadloom sync-check` runs — so a doc the gate calls stale shows
  `stale — <reason>` on the site (`fresh` / `stale` / `untracked`). The badge
  also shows the stored `last synced` time (deterministic, not wall-clock) and
  the owning node's source-coverage %.
- The badge is wrapped between stable `<!-- beadloom:badge-start -->
> 📘 **reference** — overview/guide, not tied to a code symbol
> 
> _Validation by Beadloom `doc_sync` — same source as `sync-check`._
<!-- beadloom:badge-end -->

` markers, so regeneration overwrites ONLY the
  badge region and leaves the authored prose byte-for-byte intact.

**The published `docs/` is the source of truth.** The source tree is never
mutated; there is no AI prose-rewriting (that is the deferred F4.1 follow-up).
Badges come from `doc_sync`, not from a model.

## Information architecture

The portal (reshaped in BDL-046) leads with **About = the README as the landing
page** and a single ordered EN sidebar; there is **no top nav**. All of this is
emitted by `application/site_nav.py` into `.vitepress/config.generated.mjs`
(deterministic, sorted, byte-stable, link-safe — no dead entries).

### Left sidebar — exact order

`render_sidebar()` emits the sidebar in this fixed order:

```
About            → /            (link — README home; always present)
Getting Started  → /docs/getting-started   (link — emitted ONLY if the page exists)
Dashboard        → /dashboard   (link, FLAT — no "Metrics" child)
Architecture     → group, collapsed: true
                     • Architecture overview → /architecture
                     • <part_of tree…>       (service root → domains → features)
Landscape map    → /landscape   (link, FLAT — no "Map" child)
Documentation    → group, collapsed: false  (EXPANDED)
                     • Overview → /docs/
                     • <docs/ tree…>         (each subdir a group, each .md a /docs/-rooted leaf)
```

- **Dashboard** and **Landscape map** are flat `{ text, link }` entries (the old
  single-child "Metrics" / "Map" groups were removed).
- **Architecture** stays `collapsed: true` with the human-readable `part_of` tree
  (`context-oracle` → "Context Oracle"); the "Architecture overview" entry leads
  it and points at `/architecture` (the page that used to be the `/` landing).
- **Documentation** is `collapsed: false` (expanded) and led by an **Overview**
  (`/docs/`). Roots in the Architecture tree are nodes with no real `part_of`
  parent (a `root part_of root` self-edge is ignored so the root service isn't
  dropped). Every link resolves to a generated page.

### About = README landing (EN `/`, RU `/ru/`)

`application/site_about.render_about()` turns the `README.md` into the `/` home
page (and `README.ru.md` into `/ru/`), **rebasing** repo-relative links so they
resolve on the published site:

| README link target | Rebased to |
|--------------------|------------|
| `docs/<x>.md` whose slug `<x>` is published | extension-less site link `/docs/<x>` |
| `README.ru.md` / `README.md` cross-link | rewritten to the counterpart route (`/ru/` ↔ `/`) — the bilingual toggle (see below) |
| `LICENSE`, source paths, an unpublished `docs/<x>` | absolute GitHub URL `https://github.com/<owner>/beadloom/blob/main/<path>` |
| external URLs + shields.io badges + pure anchors | unchanged |

The transform is pure and deterministic, leaves prose / inline code / fenced
blocks untouched, and handles the badge-link idiom `[![alt](img)](target)`
(rebases the outer link, recurses the inner image). The About page is plain
Markdown (no `layout: home` hero) so it reads identically to the README on
GitHub. If no README exists, `/` falls back to the architecture overview.

### Bilingual About via in-page cross-link (NOT VitePress locales)

The language toggle is an **in-page cross-link**: `render_about` rewrites the
README's `[Русский](README.ru.md)` / `[English](README.md)` line to the
counterpart route (`/` ↔ `/ru/`), driven by `site._CROSS_LINK_ROUTES`. The
toggle therefore appears ONLY on the two About pages and never 404s elsewhere;
the rest of the portal stays EN.

> **Why not VitePress `locales`?** It was evaluated and **dropped**. The
> default-theme locale switcher does a global `/x ↔ /ru/x` path mapping for
> *every* page, so in dogfooding it (a) translated the whole menu — even though
> only About is bilingual — and (b) 404'd when clicked on any page other than
> `/ru/`, because no mirrored RU tree exists. A single curated About-only
> in-page link gives the bilingual entry without a mirrored tree or a translated
> menu. (`navRu` / `sidebarRu` / a `locales` config block were all removed.)

### Empty top nav

The top `nav` is `[]` (`render_nav()` returns `[]`). The VitePress default theme
still renders the **appearance (light/dark) toggle** and the **built-in local
search** in the nav bar independently of `nav` entries, so removing the nav items
keeps both. (There is no locale switcher — see above.)

### Documentation Overview

`docs/index.md` is generated by `site._render_docs_overview()` as a short
**descriptive** page: a one-paragraph intro plus a `## <Group>` heading per
top-level docs group (Domains / Services / Guides / …) followed by a single
sentence that NAMES that group's members as inline, human-labelled **text** —
deliberately **not** a second copy of the sidebar tree (the expanded
Documentation sidebar is the navigable map; a duplicate link wall read poorly in
dogfooding). It is link-safe (no links at all) and deterministic.

### How feature docs get tracked + the reference badge

Published docs carry a per-doc badge (injected into the `site/docs/` **copy**
only, between `<!-- beadloom:badge-start -->` / `<!-- beadloom:badge-end -->`
markers; the source `docs/` is never mutated):

- A doc tied to a code symbol shows `✅ fresh` or `⚠️ stale — <reason>`, computed
  by `doc_sync` via the SAME path `beadloom sync-check` runs.
- A doc tracked by **no** sync pair (an overview/guide, like this one) is badged
  neutrally as **`📘 reference — overview/guide, not tied to a code symbol`** —
  it is not a defect, so it shows no coverage % (which would read as a
  contradiction). This reworded badge replaced the old "untracked" wording.

A **feature SPEC** becomes "tracked" (so its doc shows fresh/stale, not
reference) by adding a per-symbol annotation comment to the owning source file:

```python
# beadloom:feature=<ref>
```

`doc_sync`'s `build_sync_state` reads file-level `# beadloom:feature=<ref>` /
`# beadloom:domain=<ref>` annotations (parsed by `_FILE_ANNOTATION_RE` in
`doc_sync/engine.py`) to bind a source file to a graph node — even when the file
has no extractable top-level symbol — so the file counts as tracked and its SPEC
is freshness-checked. (This is the annotation, NOT the YAML `source:` field, that
drives per-SPEC freshness.)

## Building and previewing

The committed VitePress **scaffold** (`site/package.json`,
`site/.vitepress/config.mjs`, and the custom theme under
`site/.vitepress/theme/` — `DiagramViewer` + the ECharts dashboard widgets, with
`echarts` / `vue-echarts` / `svg-pan-zoom` pinned to exact versions) renders the
generated content tree. The build output (`site/.vitepress/dist/`), the VitePress
cache, and `site/node_modules/` are gitignored — only the scaffold and the
generated, deterministic Markdown/config/data are committed. The Python generator
and the Mermaid guard stay fully pytest-testable without Node.

```bash
# 1. Generate the content tree from the indexed graph (run `beadloom reindex` first).
beadloom docs site --out site

# 2. Build the static site.
cd site && npm install && npm run docs:build

# 3. Preview the built site locally.
npm run docs:preview          # or `npm run docs:dev` for a live-reload dev server
```

For the landscape map (Showcase B), feed a federation artifact:

```bash
beadloom federate service-a.json service-b.json   # writes .beadloom/federated.json
beadloom docs site --out site --federated .beadloom/federated.json
```

### Deploy to GitHub Pages

Beadloom ships a ready deploy workflow: **`.github/workflows/deploy-site.yml`**. On every push to `main` (or manual `workflow_dispatch`) it regenerates the site from the graph (`beadloom reindex && beadloom docs site --out site`), runs `npm ci && npm run docs:build`, and publishes `site/.vitepress/dist` via `actions/upload-pages-artifact` + `actions/deploy-pages` (with `pages: write` + `id-token: write` and a `pages` concurrency group). Because CI regenerates the site, the published page never drifts from the code.

This repo is served as a **GitHub project page** at `https://zoologov.github.io/beadloom/`, so `site/.vitepress/config.mjs` sets `base: "/beadloom/"`. VitePress prepends that base to markdown/nav links at build time; Mermaid diagram `click` targets are raw strings the plugin does not rewrite, so `DiagramViewer.vue` prepends `import.meta.env.BASE_URL` to internal click hrefs at runtime (the generated Markdown stays base-agnostic).

**One-time setup (repo owner):** Settings → Pages → **Source = GitHub Actions**. Then the first push to `main` deploys the site.

> For a user/organization page or a custom domain served at the root, drop `base` (defaults to `/`) — no other change needed; the base-aware click rewrite is a no-op when base is `/`.

## Determinism

Identical graph → byte-identical tree: pages are sorted, frontmatter is stable,
and no wall-clock value lands in the diffed output (the published-doc badge uses
the stored `sync_state.synced_at`, not "now"; the dashboard's `dashboard.data.json`
— including `trends` and `recommendations` — and the generated Mermaid are sorted
and byte-stable; the only wall-clock read is the metrics-history point appended to
`.beadloom/metrics_history.json`, which never lands in a diffed dashboard field).
This makes the generated tree safe to commit and to diff in review, and makes a
rebuilt site reproducible.

## Where this fits — TUI vs VitePress

- **TUI** (`beadloom tui`) is the engineer's *live, per-repo workstation* — "what
  is happening now," real-time, over SSH.
- **VitePress** is the team's *published, landscape-wide source of truth* —
  versioned, URL-addressable, readable by humans and agents alike. It is the
  channel for PMs, new devs, other teams, and URL-reading agents.

## Scope and follow-ups

- **Portal IA + bilingual About (BDL-046):** About = README as the landing
  (`/`); a single ordered EN sidebar (About / Getting Started / flat Dashboard /
  collapsed Architecture with a `/architecture` overview / flat Landscape map /
  expanded Documentation led by a descriptive Overview); empty top nav (theme
  toggle + search retained); bilingual About via an in-page `/` ↔ `/ru/`
  cross-link (VitePress `locales` evaluated and dropped); feature SPECs tracked
  via per-symbol `# beadloom:feature=<ref>` annotations; the neutral "📘
  reference" badge for overviews/guides. Browser-confirmed on the deployed site.
- **Delivered (F4.2 / F4.3):** the `docs site` generator, all three showcases,
  and the committed VitePress scaffold — dogfooded by building Beadloom's own
  site (`vitepress build` exit 0).
- **Hardened (F4.4):** render correctness (the two F4 Mermaid bugs fixed at the
  source + the generation-time validity guard), pan/zoom/fullscreen on every
  diagram, the interactive ECharts dashboard (critical-first banner + cards,
  gauges, category charts, honest trends, recommendations — the old text dump
  removed), and the local contract-graph landscape with safe (page-aware) clicks.
  Dogfooded on Beadloom's own site (real `vitepress build` exit 0, render
  browser-confirmed). F4 and F4.4 ship together.
- **Deferred (F4.1):** the AI tech-writer in CI — orchestrating an *external*
  model to refresh drifted docs, scoped by `sync-check` / `docs polish --json`,
  with team review on a PR. The published-docs showcase intentionally does NOT
  rewrite prose today; badges are computed, not generated.
- **Deferred:** a richer JS graph library for the landscape map (Cytoscape / D3)
  beyond the current clickable Mermaid thin slice; REST/OpenAPI + gRPC contracts
  in the federated map.

See the [`beadloom docs site` CLI reference](../services/cli.md#beadloom-docs-site),
the [application domain README](../domains/application/README.md) for the
generator modules, and the [federation SPEC](../domains/graph/features/federation/SPEC.md)
for the contract graph the landscape map renders.
