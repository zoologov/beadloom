# CONTEXT: BDL-059 — Code-health debt paydown (cohesion-driven)

> **Status:** Approved
> **Created:** 2026-06-15
> **Type:** epic
> **PRD:** ./PRD.md · **RFC:** ./RFC.md

---

## State

- `main` at 2.1.0 (BDL-058 merged). Branch not yet created (epic runs per-slice on `features/BDL-059-sN` branches off `main`, one PR per slice).
- The 8 debt items (#122–#129, scoped) verified open at HEAD by the BDL-059 structural survey.
- Monster modules confirmed: `graph/rule_engine.py` 2249, `onboarding/scanner.py` ~2500, `application/reindex.py` 1371, `application/debt_report.py` 1109, `graph/federation.py` 1000, `graph/import_resolver.py` 929, `application/site_dashboard.py` 845, `services/cli.py` (all-commands monolith). Layering inversion: `graph/linter.py` + `graph/import_resolver.py` import `application.reindex`.
- Cohesive-at-size (NOT to be split): `contracts.py` 402, `loader.py` 457, `c4.py` 662, `diff.py`, `snapshot.py`, `linter.py`.

## Key decisions (locked in PRD/RFC; owner-approved)

- **Cohesion-driven design is now a first-class flow principle** (peer to DDD/TDD/TBD) — codified in S0 into the CORE dev+review roles. Decompose monster modules BY RESPONSIBILITY; `domain-size-limit` passes as a CONSEQUENCE of real cohesion, never by node-reclassification gaming. **Guard against over-splitting** (cohesion > line count; one nameable responsibility per module; no shrapnel).
- **Behavior-preserving (G0):** no change to CLI/MCP output, gate verdicts, or graph semantics; full suite + `beadloom ci` green at every slice; golden-output tests for #123/#124/#128.
- **Fix the layering inversion** (`graph`→`application.reindex`) — in scope; `lint --strict` clean without the lazy-import workaround.
- **Cycle detection:** WHITE/GREY/BLACK + global-visited + path-as-set; preserve output (`seen_cycles`, `max_depth`). Not Tarjan.
- **Repository seam:** connection context-manager (no bare `open_db`) + `infrastructure/repository.py`; `tui/` reads through application, not raw SQLite.
- Decomposition maps (rules/federation/cli-commands/scanner/reindex/debt/dashboard) are in the RFC — dev validates exact cohesion boundaries with review.
- `__init__.py` re-exports keep public import paths stable across extractions (`git mv` preserves history).

## Standards (from CLAUDE.md §0.1 + this epic)

- **Stack:** Python 3.10+, SQLite, Click, Rich, tree-sitter. **Tests:** pytest + pytest-cov, coverage ≥ 80%, **TDD**.
- **Linter/formatter:** ruff. **Types:** `mypy --strict` (ty deferred).
- **Architecture:** DDD packages; boundaries enforced by `beadloom lint --strict`. **Trunk-based** (one PR per slice; `main` protected). **No shadow code** (`module-coverage`=error; new modules are graph nodes with `# beadloom:` annotations).
- **Cohesion-driven design (NEW, peer to the above):** one nameable responsibility per module/class/function; split monsters by responsibility; never over-split; `domain-size-limit` is a consequence, not a driver.
- Per-bead completion: `uv run pytest`, `ruff check`, `mypy src/`, `beadloom reindex && sync-check && lint --strict`, golden-output checks where applicable, checkpoint, `bd close`.

## Constraints / invariants

- **No public API / output change.** New modules/packages internal; CLI/MCP surface untouched. Verify before/after `beadloom ci` / `status` / `ctx` parity per slice.
- Do NOT regress the symbol-pair `sync_state` / reason-masking / fixpoint invariant, nor the `surface_drift` (reference) path from BDL-057.
- Generated `site/` is gitignored (BDL-056) — do NOT re-commit it.
- When removing a private-attr test assertion, replace it with the equivalent observable-behavior assertion (don't just delete).
- Each slice is independently green + mergeable; the epic can pause between slices.
