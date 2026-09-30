# CONTEXT: BDL-076 — The architecture graph viewer, made a working tool for the team and for adopters

> **Status:** Approved
> **Created:** 2026-09-30
> **Last updated:** 2026-09-30

---

## Goal

Give the team a graph viewer they can work in, and give adopters the same viewer. The viewer must:

- pan without dragging;
- draw readable, directional edges;
- filter without breaking nesting;
- show a node's neighbourhood with depth and direction;
- offer an impact mode for estimates;
- show a full node card;
- keep its toolbar in its own space, in the page and in full screen;
- open node pages focused on their node.

Adopters on every stack we claim get it from `beadloom docs site` alone. Browser tests hold all of
it.

## Key Constraints

- **Keep VitePress 1.6.4, Cytoscape.js 3.34.1 and cytoscape-elk/ELK 0.12.** Every measured defect is
  configuration. The exact npm lock stays exact; `web-worker` is the one existing range.
- **Cytoscape takes literal colours only.** Theme colours are resolved at runtime from the CSS
  variables and rebuilt on a theme switch. No `var(...)` reaches a Cytoscape style.
- **The site is static.** Everything the card and the impact mode show is computed by
  `beadloom docs site` into the data file. The browser never queries the index.
- **The data file is a contract.** Its schema version is 2, and every key of version 1 is kept.
  Python tests pin the keys. The viewer refuses an unknown version with a visible message.
- **Impact mode is the graph's view** and says so in the UI. Code-level impact is `beadloom-ikj6`.
- **No project name, base path, repository or layer vocabulary is hard-coded** in anything that
  ships. This is slice 2's rule, and slice 1 must not add new instances.
- **The viewer is JavaScript, and `beadloom impact` cannot see it.** Every bead names its `.vue`/`.js`
  files explicitly, and review covers them.
- **Browser tests assert state, not pixels.** They use the read-only test handle
  `window.__beadloomViewer`. The `site-e2e` job stays non-required until it has run clean on ten
  pull requests.
- **The owner looks at the viewer in a browser before each slice's merge.**
- **Language rule for anything Russian:** grammatically correct, easy to read, clear and concise,
  with no abbreviations, no terms the reader must translate, and no AI-writing patterns.
- **Commits and suites.** Commit only your own files, by explicit path, under
  `bd merge-slot acquire/release --holder <bead-id>`. Subagents run long suites in the foreground.
  Never pipe a command whose exit code is the answer.

## Code Standards

### Language and Environment

- **Language:** Python 3.10+ (type hints, `str | None` syntax) for the generator. JavaScript (ES
  modules) and Vue 3 SFCs for the viewer; no TypeScript unless the RFC is amended.
- **Frontend architecture:** Feature-Sliced Design (owner, 2026-09-30). Layers from top to bottom:
  `app`, `pages`, `widgets`, `features`, `entities`, `shared`. A layer imports only layers below it,
  and a slice is used only through its public `index.js`.
- **Package manager:** uv (Python), npm with the committed lockfile (the site).
- **Architecture:** DDD packages: `ai_agents/`, `application/`, `context_oracle/`, `doc_sync/`,
  `graph/`, `infrastructure/`, `onboarding/`, `services/`, `tui/`.

### Methodologies

| Methodology | Application |
|---|---|
| TDD | Python: test-first for the data file and the pages. Viewer: each behaviour lands with its Playwright case seen failing first. |
| Clean Code | SRP, DRY, KISS. The viewer core is split into composables by concern: style, filters, selection, URL state. |
| Architecture | `services -> application -> domains -> infrastructure`; the viewer reads only the data file. |

### Testing

- **Python:** pytest + pytest-cov, with coverage of at least 80% on changed modules.
- **Browser:** Playwright against `vitepress build` served by `vitepress preview`, run on Chromium.
- **Fixtures that are not this repository:** the adopter fixtures for every claimed stack in slice 2.

### Code Quality

- **Linter:** ruff: `uv run ruff check src/ tests/`
- **Typing:** mypy --strict: `uv run mypy src/`
- **Site:** `npm run docs:build` passes, and the browser tests pass.
- **Gate:** `beadloom ci` rc 0.

### Restrictions

- No `Any` or `# type: ignore` without a stated reason. No `print()`/`breakpoint()`. No bare
  `except:`. Use pathlib, SQL parameters `?` and `safe_load`.
- No `console.log` left in the viewer. Use no global state beyond the documented test handle.

## Architectural Decisions

| Date | Decision | Reason |
|---|---|---|
| 2026-09-29 | The viewer is P0, ahead of `beadloom-jwfc` | Owner: the team's request; the graph is the foundation. |
| 2026-09-29 | Node pages embed the main viewer focused on their node | Owner. |
| 2026-09-29 | The toolbar lives inside the viewer's own space | Owner: one UI in the page and in full screen. |
| 2026-09-30 | The theme ships in the wheel, and `docs site` writes the scaffold | Owner: one version, no npm channel. |
| 2026-09-30 | Playwright in CI | Owner. |
| 2026-09-30 | One viewer core for architecture and landscape | Owner. |
| 2026-09-30 | Two slices: the viewer for the team, then the portal for adopters | Owner. |
| 2026-09-30 | An impact mode, by the graph, in slice 1; code-level impact deferred to `beadloom-ikj6` | Owner. |
| 2026-09-30 | This repository's site comes under its own beadloom first (A0): one graph, the viewer's nodes, docs and bound tests; `.vue` support measured first | Owner: the viewer is today a blind spot of the tool, and our own JS is the honest first test of the JS/TS claim. |
| 2026-09-30 | The three JS/TS/Vue fixes (`beadloom-hjr1`, `beadloom-g9fb`, `beadloom-tmxa`) join BDL-076 before the viewer work | Owner, after A0 step 1: an adopter's JS/TS graph would show as unconnected nodes, and our site cannot join the graph without them. |
| 2026-09-30 | Frontend code follows Feature-Sliced Design | Owner. The viewer and the rest of the theme are laid out by FSD layers: `app` (the VitePress theme entry), `pages`, `widgets`, `features`, `entities`, `shared`. Each layer holds slices with `ui`/`model`/`lib` segments and a public API per slice. The site's graph nodes (A0 step 2) follow the slices, and the FSD import direction is declared as a layer rule, so beadloom checks our own frontend the way it checks an FSD adopter. |
| 2026-09-30 | The portal's Python modules move into `application/site/`, owned by `site-generation`, instead of raising the domain-size limit | Owner, after A1 took `application` to 183 of 180 symbols. |
| 2026-09-30 | `beadloom-oo4m` and `beadloom-5o48` join the epic; `doc-area-coherence` returns to error before PR 1 | Owner: the same class as J1–J3 — the tool not yet ready for a project with more than Python; no slice ships with a weakened check. |
| 2026-09-30 | Keep VitePress and Cytoscape | RFC: every defect was measured as configuration. |
| 2026-09-30 | Edge curve style `bezier` (A2) | Measured on this repository's graph over every drawn edge: 15.7% of an edge's middle lies within 4 layout units of another edge under `bezier`, against 40.7% under vertical `taxi` and 25.1% with `taxi` inside a lane; 22 edges more than half shared against 119 and 73. `taxi` runs every edge out of a node down one trunk, so edges become indistinguishable there. |
| 2026-09-30 | Each site slice is a `component` carrying its own `fsd-<layer>` tag; no node per layer (A2) | A tagged layer container would be shared by every slice inside it, and the layer rule reads two ends that share a tagged container as internal, so two widgets importing each other would pass. With the tag on the slice, a same-layer import is a crossing, which is FSD's own rule. `domain` and `feature` carry Python-package rules (`domain-needs-parent`, scenario coverage) that do not fit a frontend slice. `app` and `shared` are one node each because FSD gives them segments, not slices. |
| 2026-09-30 | `doc-area-coherence` at `warn` until `beadloom-5o48` (A2) | Seventeen sources under `site/` make a second supported source tree; the rule's root derivation then comes out empty and it checks none of 126 pairs, and no setting avoids it. At `warn` the "checked nothing" line still prints on every run; what is lost until the fix is that a misplaced document under `src/` no longer fails the Gate. |

## Related Files

Discover them with `beadloom ctx site-generation`, `beadloom ctx application` and `axes.md`
Supplement A. The viewer's files are not in the index's code tables.

## Current Phase

- **Phase:** Planning
- **Current bead:** none. Beads are created after PLAN is approved.
- **Blockers:** none
