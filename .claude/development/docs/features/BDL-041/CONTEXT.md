# CONTEXT: BDL-041 — F4.4: Site rendering fixes + dashboard UX

> **Status:** Approved
> **Created:** 2026-06-02
> **Last updated:** 2026-06-02

---

## Goal

Fix the two F4 generator bugs that make the VitePress diagrams render broken, add a generation-time Mermaid validity guard (so broken diagrams fail pytest, not the browser), make diagrams pan/zoom/fullscreen, and turn the dashboard into a real ECharts dashboard (gauges + charts + honest trends + a prioritized recommendations panel) — Approach C (Beadloom emits deterministic `dashboard.data.json`; committed Vue widgets render it). Dogfooded by re-rendering Beadloom's own site with zero diagram/console errors. (Immutable after approval.)

## Key Constraints

- **Build green ≠ renders ok — close the gap.** A generation-time structural Mermaid guard rejects the F4 bug classes in pytest (no browser/node); the dogfood MUST additionally validate the real render (not just `npm run docs:build` exit 0). No green build may hide a broken page again.
- **Beadloom produces, VitePress renders.** Python emits deterministic data + Mermaid; Vue/ECharts components render client-side. Data stays honest-by-construction — dashboard numbers + recommendations come from the EXACT gate code paths (`lint`/`debt_report`/`doctor`/`sync-check`/`federate`); no front-end-invented figures.
- **Honest trends.** Time-series come only from real recorded history (`metrics_history` append-log + existing `graph_snapshots`); sparse at first, grows per build; NO interpolation/fabricated points; timestamps from stored values, not `now()`.
- **Determinism.** `dashboard.data.json` (incl. trends/recommendations) + generated Mermaid are sorted + byte-stable; injected timestamps in tests.
- **C4 Rel-drop is safe, not lossy.** Only drop a `Rel` whose endpoint genuinely isn't a declared diagram node (the System root); the relationship still lives in the graph + the landscape map; count/log dropped Rels.
- **Pinned frontend.** `site/package.json` pins exact `echarts` / `vue-echarts` / `svg-pan-zoom`; the custom theme is committed. The Python generator + guard stay fully pytest-testable without node.
- **No schema bump.** `metrics_history` is additive append-state (JSON file or small additive table), not a versioned artifact.
- **F4 + F4.4 ship together** — F4 push stays paused until the render is fixed (a published broken diagram = a published lie).
- Follow-up to BDL-040 (F4); the AI-tech-writer F4.1 remains a separate deferred epic.

## Code Standards

(from CLAUDE.md §0.1)

| Standard | Application |
|----------|-------------|
| Language/env | Python 3.10+ (`str \| None`), uv; frontend = pinned npm deps |
| TDD | Red → Green → Refactor |
| Linter/format | ruff (Python) |
| Typing | mypy --strict (Python) |
| Tests | pytest + pytest-cov, coverage ≥ 80% (Python surface) |

**Restrictions:** no `Any`/`# type: ignore` without reason; `pathlib`; parameterized SQL; `yaml.safe_load`; no bare `except:`; deterministic serialization (sorted, stable). Vue components small + pinned; no secrets.

**Commit format:** `[BDL-041] <type>: <description>`.

## Architectural Decisions

| Date | Decision | Reason |
|------|----------|--------|
| 2026-06-02 | Landscape `_mermaid_id` prefixes ids (`n_…`) | charset sanitization alone didn't stop the reserved-keyword collision (`graph`); a prefix guarantees no keyword clash |
| 2026-06-02 | C4 emits `Rel()` only between declared diagram nodes | the `drawRels` crash was a Rel to the undeclared `System` root; dropping such Rels is safe (relationship stays in graph + landscape) |
| 2026-06-02 | Generation-time guard = targeted structural validators (not a full Mermaid parser) | covers the specific bug classes (reserved-id, C4 Rel integrity), extensible, deterministic, pytest-able without node; `mmdc` smoke optional 2nd net |
| 2026-06-02 | Dashboard = Approach C (deterministic `dashboard.data.json` + committed Vue/ECharts widgets) | data honest+deterministic, render interactive+beautiful |
| 2026-06-02 | Chart lib = ECharts (`vue-echarts`) | richer for a real dashboard (gauges/trends/themes), good Vue integration — best quality/beauty/efficiency balance |
| 2026-06-02 | Trends from a `metrics_history` append-log + existing `graph_snapshots` | real history, honest sparse-start, no fabrication |
| 2026-06-02 | Recommendations from existing gate data | actionable + honest by construction |
| 2026-06-02 | Dogfood must validate the real render, not just `build` exit 0 | closes the F4 "build green ≠ renders ok" gap |

## Related Files

(discover via `beadloom ctx`/`why` — never hardcode)
- `src/beadloom/application/site_landscape.py` (`_mermaid_id` reserved-word fix)
- `src/beadloom/graph/c4.py` (C4 `Rel()` integrity)
- NEW `src/beadloom/application/site_mermaid_guard.py` (`validate_mermaid`)
- `src/beadloom/application/site_dashboard.py` (trends + recommendations into data.json)
- NEW `src/beadloom/application/site_metrics_history.py` (trend history append/read)
- `src/beadloom/application/site.py` (wire guard; mount widgets in `dashboard.md`)
- NEW `site/.vitepress/theme/index.js` + `site/.vitepress/theme/components/*.vue` (`DiagramViewer`, `HealthGauges`, `CategoryChart`, `TrendCharts`, `Recommendations`)
- `site/package.json` (pinned `echarts` / `vue-echarts` / `svg-pan-zoom`)
- `.beadloom/metrics_history.json` (or a small additive table — trend history store)
- `docs/guides/vitepress-site.md`, `CHANGELOG.md`, `.claude/development/STRATEGY-3.md`, `BDL-UX-Issues.md`

## Current Phase

- **Phase:** Planning
- **Current bead:** (none yet — created after PLAN approval)
- **Blockers:** none
