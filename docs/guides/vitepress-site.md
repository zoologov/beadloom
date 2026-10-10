# VitePress Site Guide

> 📘 **reference** — overview/guide, not tied to a single code symbol.

`beadloom docs site` turns the indexed architecture graph into a **VitePress
knowledge base** — a published, versioned, URL-shareable source of truth for
humans *and* agents. Any project indexed by Beadloom gets it: the theme ships in the
package, and the project's own identity comes from its configuration.

> **Beadloom produces, VitePress renders.** Beadloom emits a deterministic
> Markdown/config content tree plus three data files (`architecture.data.json`,
> `landscape.data.json`, `dashboard.data.json`), and writes beside them the theme
> it ships (Vue, Cytoscape with ELK, ECharts); VitePress (a static site generator)
> builds the result. There is no live server, no SaaS, and no LLM in this path —
> freshness comes from rebuilding on push, the same way `beadloom ci` keeps the
> graph honest.

The steps from installation to a published portal are in
[Getting Started](../getting-started.md#publish-the-portal). This guide describes what the
portal shows, how it is built, and every setting it reads.

> **Build green ≠ renders ok.** A generation-time Mermaid validity guard rejects
> the diagram bug classes that crash the browser render *during generation /
> pytest* — no green `vitepress build` can hide a broken page (see the guard
> section below).

## What it generates

```bash
beadloom docs site [--out DIR] [--federated FILE] [--pages-workflow] [--project DIR]
```

Reading the graph **read-only**, the command writes the following under `--out`
(default `site/`). It NEVER writes into the source `docs/` tree. Besides the content below, it
writes the portal's scaffold (see [The portal for your project](#the-portal-for-your-project)).

| Output | Showcase | What it is |
|--------|----------|------------|
| `index.md` | — | **About** — the home page (`/`), generated from `README.md` as [project text](#project-text-on-the-portal). Falls back to the architecture overview if no README. |
| `ru/index.md` | — | **About (RU)** — the `/ru/` page, generated from `README.ru.md` by the same transform, only when that file exists. The bilingual entry is an in-page cross-link, NOT VitePress locales (see below). |
| `architecture.md` + `public/architecture.data.json` | Architecture | The architecture viewer (`/architecture`): the interactive graph described in [the architecture viewer](#the-architecture-viewer), with a static count summary for a reader without JavaScript. |
| `architecture-diagram.md` | Architecture | The Mermaid fallback: node counts, the top-level C4 diagram, a health summary line. |
| `domains/<ref>.md`, `services/<ref>.md`, `features/<ref>.md`, `other/<ref>.md` | Architecture | One page per node of every kind: summary, source, public symbols, `part_of`/`depends_on`/`uses` edges as links, linked docs, and the viewer opened on the node. |
| `dashboard.md` + `dashboard.data.json` | **A — metrics dashboard** | An interactive ECharts dashboard: a critical-first alert banner + status cards, gauges, category charts, honest trends, and a recommendations panel. |
| `landscape.md` + `public/landscape.data.json` | **B — 🌟 landscape map** | The contract graph in the viewer's landscape mode. |
| `landscape-diagram.md` | **B — 🌟 landscape map** | The same contract graph as a Mermaid diagram with pan, zoom and full screen. |
| `docs/**` + `docs/index.md` | **C — published validated docs** | The real `docs/` tree, each document as [project text](#project-text-on-the-portal), with per-doc freshness/reference badges. `docs/index.md` is a descriptive Documentation **Overview** (intro + per-section descriptions), not a flat link wall. |
| `.vitepress/config.generated.mjs` | — | Nav/sidebar config imported by the shipped `config.mjs`. The top nav is empty; the left sidebar is a single ordered EN tree (see [Information architecture](#information-architecture)). |
| `.vitepress/site.generated.mjs` | — | The portal's identity from the [`site:` block](#configuration-reference-site): title, description, base, repository link and its icon, the nav logo's address and whether it is drawn in the text's colour, the favicons and the footer switch. |
| `public/logo.svg` or `public/logo.png` | — | The project's own logo, copied byte for byte from `site.logo`, only when the project declares one. |
| `public/brand/beadloom-favicon.svg`, `.png` + `-dark.png` | — | Beadloom's favicon, written only when the portal shows it: without a logo of the project's own. |

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
- **`RuleFindings`** (BDL-080) — the population lint's numbers were counted over: lint's totals
  with how many of them sit on how many nodes and how many on none, on this repository's portal
  `This project: 0 errors, 69 warnings — 33 on 27 nodes, 36 on none.`, then every finding
  bound to no node with its rule, severity, message and `file:line`. A node's own findings are
  on its card.
- **`PageMap`** (BDL-080) — the pages the `docs site` run wrote: `beadloom docs site wrote 297
  pages; the About page in en (index.md), ru (ru/index.md).` on this repository's portal, then
  each section's pages in the sidebar's order (about, dashboard, architecture, nodes,
  landscape, docs). A file you place under `.beadloom/site/` is on the portal and not counted.
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

Every Mermaid diagram Beadloom emits (the top-level C4 diagram on
`architecture-diagram.md`, the landscape diagram on `landscape-diagram.md`) is run
through a structural validity guard (`application/site/mermaid_guard.validate_mermaid`)
**before the page is written**.
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
each page (and re-scans on route change, since Mermaid renders async, and whenever a
theme switch renders a diagram again). It is SSR-safe and renders no markup of its
own, so a JS-disabled viewer still gets the static diagram.

### Showcase B — 🌟 the cross-repo landscape map

`landscape.md` renders the **contract graph** in the viewer's landscape mode (see
[the landscape](#the-landscape)), and `landscape-diagram.md` renders the same graph
as a **Mermaid** diagram (with pan/zoom/fullscreen, like every diagram on the site):

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

The `--federated` artifact reaches the Mermaid diagram (and the dashboard) only; the
viewer's landscape always reads the project's own contract graph.

In the Mermaid diagram edges are labelled by their verdict; a `classDef` health
overlay colours nodes (green = healthy, red = broken, grey = external/expected) and
broken edges get a red `linkStyle`.

**Safe clicks (no 404s).** A node is clickable to its intra-repo page ONLY when a
page was actually generated for it. Every node of the project's own graph has one,
under `other/` for a kind with no directory of its own (a node declared `kind: site` is read as a
service, so its page is under `services/`); a foreign federated repo has
none and renders without a click, so the map never links to a dead URL.

### Showcase C — published validated documentation

`publish_docs` copies the **real** `docs/**` tree into `site/docs/…`, preserving
structure, passes each Markdown copy through the [project-text path](#project-text-on-the-portal),
and injects a per-doc validation badge into the **copy only**:

- The badge status comes from the `doc_sync` engine via `check_sync` — the SAME
  code path `beadloom sync-check` runs — so a doc the gate calls stale shows
  `stale — <reason>` on the site (`fresh` / `stale` / `untracked`). The badge
  also shows the stored `last synced` time (deterministic, not wall-clock) and
  the owning node's source-coverage %.
- The badge is wrapped between stable `<!-- beadloom:badge-start -->` /
  `<!-- beadloom:badge-end -->` markers, below the document's front matter when it
  has one that VitePress can read, so regeneration overwrites ONLY the badge region.
  Front matter VitePress cannot parse would fail the build at the top of the page, so
  the badge then goes first and the block below it shows as Markdown.

**The published `docs/` is the source of truth.** The source tree is never
mutated; there is no AI prose-rewriting (that is the deferred F4.1 follow-up).
Badges come from `doc_sync`, not from a model.

## The architecture viewer

The viewer is one component in three places, and it draws only what the data files say:

- **`/architecture`** shows the whole architecture graph.
- **Every node page** has a **Graph** section: the same viewer, 60% of the window high, opened
  with the page's node selected, its neighbourhood one step deep and its card open. From there
  every control works as on `/architecture`, and the selection can move anywhere.
- **`/landscape`** shows the contracts between services, in the viewer's landscape mode.

The viewer reads the data file of the last `beadloom docs site` run. It does not query the index,
so a picture is as current as the build that published it.

### Reading the picture

BDL-078 gave the viewer its present look. If you knew the earlier one: there are no thick lines,
no bridges, no dots where lines part and no colour gradient along a line any more.

- **Nodes are cards.** Every node, a feature or a domain box alike, is a card in its layer's
  colour: a thin border over a light tint of it, its title in the middle, its corners rounded at
  one radius on screen at every zoom. The layers are the ones the project declares, top to
  bottom, so an adopter sees its own names. Every `layers` rule in `rules.yml` is drawn: a node
  takes the colour of its layer in the rule that places it (its own tag first, else its nearest
  tagged container's), and each rule's layers have tones of their own. A node in no layer is drawn
  in a neutral grey and the legend then names **no layer**. An open box is a fainter tint inside a thin solid border, with
  its title inside at the top. The one box that holds the whole project is a frame: a border a
  pixel wide and a tint fainter than any node.
- **Node status is a mark in the corner.** A node carries at most one status, as a dot in its top
  right corner, and its border stays its layer's: a filled red dot is a rule violation (a finding
  of severity `error`, what `beadloom lint --strict` fails on), a filled yellow dot is stale docs,
  a yellow ring is a rule warning (findings of severity `warn` only). A node with none has no
  mark.
- **One thin line weight.** Every line is drawn at one thin weight at every zoom, whatever its
  kind or how many edges it carries. Kinds differ by colour and dash: `depends_on` solid in a
  light neutral (an import), `uses` dotted (a declared runtime use), `consumes` and `produces`
  dashed with different dashes and tones. A `depends_on` edge any layer rule finds against is
  dashed in red, exactly when `beadloom lint` reports it. A line is one colour from end to end.
- **Arrowheads carry the direction.** A head is one size on screen and stands on a straight piece
  of line at least as long as itself. Lines that share their last run into a node or a box end in
  one arrowhead, not one per line; lines that reach a side separately keep their own, with a gap
  between them.
- **Routes.** A line runs at right angles, around every box it does not connect, and enters its
  target on a side. Where lines that ran together part, the turning line leaves in a rounded merge
  on the stroke. An edge from a node into the box that holds it is drawn the same way, a square
  line from the node to the box's border.
- **Labels on hover.** A line's kind is shown only while the pointer is on it. Counts are on pills
  (below).
- **The legend** under the canvas lists the layers, the node statuses (each as a small card
  with its mark) and the line styles drawn at the level on the canvas now, each sample in the
  colour the canvas uses, so it never names something the canvas does not show. A line of the
  map that carries one kind of edge keeps that kind's dash. A line that carries several kinds
  is drawn solid in the colour of the kind it carries most, and while one is drawn the legend
  adds the entry "several kinds: solid, in the colour of the kind it carries most". Where two
  or more layer rules are drawn, the layers are grouped per rule under the rule's `title:` (its
  name where it declares none), each group top to bottom.
- **Layer boxes.** A layer rule scoped to a box inside the project, such as a Feature-Sliced
  frontend's rule scoped to its service, draws one box per layer inside that box, each holding the
  parts the rule places in that layer, stacked top to bottom. A layer box is no node: it has no
  card and no page, and a tap on it selects nothing. The box holding them opens only where they
  are readable, also when you tap it: at the zoom that frames it whole it stays closed and titled.
  The scope is the rule's `scope:` key, or else the lowest box holding every node the rule places.
  A rule whose scope is the whole project draws its layers as lanes, as before.

### Laying out

The layout is computed in the browser, in the background, so the page stays responsive meanwhile.
Until it is ready the canvas says **Laying out the graph…**, and the toolbar already works. The
layout is computed once per data file: the architecture page, a node page and full screen draw
the same layout, and a page you return to without reloading does not wait for it.

If the layout cannot run, a note above the canvas says so and names the error. The canvas stays
hidden and the filters, the neighbourhood, Impact and the navigation buttons are off. Panel and
Full screen still work, and the static summary on the page remains the source of truth.

### The overview

At the whole-graph fit the architecture is drawn like a map: the top-level boxes, closed, and
between two of them one line that carries every edge between them and their contents.

- **Its own routing.** The overview's lines are routed together, around every box and title:
  parallel lines keep a visible gap, each line runs straight into its box with room for its
  arrowhead, no line runs under a title, and lines inside the project's frame stay inside it.
  Measured on this repository's graph before and after BDL-078: overlapping arrowhead pairs went
  from 12 to 0, the smallest gap between parallel lines from 0.8 px to 7.1 px, lines under a
  title from 13 to 0. The routes are planned once for what the filters show; zooming or opening
  a box moves none of them.
- **Calm by default.** At rest the lines are thin and light. Point at a box, or select it, and its
  lines and their counts come forward while every other line fades; move away and all are back
  at rest.
- **Counts on pills.** A line that carries more than one edge says how many on a small pill on the
  line, which no other line paints over and which covers no box, title, arrowhead or other pill.
  A line that carries one edge has no pill. Where a pill finds no free place it is left out, and
  the line's count shows in the note while the pointer is on the line. A closed box large enough
  on screen says how many edges come in and go out in its lower right corner, `in 12 · out 7`.
- **Titles.** A box's title is drawn inside it at 14, 12.5, 11 or 10 px, the largest that fits. A
  top-level box too small for its title is drawn a little larger around its place, never moving;
  where even that does not fit one line, the name is broken onto two. Only a title neither way
  fits stands beside its box on a plate with a border, and no line runs under it.
- **At most 100 lines.** When the map would draw more, the weakest lines are left out, and each
  box counts its lines left out as **+N** under its title. With the pointer on a box, or the box
  selected, all of its lines are drawn.

The overview is made for a project whose top level fits the canvas. For a project whose
top-level boxes come out a few pixels across, a further grouping tier is deferred; such an
overview is drawn as it lays out.

### Zooming in: boxes open when you can read them

- **A box opens when its nodes are readable.** Once you have zoomed in past 1.3 times the
  whole-graph fit, a box in view opens when its smallest node is about 24 pixels tall on screen,
  and closes again below 90% of that. An open box draws its children and the edges among them,
  and boxes inside it open the same way. Nothing moves between levels: every box keeps its place
  and size.
- **An open box keeps its outward edges on its own lines.** An edge between a node inside the box
  and anything outside it stays on the box's line to that neighbour, so opening a box moves no
  line and changes no count around it. A node inside whose edges leave the box this way carries
  a small **+N** badge on its right side. Point at the node, or select it, and its own edges to
  the outside are drawn on top, one line to each box they reach, each with its count.
- **Edges to the box's own container** stay drawn, as square lines to the border.
- **Filters compose with the map.** The search box opens the boxes that hold its matches. Other
  filters open nothing: a closed box stays closed, and its lines carry only the edges the filters
  show.
- **Marks keep their size.** Line weight, arrowheads, corners, titles and pills keep one size on
  screen as you zoom.

The landscape has no boxes, so it is always drawn in full.

### Shared lines: trunks and buses

A node with many edges would otherwise leave its side in a staircase, one channel per edge. The
viewer gathers them instead, without moving any node:

- **A bus.** The edges that leave one side of a node in one direction start from the middle of
  that side and run along one line before each turns off into its own lane.
- **A trunk.** A node with twenty or more drawn edges sends its edges to one top-level box along
  one route, up to a line along that box, where each drops in where it enters.

Where edges that ran together part, the turning one leaves in a rounded merge; there is no dot.
With the pointer on a shared line, a note over the canvas names the edges along it: the first
eight, then "and N more". Outside a selection, edges fade in colour rather than turning
see-through, so a trunk of faded edges is no darker than one faded edge.

### Following a line

The line under the pointer, the lines of the node under the pointer, and every line of a
selection's walk are drawn on top of everything they cross, in their full colour, over a thin
casing in the canvas's colour that clears the lines beneath. So you can follow one line through a
busy area without anything drawn across it. Where such a line runs through an open box's title,
the title is drawn again over it.

### Moving around

A drag pans the canvas, on a node or inside a box too, and the scroll wheel zooms. No gesture
moves a node: the edges are drawn from the layout, and a moved node would leave them behind.
Earlier versions had an **Arrange** button that made nodes draggable, and BDL-077 removed it.
The toolbar has zoom in and out, **Fit** (the visible graph), **Centre** (on the selection),
**Panel** (show or hide the panel) and **Full screen**. With focus in the viewer, `+` and `-`
zoom, `0` fits, `f` toggles full screen and `Esc` clears the selection. Fit and centre leave out
the part of the canvas the open panel covers.

### Filters

On the architecture: **Kind**, **Domain** (the domain and everything inside it), **Layer** (where
two or more layer rules are drawn, each layer named with its rule's title, such as
`FSD architecture: widgets`; the URL carries the rule's name instead, `site-fsd-layers: widgets`,
and a link naming a bare layer still opens on it), a search box (id or label, ignoring case) and **Only flagged** (nodes with a status). The boxes
that hold a shown node stay, so a filtered feature is still drawn inside its domain. On the
landscape: **Protocol**, **Verdict** (problems, healthy or neutral) and **Only problems**; a
service is shown when it takes part in a shown contract.

### The neighbourhood

A click on a node selects it: its card opens in the panel and its neighbourhood is marked. Three
toolbar controls set the neighbourhood:

- **Depth:** 1 to 5 steps, or `all`.
- **Direction:** `outgoing` follows the arrows (what the node depends on, uses, consumes or
  produces), `incoming` goes against them (what reaches the node), `both` is the two together.
  "Both" does not turn round on the way: a walk that could would reach nearly the whole graph at
  depth 2.
- **Hide the rest:** hide what the neighbourhood leaves out instead of dimming it. The boxes
  around what it reached stay.

A selection — a click, a search, a link, the card or a node page — zooms and pans the view to the
neighbourhood, never so far out that the node is too small to read, in a short animation, or at
once when your browser asks for reduced motion. A click on a box selects the box: it opens (a box holding layer boxes opens once they
are readable), is framed whole, keeps its contents at full strength, and draws its edges to the outside as pointing
at it does; its card says what it holds. Selecting a node with the default neighbourhood draws its
edges on the same lines pointing at it draws them, each line with its count; change the depth,
the direction or the hide setting, or turn on Impact, to open the boxes of every node the walk
reaches.

A click on the empty canvas, or `Esc`, clears the selection and shows the whole graph again.

### Impact on the architecture

**Impact** in the toolbar answers "what does a change to this node reach?". It walks from the
selected node to everything that depends on it, then to what depends on those, with no depth
limit, backwards along `depends_on`, `uses` and `consumes`. Each reached node is filled with the
colour of its distance: direct dependents are ring 1, theirs ring 2, and so on. The panel then
shows:

- how many nodes depend on the selected one, and how many at each distance;
- the domains and the services that hold them;
- each crossing between two layers on the walked edges, with a count;
- the risky nodes, each with its reasons, also marked on the canvas with a dashed red outline:
  **no bound tests**, **stale docs** (a doc compared and found out of date), **docs not checked**
  (a doc with no sync pair, or whose pair could not be compared), **open findings**. A click on
  one selects it;
- `beadloom why <ref>` and, when the node has a source, `beadloom impact <source>`, to copy.

What it does not claim: it is the graph's view, and the panel says so. The edges come from
imports and declarations; the walk says nothing about how the code behind a node uses what it
imports, and it does not follow `produces`. The two commands are the code-level answer.

### The landscape

On `/landscape` a service is a node and a contract is an edge from its producer to its consumer.
A service's border is its health: green healthy, red broken, grey neutral. A contract edge is
drawn by its health: healthy solid green, drifting dashed yellow, broken dashed red with its
verdict as a badge, neutral dotted grey (external, expected, dead or unmapped). The
neighbourhood controls work here as on the architecture.

**Impact on the landscape** walks each contract from its producer to its consumers, then to their
consumers, with no depth limit and whatever the protocol. A change to a service reaches the
consumers of what it produces, never its producers. The panel shows how many services are
reached and at which distance, the contracts crossed, their protocols, the broken contracts on
the path, and each reached service at risk: one that takes part in a **broken contract** or an
**unverified contract**. A contract is unverified when it is not broken and its verdict was not
decided by comparing the two sides' declared surface (its `verdict_basis` is not `surface`), for
example a plain dependency whose verdict only says that both sides exist. The commands to copy are
`beadloom why <ref>` and `beadloom ctx <ref>`.

What it does not claim: it follows the contracts as the reconciler recorded them. It does not
read either side's code, and it does not say that a consumer uses the part of a contract a change
touches. On this repository the one contract, `site-data:site-bundle` from `beadloom` to
`vitepress-site`, is confirmed on the presence of both sides only, so its consumer shows as at
risk through an unverified contract.

### The two cards

The panel shows a card for the selected node, one kind per mode.

- **The architecture card:** the node's id and summary; kind, lifecycle, tags; its layer and
  whether that is its own tag or inherited from its container; its source; its activity; its
  debt with the reasons; its docs, each with its sync status and a link to the published copy
  when there is one; its bound tests with their count, placement and the files bound to the
  node itself; its first 50 public symbols and how many more there are; its edges by kind and
  direction, where a click selects the other end; its rule findings with their severity, said
  against lint's reach over the whole project, on this repository's portal
  `none — this project: 0 errors, 69 warnings — 33 on 27 nodes, 36 on none`, so "none" is not
  read as "lint never ran"; a link to its page; `beadloom ctx <ref>` and `beadloom why <ref>`
  to copy; for a box, what it holds and how many of its edges go out to and come in from each
  neighbour, and its debt said twice, its own and the debt of the nodes inside it by reason.
  The card of the box that holds the whole project also lists the findings bound to no node,
  with the file and line each points at. "None" means the data file holds nothing for the field; "not recorded" means
  the file does not carry the field at all.
- **Activity** counts changed lines (added plus deleted) over the last 30 days, not commits, so a
  squash-merged history reads the same as any other: `412 lines changed in 30 days, hot`. The
  levels are relative to your project: among the nodes changed in 30 days, the busiest tenth is
  `hot`, the next three tenths `warm` and the rest `cool`; a node with no change in 30 days but
  some in 90 says `no change in 30 days, quiet`, and none in 90 `no change in 90 days, dormant`.
  Boxes are ranked among boxes and include their parts' changes; other nodes are ranked among
  themselves. Because the levels are relative, a node's level can change when the rest of the
  project does. Lock files, files git's attributes mark `linguist-generated` or `binary`, and
  the patterns your project lists under `activity.exclude` in `.beadloom/config.yml` do not count
  (see [Getting Started](../getting-started.md#configuration)). Activity is measured on the
  history the build checked out: on a shallow clone that does not reach back 90 days it is not
  recorded and the card says "not recorded".
- **The source link** points at the source as it was in the commit the site was generated from.
  The repository is the one `site.repo_url` declares, else the project's `origin`. The generator
  writes the link for a forge it recognises by the host: GitHub, GitLab, Bitbucket, Gitea,
  Codeberg and Azure DevOps by their public hosts, and any host the project declares under
  [`site.forges`](#forges-a-self-hosted-forge). For any other host the card shows the source as
  plain text, because a guessed address would be a dead link. Nothing else from the git remote
  is published.

  A portal built from a commit that no branch of `origin` holds, such as a local build before a
  push, would link every node to a page that does not exist, since the forge has never seen
  that commit. Its links name a branch `origin` holds instead: the upstream of the branch the
  commit is on when that upstream is on `origin`, else `origin`'s branch of the same name, else
  `origin`'s default branch (`origin/HEAD`). With none of them they keep the commit. Only
  `origin` counts, because without `site.repo_url` the links name `origin`'s address: a commit
  or an upstream that only a fork holds would be a 404 there too (BDL-080 S4h). The stand-in
  branch and `pushed` are judged by `origin`'s branches even when `site.repo_url` names a
  repository on another forge, a decision of BDL-080 that may be revisited. A path that exists
  only in the unpublished commit is still missing on the branch. The card says `built from an
  unpublished commit; links point at main` under the link, and `docs site` warns on stderr,
  naming the fix when no branch stands in:

  ```text
  Warning: the portal was built from 39f9247dddfd, which is on no branch of origin, so its source
  links point at main instead; a path that exists only in that commit is not there. Push the
  commit and run `beadloom docs site` again for links to it.
  ```

  Only the refs the clone already holds are read, and the remote is never contacted. A CI
  checkout of a pushed branch holds the commit it builds under a remote-tracking ref of
  `origin`, so a portal built there links the commit.
- **The service card** on the landscape: the service's kind, health, number of contracts and page,
  then every contract it produces or consumes, with its verdict, protocol, routing, the fields or
  the message body each side declares ("undeclared" when a side declared none) and, for a
  breaking contract, the references the producer does not serve. A click on a producer or a
  consumer selects it. A contract with no declared protocol is shown as a plain dependency.

### Full screen

**Full screen**, or `f`, takes the whole viewer to full screen: the toolbar, the canvas, the panel
and the legend. In the page the panel lies over the canvas's right edge; in full screen it sits
beside the canvas. Where the browser refuses the Fullscreen API, the viewer is pinned over the
window instead, and `Esc` with nothing selected leaves it.

### Links to a view

The viewer keeps its state in the page's query string, so the address in the browser is a link
to the view as it is: the filters (`kind`, `domain`, `layer`, `violations`, `q` on the
architecture; `protocol`, `verdict`, `problems` on the landscape), the selection (`focus`),
`depth`, `dir`, `hide`, and `view=impact`. Only values that differ from the defaults are written,
and changing the view adds no browser history entry. On a node page a cleared selection is
written as `focus=`, so a reload does not select the page's node again.

## Information architecture

The portal (reshaped in BDL-046) leads with **About = the README as the landing
page** and a single ordered EN sidebar; there is **no top nav**. All of this is
emitted by `application/site/nav.py` into `.vitepress/config.generated.mjs`
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

`application/site/about.render_about()` turns the `README.md` into the `/` home
page (and `README.ru.md` into `/ru/`) through the
[project-text path](#project-text-on-the-portal): its links are rebased so they resolve on
the published site, and it is shown as written. The About page is plain Markdown (no
`layout: home` hero) so it reads like the README on a forge. If no README exists, `/` falls
back to the architecture overview.

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

## The portal for your project

`beadloom docs site` writes two kinds of file into the portal directory: the content it
generates from the graph on every run, and the **scaffold** the package ships — the theme and
the viewer, `package.json` with its lockfile, `.vitepress/config.mjs`, and the browser tests
under `e2e/`. One beadloom version means one theme: there is no separate npm package to keep in
step. The run says what it did with the scaffold:

```text
Scaffold (beadloom <version>): 209 written, 0 updated, 0 unchanged, 0 retired, 0 empty folders retired, 0 moved pages retired, 0 copied from .beadloom/site/
```

### The marker, upgrades and hand edits

Every scaffold file carries one marker line: the beadloom version that wrote it and a SHA-256
of the rest of the file — a comment in `.js`, `.mjs`, `.vue`, `.css` and `.svg`, a `"//"` key on
the second line of a `.json` file. The marker is how beadloom tells its own files from yours, so
each run does this:

| The file in the portal | What the run does |
|------------------------|-------------------|
| absent | writes it (`written`) |
| marker intact, same body and version | leaves it (`unchanged`) |
| marker intact, the installed beadloom ships another body or version | rewrites it (`updated`) — this is how an upgrade reaches the portal |
| no marker, or edited after beadloom wrote it | never overwrites it, and names it on stderr with the remedy (`kept`); the exit code stays 0 |
| marker intact, and the installed beadloom no longer ships it | removes it (`retired`), so a retired browser test does not keep running |
| a folder that the removed files leave empty | removes it too (`empty folders retired`), so a renamed slice leaves no empty tree; a folder you made, or one still holding anything, stays |
| a node page `docs site` wrote under a section the node's page has left | removes it (`moved pages retired`), so a portal an earlier version wrote does not keep `other/<ref>.md` beside `services/<ref>.md` for a node declared `kind: site`; a section it leaves empty is counted with the empty folders. A page is `docs site`'s by its opening (front matter with `title: <ref>` and a `kind:` line, then `# <ref>`); a page that opens otherwise, a path under `.beadloom/site/`, and the page of a node this run writes no page for all stay |

```text
Kept 1 file(s) under site that beadloom did not write or that were edited by hand; the shipped version was not written over them:
  - .vitepress/theme/app/index.js: was edited by hand after beadloom wrote it, so it was not replaced
    -> put your version in .beadloom/site/.vitepress/theme/app/index.js, which is copied last on every run, and delete site/.vitepress/theme/app/index.js; or delete it to take the shipped one
```

The scaffold is written without the graph annotations its source carries in this repository,
so nothing in a portal names a node of ours.

### Your own portal files

A file under `.beadloom/site/` is copied into the portal last, on every run, at the same path
relative to the portal root. A path it provides replaces the shipped file, which the scaffold
then does not write at all, and it is never upgraded by beadloom. Use it for a page, a
stylesheet or a component of your own; commit it with the project. A replaced shipped file is
yours to keep in step with later beadloom versions.

### What the portal reads from the project

- the graph and the index (run `beadloom reindex` first);
- `README.md`, `README.ru.md` and `docs/**`, as [project text](#project-text-on-the-portal);
- the [`site:` block](#configuration-reference-site) of `.beadloom/config.yml`, and the logo
  file `site.logo` names;
- the `origin` remote, only for the card's source links when no `site.repo_url` is declared,
  and for the [base warning](#the-base-path-and-github-pages). Nothing else from the remote is
  published.

## Project text on the portal

The project's own Markdown reaches three places: the README pair on the About pages, each
node's summary on its node page, and every document under `docs/`. VitePress compiles every page
as a Vue template, so text written for a forge can fail the build or render something else:
measured on the VitePress release the scaffold pins, a Helm value written in double braces failed
`vitepress build`, an arithmetic expression in double braces rendered as its result,
`List<String>` and an unclosed `<details>` failed the build, and a `<style>` restyled the whole
page. Every piece of project text therefore takes one path onto the
portal (`project_text.render_project_text`). It is read with markdown-it-py configured as
VitePress configures markdown-it, so code, links and raw HTML are found exactly where VitePress
finds them.

### Links

A relative link is resolved against the file it was written in, then:

| The target | On the portal |
|------------|---------------|
| a file the portal publishes: a document under `docs/`, `README.md`, `README.ru.md` | that file's page (`/docs/<slug>`, `/`, `/ru/`), the anchor kept |
| another file under `docs/` that the portal copies, such as an image | the copy, from where the page sits |
| a file under `docs/` the portal does not publish | the link's text |
| any other file in the repository (`LICENSE`, `src/…`) | the declared repository's page for it at the commit the site was generated from, by the forge's route (`<repo>/blob/<commit>/LICENSE` on GitHub, `<repo>/-/blob/<commit>/LICENSE` on GitLab); an image goes to the forge's raw route |
| the same, with no `site.repo_url` declared, no commit, or a host no forge is known for | the link's text (an image's alt text) |
| a path outside the repository (`../other/x`) | the link's text |
| an absolute address, `//host/x`, an anchor, an empty target | unchanged |

Reference definitions (`[label]: target`), images and the badge idiom `[![alt](img)](target)` are
rebased too. A raw HTML `href`, `src`, `srcset` or `poster` follows the same rule, written in full
under the base path, because VitePress does not rewrite raw HTML.

### Shown as written

The text is changed only where Vue would read it, and only so that the page shows what the
author wrote:

- Double braces in text show as written: an empty HTML comment is put between the two opening
  braces. A code span holding them becomes `<code v-pre>`; an indented code block holding them is wrapped in
  `<div v-pre>`. The content of a fenced code block and readable front matter are left alone,
  since VitePress already shows them as written.
- A link's text that VitePress writes from an address, an autolink `<https://…>` or a bare
  address it links, has its percent-escapes decoded, so `%7B%7B` would show double braces the
  source does not. Such a link is written as the Markdown link it renders,
  `[address](<address>)`, and its text then shows as written.
- A brace VitePress's attributes plugin (markdown-it-attrs) would read as the start of
  attributes — `{.class}` at the end of a paragraph or a heading, on a line of its own, right
  after a link, an emphasis or a code span — gets a backslash before it, so it shows as the
  brace and is not moved onto the element, where Vue would compile an attribute named `:x`,
  `@x` or `v-x`. A heading's own `{#id}` is shown too, not applied: a repeated id stops the
  build, and a forge does not apply it either. An image's alt text or a container's title that
  ends with such braces gets an empty HTML comment after it instead.
- A fenced block's language line, which VitePress writes into the page as it is, holds `<`,
  `"` and double braces as HTML entities.
- Front matter VitePress cannot parse (VitePress reads it with gray-matter and js-yaml 3; a key
  written twice is one example) would fail the build at the top of a page. The text then
  opens with a blank line, and the block shows as Markdown. Only YAML front matter is read;
  a block in another language shows as Markdown too.
- Raw HTML is kept only when it is the lowercase HTML a forge renders in a README (`<details>`,
  `<img>`, `<table>`, `<kbd>`, …) and its closing tag is inside the same block. Any other tag, an
  unclosed one, `<script>`, `<style>`, `<template>`, `<iframe>` and `<textarea>` show as text.
- An attribute only Vue gives meaning to (`@click`, `#slot`, `.prop`) is dropped, and a directive
  such as `v-if` or `:title` is shown rather than run.

**A Vue component written in a document shows as text.** `<Badge type="tip">` or a component of
your own in `docs/**` or in the README appears on the page as the markup you wrote, because the
portal cannot tell a component you meant from text that only looks like one. Put a page that
uses live components under [`.beadloom/site/`](#your-own-portal-files): it is copied as
written and compiled by VitePress like any page, so the components VitePress's default theme
registers work there. A component of your own also has to be registered in the theme entry,
`.vitepress/theme/index.js`, which you would then provide under `.beadloom/site/` too.

## Configuration reference: `site:`

The portal's identity is the `site:` block of `.beadloom/config.yml`. Every key is optional.

```yaml
site:
  title: Acme Orders
  description: Orders, payments and stock
  base: /orders/
  repo_url: https://github.com/acme/orders
  logo: docs/assets/orders-logo.svg
```

| Key | Default | What it sets | Refused when |
|-----|---------|--------------|--------------|
| `title` | the project directory's name | the site title in the nav bar and the browser tab | it is not a non-empty string |
| `description` | `The architecture of <title>: its graph, its documentation and its health` | the page description | it is not a non-empty string |
| `base` | `/` | the path the portal is served under; VitePress prefixes every link and asset with it | it does not start and end with `/`, or it holds a GitHub Actions expression opener (a workflow would evaluate it) |
| `repo_url` | none: no repository link | the repository link in the nav bar, the repository the card's source links and the project text's file links go to | it is not an `http` or `https` address with a host; it carries a user, a password, a query or a fragment, which the portal would publish; on a host whose forge is known, it stops before a repository (a host or an owner alone, an Azure DevOps project with no `_git/<repository>`) or runs past the repository into one of the forge's pages (`…/tree/main`, `…/pulls` on GitHub) |
| `forges` | none: only public forge hosts are recognised | the forge serving each host, below | see below |
| `repo_icon` | read from the host of `repo_url`, below | the icon beside the repository link in the nav bar | it is not one of `github`, `gitlab`, `bitbucket`, `codeberg`, `gitea`, `azuredevops`, `git` |
| `logo` | none: no logo in the nav bar | the project's logo in the nav bar, beside the title, and the portal's favicon: an SVG or a PNG named by its path relative to the project root, copied into the portal as `public/logo.svg` or `public/logo.png` | it is not a non-empty string; it is an absolute path; its suffix is not `.svg` or `.png`; it resolves outside the project root; no file is there |
| `powered_by` | `true` | the footer of every page, below | it is not `true` or `false` |

`repo_url` is stored in one spelling: the scheme and the host lower-cased, a trailing `/` and one
`.git` removed, the port and the case of the path kept. A key the block does not read is refused
by name, with the keys it does read. The project's name is never taken from the git remote.

On a host whose forge is known, `repo_url` is held to where that forge's repository address
ends. GitHub, Bitbucket Cloud, `codeberg.org` and `gitea.com` serve a repository at exactly
`/<owner>/<repository>`; on GitLab, a route word GitLab reserves (`-`, `tree`, `blob`, …) after
the group and the project is a page; Azure DevOps ends a repository at `_git/<repository>`. A
Gitea or GitLab host declared under `forges` may serve under a path, so it is not held to two
segments, and a forge declared by a template is not held to any shape. The refusal for an
address that stops too early names the shape the forge writes, such as `/<owner>/<repository>`.

**Where a refusal shows.** `beadloom docs site` stops before writing anything and exits 1;
`beadloom config-check` exits 1; the Gate's `config-check` step reports the rule `site-config`
and blocks. Each names the key (`site.base`, `site.forges[git.acme.example]`) and the remedy, and
never repeats a `repo_url` it refused, because it may hold a credential:

```text
Error: the `site:` block of .beadloom/config.yml cannot be used:
  - site.base: `site.base` is `orders`, and a base path starts and ends with `/`
    -> write `base:` as the path the portal is served under, e.g. `/orders/`
```

### The nav bar and the footer

The nav bar shows the project's own logo when `logo` names one, and nothing in its place when it
does not. An SVG logo drawn in `currentColor` is drawn in the colour of the title beside it, dark
on the light theme and light on the dark one, at 32 by 32 pixels: as an image it could not take
the page's colour and would be black on the dark theme. Every other logo is drawn as it is, in
its own colours and proportions, 32 pixels high as well, so every portal's nav bar holds its
logo at one height.

The favicon is the project's logo when it declares one of its own, the same file as it is, an
SVG or a PNG. Without one it is Beadloom's square icon, theme-adaptive: an SVG,
`public/brand/beadloom-favicon.svg`, whose `prefers-color-scheme` query draws the glyph dark
(`#3c3c43`) on a light browser and light (`#dfdfd6`) on a dark one, and two 32 by 32 pixel PNGs
for the browsers that take no SVG favicon, such as Safari. A PNG cannot adapt, so there is one
per scheme: `public/brand/beadloom-favicon.png` carries the dark glyph, and
`public/brand/beadloom-favicon-dark.png` the light glyph, linked behind the media query
`(prefers-color-scheme: dark)`.

A logo that is Beadloom's own icon, byte for byte, is not a logo of the project's own: it takes
Beadloom's favicon too, as this repository's portal does. The rule compares the file with the
square icon the installed package ships, byte for byte, so a copy of that icon gets the
theme-adaptive favicon where the icon as it is would draw a black square on a dark tab. The copy
`docs site` writes into a portal's `public/brand/` carries the generated marker and is not that
icon. A logo that differs by one byte is the project's own, and is its favicon as it is.

Without `repo_url` the nav bar has no repository link, and `beadloom config-check` says so on a
project that declares a `site:` block, without blocking:

```text
  ! site.repo_url: `site.repo_url` is not declared, so the portal's header has no repository link
    -> declare `repo_url:` under `site:` to link the repository from the header
```

The icon beside the repository link is read from the host of `repo_url`, and `repo_icon` names it
where the host says nothing, as a self-hosted instance's host often does:

| Host of `repo_url` | Icon |
|--------------------|------|
| `github.com` | `github` |
| `gitlab.com`, or a host whose first label is `gitlab` (`gitlab.acme.example`) | `gitlab` |
| `bitbucket.org` | `bitbucket` |
| `codeberg.org` | `codeberg` |
| `gitea.com`, or a host whose first label is `gitea` | `gitea` |
| a host declared under `forges` as a kind | that kind's icon (`azure` draws `azuredevops`) |
| `dev.azure.com`, `*.visualstudio.com` | `azuredevops` |
| any other host | `git` |

A declared `repo_icon` wins over every row; it takes one of `github`, `gitlab`, `bitbucket`,
`codeberg`, `gitea`, `azuredevops` and `git`. `azuredevops` names a self-hosted Azure DevOps
Server, whose host says nothing.

Every page ends with a footer about Beadloom rather than about the project. Its first line is
Beadloom's small icon and "Powered by Beadloom", without a link; its second line is "MIT" and a
link to Beadloom's repository drawn with the GitHub mark. `powered_by: false` removes the footer
whole. On a portal with a logo of its own, the footer is the one place Beadloom's icon appears.
The scaffold ships one brand file, `public/brand/beadloom-icon.svg`: the square icon that is
Beadloom's only mark, which the footer draws.

### `forges`: a self-hosted forge

A source link needs the forge's own route, and a guessed route is a 404 that looks like a link,
so a host is recognised only when it is a public forge's (`github.com`, `gitlab.com`,
`bitbucket.org`, `codeberg.org`, `gitea.com`, `dev.azure.com`, `*.visualstudio.com`) or when the
project declares it. `forges` maps a host name — no scheme, port or path — to one of:

- **a kind:** `github`, `gitlab`, `gitea`, `bitbucket` (Bitbucket Cloud's routes) or `azure`. The
  kind's routes are used for every repository on that host, over HTTPS or SSH, with or without a
  port.
- **templates:** `source:` (required), the page for a path, and `raw:` (optional), the file
  itself, for images. A template uses the placeholders `{url}` (the repository's web address),
  `{ref}` (the commit) and `{path}`, must contain `{path}`, and must yield an `http(s)` address
  with no credential. Without `raw:`, an image in project text becomes its alt text.

A self-hosted GitLab, with the repository under a subgroup:

```yaml
site:
  title: Ledger
  base: /ledger/
  repo_url: https://git.acme.example/finance/platform/ledger
  forges:
    git.acme.example: gitlab
```

A node's source then links to
`https://git.acme.example/finance/platform/ledger/-/tree/<commit>/<source>`, a README link to
`LICENSE` goes to `…/-/blob/<commit>/LICENSE`, and a README image comes from
`…/-/raw/<commit>/<image>`. A forge no kind describes, such as Bitbucket Data Center, is written
as templates:

```yaml
site:
  repo_url: https://bitbucket.acme.example/projects/FIN/repos/ledger
  forges:
    bitbucket.acme.example:
      source: "{url}/browse/{path}?at={ref}"
      raw: "{url}/raw/{path}?at={ref}"
```

The routes were written from the forms each forge publishes, not opened against a live forge;
the Azure DevOps `raw` route is the least certain. A refused entry is named by its host:

```text
  - site.forges[git.acme.example]: `site.forges[git.acme.example]` names `gitlabb`, which is not a forge kind; the kinds are `azure`, `bitbucket`, `gitea`, `github`, `gitlab`, or a mapping with a `source:` template
```

## Building and previewing

The portal needs `Node.js 22` or later (`engines.node: >=22` in the shipped `package.json`; an older
Node makes `npm ci` print an `EBADENGINE` warning). Every npm dependency is pinned exactly in the
shipped lockfile. The Python generator and the Mermaid guard stay fully
pytest-testable without Node.

```bash
# 1. Generate the content and the scaffold from the indexed graph (run `beadloom reindex` first).
beadloom docs site --out site

# 2. Install the portal's dependencies from the shipped lockfile, then build.
cd site && npm ci && npm run docs:build

# 3. Preview the built site locally.
npm run docs:preview          # or `npm run docs:dev` for a live-reload dev server
```

`npm run dev-check` starts the dev server, loads a page with a Mermaid diagram and the
architecture page in Chromium (after `npx playwright install chromium`), and fails on any page
error. The shipped config pre-bundles `mermaid` and the layout engine's worker for the dev server,
which a page with a diagram needs under `vitepress dev` (BDL-078).

`npm run lint:fsd` runs Steiger, Feature-Sliced Design's own linter, over `.vitepress/theme`
(BDL-080). The scaffold pins `steiger` and `@feature-sliced/steiger-plugin` exactly as
development dependencies and ships `steiger.config.js`: the plugin's `recommended` set with one
rule off, `fsd/insignificant-slice`, and the reason written beside the switch. The theme is cut
so that pieces of work touching disjoint slices can run in parallel, not for reuse, so a feature
that only the graph viewer uses is the intended shape. The pinned Steiger declares a later
Node.js release than the scaffold's own `engines` floor, and on an earlier one it still ran,
with an npm `EBADENGINE` warning (measured by BDL-080 S2a). It is
a style linter: `beadloom lint` judges the graph's slices and their imports, Steiger judges the
files, and `beadloom ci` names it under "Not run by this gate" when a pipeline runs it.

Everything under the portal directory is output: `beadloom init` ignores `/site/` in
`.gitignore` (see [Getting Started](../getting-started.md#what-init-writes)), and nothing there
needs committing. Your own portal files go under `.beadloom/site/`.

For the federated landscape diagram (Showcase B), feed a federation artifact:

```bash
beadloom federate service-a.json service-b.json   # writes .beadloom/federated.json
beadloom docs site --out site --federated .beadloom/federated.json
```

### The base path and GitHub Pages

GitHub serves a project repository's Pages site under `/<repo>/`, and a portal built for the
base `/` loads none of its assets there. When `site.base` is `/` and the `origin` remote is a
`github.com` project repository, `docs site` warns on stderr and exits 0:

```text
Warning: the portal is built for the base /, and GitHub Pages serves this project repository under /tidewater/, where the portal loads none of its assets. Set `site.base: /tidewater/` in .beadloom/config.yml, unless the site is served from a custom domain.
```

A `<owner>.github.io` repository, another host, no remote and a declared base other than `/` get
no warning. A project repository served from a custom domain is at `/` and is warned about all
the same, which the warning says.

### Deploy to GitHub Pages

`beadloom docs site --pages-workflow` writes `.github/workflows/beadloom-portal.yml` beside the
portal, and reports it:

```text
Pages workflow: .github/workflows/beadloom-portal.yml written (base /tidewater/, Node 22, portal site/, branch main)
```

The workflow does in CI what `docs site` did locally: it installs the same beadloom version with
`beadloom[languages]` on Python 3.12, checks the repository out with its whole history
(`fetch-depth: 0`, because node activity is measured on the history the clone holds), runs
`beadloom reindex` and `beadloom docs site --out <dir>`,
sets up the Node major the scaffold declares, runs `npm ci` and `npm run docs:build`, and deploys
`<dir>/.vitepress/dist` with `actions/upload-pages-artifact` and `actions/deploy-pages`.

- **Branch.** It runs on a push to the default branch git records for `origin` (`origin/HEAD`),
  and its build runs only when the ref is a branch and is the repository's default branch at run
  time, so a tag or a manual run on another branch deploys nothing. When git records no default
  branch the report ends `no branch`, every push starts a run that deploys only from the default
  branch, and stderr names the fix: `git remote set-head origin --auto`, then run the command
  again.
- **Base check.** A step fails the build when `site.base` differs from the path GitHub Pages
  reports for the repository, naming the base to set.
- **Permissions.** Nothing at the top (`permissions: {}`); `build`, which runs install scripts,
  only reads (`contents: read`, `pages: read`); `deploy` alone has `pages: write` and
  `id-token: write`. Every action is pinned by commit SHA, with its release in a comment.
- **Upgrades and edits.** The file carries the scaffold's marker: run the command again after
  upgrading beadloom or changing `site:` and an unedited workflow is rewritten; an edited one, or
  one beadloom did not write, is kept and reported with the remedy.
- `--out` must lie inside the project, or the command exits 1 before writing anything.

**One-time setup:** Settings → Pages → **Source = GitHub Actions**, then commit the workflow and
push to the default branch. Whether the build job's `pages: read` is enough for
`actions/configure-pages` has not been verified on GitHub yet. <!-- TODO: verify -->

This repository deploys its own portal with `.github/workflows/deploy-site.yml`, which runs the
same `docs site --out site`, `npm ci` and `npm run docs:build` on every push to `main` and is
served at `https://zoologov.github.io/beadloom/` under the base `/beadloom/` its `site:` block
declares. Mermaid click targets are raw strings VitePress does not rewrite, so
`DiagramViewer.vue` prepends the base at runtime; the generated Markdown stays base-agnostic.

## Browser tests in the portal

The scaffold ships the viewer's Playwright suite under `e2e/`, so any portal can run it:

```bash
cd site
npx playwright install chromium
npm run test:e2e
```

`e2e/support/serve.mjs` builds the portal and serves the build, so the suite tests the bundle
that deploys, under the base the `site:` block declares (`BEADLOOM_E2E_BASE` overrides it). It
refuses to start before `beadloom docs site` has written the content.

The cases that time the viewer run last, one at a time, in a Playwright project of their own
(`performance`), and only when every other case has passed, because a case timed beside other
browsers would time them too. Their bounds depend on where the suite runs: `ci` when the `CI`
variable is set, `local` otherwise. The `local` bounds were measured on an Apple M1 Max. On a
slower machine, set `BEADLOOM_E2E_ENVIRONMENT=ci` for the wider bounds. To run only them:

```bash
npx playwright test -c e2e --project performance --no-deps
```

A correct portal can lack what a case is written about: a project with no layer rule has no
layers to colour, and a single project's landscape has no contract to walk. Such a case is
skipped, and the report names the missing shape:

```text
this portal's graph lacks what the case needs: fewer than two declared layers; a project declares its layers with a layer rule in .beadloom/_graph/rules.yml
```

With `BEADLOOM_E2E_NO_SKIP=1` a missing shape fails the case instead. Set it for a portal that is
meant to hold every shape, so a change that would quietly turn a check into a skip is reported
as a failure; this repository's `site-e2e` job does. Measured on six small projects, one per
stack (`tests/fixtures/site/`, macOS, `Node.js 22`), when the shape skips were introduced in
BDL-076, all 101 cases of that suite ran or skipped by shape and none failed: between 7 and 27
cases skipped, the most on the projects with no declared layers. The suite has grown to 182 cases
since, and in BDL-077 it passed on each of the six (`beadloom-m6k7.5`, macOS).

## Determinism

Identical graph, commit and run instant → byte-identical tree: pages are sorted,
frontmatter is stable, and the published-doc badge uses the stored
`sync_state.synced_at`, not "now"; the dashboard's `dashboard.data.json` —
including `trends` and `recommendations` — the data files and the generated
Mermaid are sorted and byte-stable. The run's instant (`now_ts`) is the only
wall-clock read. It lands in the metrics-history point appended to
`.beadloom/metrics_history.json` and in the `generated_at` field of
`architecture.data.json`, and in no dashboard field. Each node's `source_url`
names the commit the site was generated from. This makes a rebuilt site
reproducible and the generated tree diffable in review.

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
- **Shipped since (F4.1, BDL-047 onward):** the AI tech-writer in CI —
  orchestrating an *external* model to refresh drifted docs, scoped by
  `sync-check --since` and symbol-level narrowing, with team review on the PR it
  commits into. It is not part of this generator: the published-docs showcase
  still does **not** rewrite prose, and the badges are computed rather than
  generated. See the [AI tech-writer guide](./ai-techwriter.md).
- **The architecture viewer (BDL-076, slice 1):** one Cytoscape and ELK viewer for
  the architecture and the landscape, with the neighbourhood, impact on both, the
  architecture and service cards, node pages opened on their node, full screen and
  URL state, and Playwright browser tests in the advisory `site-e2e` CI job. It
  replaced the Mermaid-only landscape and the per-node Mermaid diagrams; the
  landscape diagram and the top-level C4 diagram stay as fallbacks on
  `landscape-diagram.md` and `architecture-diagram.md`.
- **The portal for adopters (BDL-076, slice 2):** the scaffold ships in the package and
  `docs site` writes it under the marker rules; the `site:` block with a self-hosted forge
  declared per host; `docs site --pages-workflow`; `init` ignoring `/site/`; project text read
  as VitePress reads it and shown as written; the browser suite runnable on any portal. Measured
  on one small project per claimed stack (`tests/fixtures/site/`), built by the
  `site-adopters` workflow.
- **Edges like a classic diagram (BDL-077):** ELK's right-angled routes around every box,
  computed in a Web Worker; trunks, buses and junction dots for busy nodes; the overview as a map
  of top-level boxes and aggregated lines that opens as you zoom in; bridges on highlighted
  edges; Arrange removed.
- **The viewer looks finished (BDL-078):** one thin line weight, arrowheads one size on screen, one
  head per shared last run, rounded merges; bridges, junction dots and the colour gradient
  removed, a followed line drawn on top over a casing instead; nodes as cards with a corner status
  mark; the overview routed on its own and calm by default, counts on pills; open boxes keeping
  their outward edges on their own lines with a "+N" per node; boxes opening when their nodes are
  readable; a selection framed; activity by changed lines with levels relative to the project.
- **Deferred:** REST/OpenAPI + gRPC contracts in the federated map.

See the [`beadloom docs site` CLI reference](../services/cli.md#beadloom-docs-site),
the [application domain README](../domains/application/README.md) for the
generator modules, and the [federation SPEC](../domains/graph/features/federation/SPEC.md)
for the contract graph the landscape map renders.
