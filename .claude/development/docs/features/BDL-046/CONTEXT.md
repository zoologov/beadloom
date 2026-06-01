# CONTEXT: BDL-046 — VitePress portal: navigation + bilingual About

> **Status:** Done
> **Created:** 2026-06-02
> **PRD:** ./PRD.md · **RFC:** ./RFC.md

---

## State

- **Phase:** planning → dev
- **Builds on:** F4 (`docs site` generator) + F4.4 (Mermaid guard, part_of/docs sidebar trees, DiagramViewer) + BDL-043 (`public/` data copy) + BDL-045 (rewritten EN+RU README — the bilingual About source).
- **Deploy:** existing `.github/workflows/deploy-site.yml` (Pages, project page `/beadloom/`) — unchanged.

## Key decisions (from PRD/RFC)

- **About = README**, generated (no hand-maintained duplicate). EN root `/`; RU `/ru/`.
- **Bilingual = About only** (Q2 = curated). VitePress `locales`; default-theme locale switcher is the language toggle. Rest of portal stays EN.
- **Architecture overview** moves off the landing → `/architecture` (inside the Architecture group).
- **Top nav removed** (`nav = []`); theme toggle + search + locale switch are rendered by the default theme regardless.
- **Menu order (exact):** About · Getting Started · Dashboard (flat) · Architecture (collapsed) · Landscape map (flat) · Documentation (expanded, Overview-led).
- **Link rebasing** in `render_about`: published doc → `/docs/<slug>`; README cross-links dropped; unknown internal → absolute GitHub URL; external/badges untouched.
- Generator output stays **pure + deterministic + link-safe** (only emits links to existing pages) — the F4/F4.4 invariant.

## Standards (from CLAUDE.md §0.1)

- Python 3.10+, SQLite, Click, Rich, tree-sitter.
- Tests: pytest + pytest-cov (coverage ≥ 80% on new code). TDD.
- ruff (lint + format); mypy --strict. No `Any`/`# type: ignore` without reason; no bare `except`; no mutable default args; no `print()`/`breakpoint()`.
- Gates before commit: `uv run pytest`, `ruff check`, `mypy src/`, then `beadloom reindex && sync-check && lint --strict && doctor`.
- Commit format: `[BDL-046] <type>: <desc>`.

## Files in play

- `src/beadloom/application/site_about.py` — **NEW** (README→About transform + link rebasing).
- `src/beadloom/application/site_nav.py` — ordered `render_sidebar()`, flatten Dashboard/Landscape, About/Getting-Started entries, `/architecture` link, Documentation overview + `collapsed:false`, empty `render_nav()`, RU sidebar.
- `src/beadloom/application/site.py` — About home (EN `/index.md`, RU `/ru/index.md`), arch overview → `/architecture.md`, docs overview `/docs/index.md`, emit `navRu`/`sidebarRu`.
- `site/.vitepress/config.mjs` — `locales` block + import `navRu`/`sidebarRu`.
- Tests: `tests/` mirrors (test_site_about, test_site_nav, test_site).
- Docs: VitePress guide, CHANGELOG, STRATEGY note (tech-writer).

## Constraints

- The Python generator MUST stay fully unit-testable without Node; `config.mjs` + locales verified by the dogfood build only.
- Dogfood (G6) hits the **deployed/built** site, not just `docs:dev` (the recurring "build green ≠ renders ok" lesson).
- Anonymization: no private dogfood project names in any committed artifact (working tree + history).

## Blockers

- None.

## UX dogfooding

- Log friction in `.claude/development/BDL-UX-Issues.md` (running total currently 121).
