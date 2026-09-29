# PRD: BDL-076 — The architecture graph viewer, made a working tool for the team and for adopters

> **Status:** Approved
> **Created:** 2026-09-30

---

## Problem

The architecture graph is the product's foundation, and the team working with it has asked for a
viewer they can actually use. Today's viewer on the VitePress portal (`architecture.html`) fails at
each basic task. Explore measured every failure (`axes.md`, Supplement B):

- **Panning drags a node.** Every node is grabbable, compound parents included. A domain or service
  box covers its children's area, so a pointer-down almost anywhere inside it grabs the box
  (`ArchitectureMap.vue:140-146`; Cytoscape defaults at the locked 3.34.1).
- **Edges are unreadable.** Every colour in the viewer's theme is written as `var(--vp-…)`, which
  Cytoscape rejects, so it resolves each one to `rgb(153,153,153)`. That covers the base edges, the
  runtime edges and the highlight of a focused node's edges (`architectureTheme.js:103-187`). Only
  two edge kinds of the six are drawn (`depends_on`, `uses`), and the legend lists a `part_of` line
  style the viewer never draws.
- **Filters break nesting.** Hiding a compound parent hides its children, so `Kind = feature` hides
  every feature that sits inside a domain. The domain filter keeps direct children only. Focus is
  depth 1, both directions, with no control over either (`ArchitectureMap.vue:184-218`).
- **Full screen is partial.** Only the canvas and the card go full screen. The controls and the
  legend stay outside (`:222-239`, `:274-329`).
- **The node card is thin.** The data file carries no `source`, no bound tests, no activity, no
  debt, no names of public symbols, and no per-pair doc freshness. Rule findings are reduced to a
  single boolean (`site.py:166-180`). 47 components and one site node have no page link
  (`site_landscape.py:228-246`).
- **Node pages show a separate Mermaid mini-diagram** (`site_pages.py:267-297`), unrelated to the
  viewer, with its own pan-zoom and its own gaps (`DiagramViewer.vue`).
- **Adopters have no portal at all.** `beadloom docs site` writes content only. The theme, the
  viewer components, `package.json` and the VitePress config exist in this repository alone, and
  the wheel ships none of them. Explore built a TypeScript project's portal only by copying this
  repository's files by hand, and the result carried Beadloom's title, the `/beadloom/` base and a
  link to `zoologov/beadloom`. The layer palette is keyed to this project's four layer names; any
  other project's layers render grey. The dashboard always mounts the ai-techwriter panel.
- **No test executes the viewer.** CI proves that the bundle builds, and nothing about interaction.

The landscape viewer (`LandscapeMap.vue`) is built the same way and shares the same defects.

## Impact

The team: the graph is where they reason about the architecture, and today they cannot pan it,
read its edges, isolate a node's neighbourhood or see what a node is. Adopters: the portal the
README and the guides describe cannot be built on their project without copying our files, and
when copied it names our project.

## Goals

- [ ] **One viewer core** serves the architecture map and the landscape map as two modes. It
      provides one toolbar, one navigation model, one full-screen mode and one node card.
- [ ] **Navigation.** Dragging the canvas pans; it never moves the node under the cursor. Moving a
      node, if kept at all, is a distinct and deliberate gesture. Zoom and fit work with mouse,
      trackpad and keyboard.
- [ ] **Readable edges.** Direction reads at a glance. Each edge kind (`depends_on`, `uses`, and the
      others the data carries) is drawn distinctly, and the legend matches what is drawn.
      Violations stand out. Every colour resolves to a real value in light and in dark themes.
- [ ] **Filters that work.** Kind, domain, layer and violations filter without hiding what nests
      inside a hidden parent. Filter state can be shared through the URL.
- [ ] **A selected node's neighbourhood.**
  - Selecting a node shows only its edges and the nodes at the chosen **depth**.
  - The **direction** can be incoming, outgoing or both. Everything else is hidden or dimmed so
    that the neighbourhood is plain to see.
  - Depth and direction are toolbar controls.
- [ ] **An impact mode for estimates** (owner, 2026-09-30, added after approving the PRD). Selecting a
      node in impact mode shows every node that depends on it, transitively and without the depth
      limit. Distance rings group them: direct dependents, then the second level, and so on.
  - The card summarises the affected nodes: how many, which domains and services, and which layer
    boundaries they cross.
  - Each affected node is marked for risk: no bound tests, stale docs, open rule findings.
  - The card offers `beadloom why <ref>` and `beadloom impact <source>` to copy, for the code-level
    answer.
  - The mode states in the UI that it is the graph's view (edges from imports and declarations),
    not a reading of the code. Precomputed code-level `impact` in the viewer is a separate item.
- [ ] **The toolbar lives inside the viewer's own space**, never in the page around it, so the
      embedded view and full screen are one UI. Full screen carries every tool and the node card.
- [ ] **A detailed node card** in a side panel:
  - identity: kind, summary, lifecycle, tags;
  - layer: the node's own and the inherited one;
  - `source`, linked to the repository;
  - docs, each with its freshness;
  - bound tests: files, count and placement;
  - public symbols;
  - incoming and outgoing edges by kind, each clickable to move the selection;
  - rule findings, with the rule name and the message;
  - activity (commits in the last 30 days);
  - debt contribution;
  - links to the node's page, and a copyable `beadloom ctx <ref>`.
- [ ] **Node pages** show the main viewer focused on the page's node, with the neighbourhood
      selected and free navigation from there. This replaces the Mermaid mini-diagram.
- [ ] **Adopters get the portal** from `beadloom docs site`. The command writes the theme, the
      viewer, `package.json` (Node version declared) and the VitePress config from the installed
      package, with the title, base path and repository link taken from the project, and layers
      coloured from the project's declared layers. It works on every stack we claim — Python, Go,
      JS/TS, Java, Kotlin, Swift — proven on projects that are not this repository. This repository
      builds its own portal through the same path; no private copy remains. A GitHub Pages
      workflow is scaffolded on request.
- [ ] **Browser tests** drive the built portal in a real browser (Playwright) and cover:
  - panning does not move a node;
  - filters;
  - neighbourhood depth and direction;
  - full screen with the toolbar and card;
  - focus from a node page;
  - edge colours resolving.

  They run in CI, first as a non-required job, over this repository and over adopter fixtures.

## Delivery

Two slices, each its own pull request:

- **Slice 1 — the viewer the team uses.** The shared core, navigation, edges, filters, the
  neighbourhood with depth and direction, the in-viewer toolbar, full screen, the node card and the
  data it needs, node pages focused on their node, and the browser tests. Built on this
  repository's portal.
- **Slice 2 — the portal for adopters.** The theme and scaffold ship in the wheel;
  `beadloom docs site` writes them with the project's own identity and layers; nothing
  repository-specific leaks; the Pages workflow on request; proven on fixtures for every claimed
  stack, with the browser tests run on them.

## Non-goals

- **Editing the graph in the browser.** The viewer reads the graph; the YAML stays the source.
- **A separate npm package** for the theme (owner, 2026-09-30: the theme ships in the wheel).
- **Federation's live cross-repo view.** Federation is deferred; the landscape mode keeps what it
  shows today, with the shared core's fixes.
- **Replacing VitePress or Cytoscape** unless the RFC shows a requirement cannot be met with them.

## User Stories

### US-1: An engineer isolates what a node depends on
**As** an engineer on the team, **I want** to select a node and see only what it depends on, two
levels deep, **so that** I can judge the blast radius of a change without reading the whole graph.

**Acceptance criteria:**
- [ ] Given the architecture page, when I select `rule-engine`, choose depth 2 and direction
      "outgoing", then only `rule-engine`, the nodes it reaches within two `depends_on`/`uses`
      edges and those edges are shown, and the rest is hidden or dimmed.
- [ ] Given a selected node, when I switch direction to "incoming", then the shown set changes to
      the nodes that reach it.

### US-2: An engineer pans without breaking the layout
**As** an engineer, **I want** dragging to pan the canvas, **so that** I can move around a large
graph without dragging nodes out of place.

**Acceptance criteria:**
- [ ] Given the architecture map, when I press inside a domain box and drag, then the viewport moves
      and no node's position changes.

### US-3: An engineer reads a node from its card
**As** an engineer, **I want** the selected node's card to tell me its kind, layer, source, docs
and their freshness, tests, symbols, edges, findings, activity and debt, **so that** I do not have to
leave the graph to learn what a node is.

**Acceptance criteria:**
- [ ] Given a selected node, then the card shows every field in the goal list that the index holds
      for that node, and says "none" where it holds nothing.
- [ ] Given the card, when I click an edge's target, then that node becomes the selection.

### US-6: An architect estimates a change's reach
**As** an architect estimating a change to `rule-engine`, **I want** to see everything that depends
on it and where the risk is, **so that** the estimate names the affected domains and the weak spots
before the work starts.

**Acceptance criteria:**
- [ ] Given impact mode on `rule-engine`, then every node that reaches it through `depends_on`/`uses`
      is shown, grouped by distance. The card gives their count, their domains and services, and the
      layer boundaries crossed.
- [ ] Given an affected node with no bound tests, stale docs or an open finding, then it carries a
      risk mark, and the card lists it.
- [ ] Given impact mode, then the UI says the result is the graph's view and offers the two terminal
      commands.

### US-4: A reader lands on a node page and explores from there
**As** a reader of `features/ai-techwriter`, **I want** the page's graph to open on that node, **so
that** I see its place in the architecture and can walk away from it.

**Acceptance criteria:**
- [ ] Given a node page, then the viewer opens with that node selected and its neighbourhood shown,
      and every toolbar control works as on the architecture page.

### US-5: An adopter builds the portal for their own project
**As** a team on a Go (or Java, Kotlin, Swift, JS/TS, Python) project, **I want**
`beadloom docs site` to give me a portal I can build and deploy, **so that** my team gets the same
viewer without copying Beadloom's repository.

**Acceptance criteria:**
- [ ] Given a fixture project of each claimed stack, when `beadloom docs site` runs and the portal is
      built with the declared Node version, then the build succeeds, and its pages carry the
      project's title, base path and repository link and none of Beadloom's.
- [ ] Given that built portal, then the browser tests pass on it.

## Acceptance Criteria (overall)

- [ ] Browser tests pass in CI on this repository's portal and on the adopter fixtures, covering
      each behaviour in the goals.
- [ ] No colour in the viewer's style resolves to Cytoscape's fallback. A test asserts this.
- [ ] The wheel carries the portal scaffold, and a project that is not this repository builds its
      portal from `beadloom docs site` alone.
- [ ] `beadloom ci` rc 0 and the nine required checks green on each slice's pull request.
- [ ] The owner has looked at the viewer in a browser before each merge.
