# PRD: BDL-059 — Code-health debt paydown (growth-gating refactors)

> **Status:** Approved
> **Created:** 2026-06-15
> **Type:** epic

---

## Problem

The P0 agentic cluster and the docs-freshness loop are shipped (through 2.1.0), and the next thread is the P1 "integration map with data" (north-star b — team/microservices). That work will **heavily touch `graph/` and `doc_sync/`** — exactly the packages carrying the most code-health debt. ROADMAP states it explicitly: *"the repository-layer + connection items gate growth (before large refactors / scale)."* Paying this down first is the honest, lower-risk sequencing (principle 1: one end-to-end thread, made honest before the next).

The growth-gating debt, all verified open at HEAD (BDL-UX-Issues + ROADMAP §Technical-debt):

- **#122 [HIGH]** — no data-access layer; `open_db` is called with no `with`/`closing` anywhere (connection leaks, SQLite write-lock risk, test ResourceWarnings); raw `conn.execute` spread across ~36 files incl. `tui/data_providers.py` (presentation reading SQLite — a layer leak); `SELECT ref_id, kind, summary FROM nodes` hardcoded ~16×.
- **#123 [HIGH]** — N+1 + non-indexable `LIKE '%…%'` in `doc_sync/engine.py` `check_source_coverage` → quadratic on a large graph.
- **#125 [MED]** — `graph/` is a god-domain (214 symbols > the 200 `domain-size-limit` → a warning on every `beadloom ci`); `application/` is 252 > 200. Mixes `federation` + `rules` + loader/diff/linter concerns.
- **#124 [MED]** — cycle detection (`rule_engine.py`) re-explores from every node with no global `visited`; `neighbor in path` is O(n); exponential risk on a dense microservice graph.
- **#126 [MED]** — god-functions carry business logic in the wrong layer: `cli.py:status` (~283 lines), `scanner.bootstrap_project` (~260), `reindex.incremental_reindex` (~216), `scanner.interactive_init` (~203).
- **#129d [MED]** — **372 private-attribute (`._x`) test couplings** that block refactors (tests assert on internals, so any refactor breaks them); plus test hygiene (#129a-f: ResourceWarning db fixtures, mandatory tree-sitter grammars in CI, parametrization, `pytest-randomly`).
- **#128 [MED]** — the L2 `bundle_cache` is not wired into `build_context` (`SELECT * FROM code_symbols` per bundle) → latency on large monorepos.
- **#127 [LOW, remaining]** — `Any` concentration in `onboarding` (doc_generator/scanner/config_reader) + `git_activity.py:251` `except ValueError: pass`.

## Impact

- **Unblocks P1 cleanly.** The federation/viz work refactors `graph/` and queries `doc_sync/`; a repository seam + a split `graph/` + decoupled tests make that work safe instead of a minefield.
- **Architectural honesty.** Beadloom sells boundary enforcement; carrying a 252-symbol god-package + a leaky data layer + uncaught cycle-cost is a credibility gap (cf. the original #91 self-audit class).
- **Scale-readiness.** The N+1 (#123), per-bundle full scans (#128), and exponential cycle detection (#124) are latent at this repo's size but real on the 1000+-node landscapes the product targets.
- **Refactor safety.** #129d is the keystone: until tests stop asserting on private internals, every refactor below is fragile.

## Goals

- **G0 — Behavior-preserving.** This is a refactor epic: **no change to CLI/MCP output, gate verdicts, or graph semantics.** The full test suite stays green at every slice; `beadloom ci` stays rc 0. A published behavior change is out of scope.
- **G1 — Test decoupling first (#129d + hygiene).** Remove the 372 private-attribute couplings (assert through public APIs / the new repository), add db yield/finally fixtures (kill ResourceWarnings), make tree-sitter grammars mandatory in CI, add `pytest-randomly`. This is the keystone that makes the rest safe.
- **G2 — Data-access layer + connection lifetime (#122).** Introduce `infrastructure/repository.py` (one home for the hardcoded queries) + a connection context-manager; route `tui` through the application layer (no direct SQLite in presentation). No `open_db` without `with`.
- **G3 — Kill the N+1 (#123).** `check_source_coverage` via a single JOIN / `IN (...)`; drop the non-indexable `LIKE`.
- **G4 — Split the god-domains (#125).** Extract `federation` and `rules` out of `graph/` into their own packages (clears the graph-214 warning); reduce `application/` below 200 (note the tension with G5 — see RFC). The `domain-size-limit` lint goes quiet by construction.
- **G5 — Extract god-functions (#126).** `cli.py:status` → `application/status.py`; decompose `scanner.bootstrap_project` / `reindex.incremental_reindex` / `scanner.interactive_init`.
- **G6 — Algorithmic + cache fixes (#124, #128).** Cycle detection with WHITE/GREY/BLACK + global visited (or Tarjan/Johnson); wire `build_context` through the L2 `bundle_cache`.
- **G7 — Type-hardening tail (#127).** TypedDict/dataclasses for the `Any`-heavy onboarding parsers; narrow `git_activity` exception.

## Non-goals (out of scope)

- **Any behavior/feature change.** No new CLI flags, no output format changes, no new graph semantics. (If a bug is found mid-refactor, log it — don't fix it inline unless trivial + tested.)
- **The P1 integration-map work itself** (field-level contracts, viz, cross-repo `ctx`) — that is the NEXT thread, enabled by this one.
- **A schema-migration framework** (#100, separate P2) beyond the migration guard already shipped.
- Chasing every `Any` in the codebase — only the onboarding concentration (#127).
- `ty` migration (still deferred; keep `mypy --strict`).

## Open architecture questions (→ resolved in the RFC)

- **`application/` 252 vs G5:** moving `cli.py:status` business logic INTO `application/status.py` *grows* `application`. How do we get `application` under 200 while absorbing god-function logic — extract sub-packages (e.g. `application/reporting/`), or raise the cap for the orchestration layer, or both? (RFC decides; the `domain-size-limit` is a `check` rule, tunable.)
- **Repository shape (#122):** one `repository.py` module vs a small package; sync vs a thin query-object layer; how `tui` consumes it without importing infrastructure directly (through application).
- **Slicing for trunk-based:** one epic, but landed as how many behavior-preserving PRs? (Proposed: 4 slices — see PLAN — each green + independently mergeable, not one mega-PR.)
- **Cycle-detection replacement:** WHITE/GREY/BLACK DFS vs Tarjan SCC — which keeps the existing rule semantics (per-rule `seen_cycles` dedup) intact?

## User stories

### US-1: The next refactor doesn't break a hundred tests
As a maintainer, when I split `graph/` or introduce a repository, tests assert through public APIs / the repository — so a structural change doesn't cascade into 372 private-attribute failures.

### US-2: The gate stops nagging about god-packages
As a maintainer, `beadloom ci` no longer prints `domain-size-limit` warnings — the structure honestly satisfies its own rule.

### US-3: No connection leaks
As a maintainer, every DB connection is context-managed; the suite runs clean under `filterwarnings=error::ResourceWarning`.

### US-4: Scale-safe internals
As an operator on a 1000+-node landscape, `sync-check` (no N+1), `ctx`/`prime` (L2 cache), and lint (bounded cycle detection) stay fast.

## Acceptance criteria

- **Behavior unchanged:** full `pytest` green and `beadloom ci` rc 0 at every slice; no diff to CLI/MCP output, gate verdicts, or graph results on the dogfood repo (verified by the test suite + a before/after `beadloom ci` / `ctx`/`status` spot check).
- The 372 private-attribute test couplings are removed (tests assert through public APIs / the repository); ResourceWarnings gone; CI fails if tree-sitter grammars are missing; `pytest-randomly` active.
- `infrastructure/repository.py` exists; no `open_db` without a context-manager; `tui` no longer reads SQLite directly.
- `check_source_coverage` is no longer N+1 / `LIKE '%…%'`.
- `graph/` and `application/` are both ≤ 200 symbols (or the `domain-size-limit` rule is intentionally, visibly adjusted with rationale); `federation` + `rules` are their own packages; **no `domain-size-limit` warning in `beadloom ci`**.
- `cli.py:status` lives in `application/`; the scanner/reindex god-functions are decomposed.
- Cycle detection uses a global-visited algorithm; `build_context` goes through the L2 cache.
- The onboarding `Any` concentration is reduced via TypedDict/dataclasses; `git_activity` exception narrowed.
- Beadloom still governs itself: `lint --strict` clean, `module-coverage` (no shadow code) holds for any new modules/packages.
