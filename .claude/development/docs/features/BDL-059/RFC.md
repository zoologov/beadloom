# RFC: BDL-059 — Code-health debt paydown (cohesion-driven)

> **Status:** Approved
> **Created:** 2026-06-15
> **PRD:** ./PRD.md
> **Type:** epic

---

## Summary

Pay down the growth-gating debt by **genuinely decomposing the monster modules along cohesion lines** and fixing the real layering inversion — not by gaming the `domain-size-limit` metric. Codify **cohesion-driven design as a first-class flow principle** (peer to DDD/TDD/TBD) so it governs this epic and all future work. Land it in behavior-preserving slices, each a green PR.

Hard invariant: **no change to CLI/MCP output, gate verdicts, or graph semantics** — full suite green + `beadloom ci` rc 0 at every slice.

## The governing principle (codified in S0)

> **Cohesion-driven design (non-negotiable; peer to DDD / TDD / trunk-based).** Every module, class, and function carries ONE clear responsibility you can name in a phrase. A module that mixes responsibilities (or has grown past readability) is split BY RESPONSIBILITY — types / policy / I/O / orchestration as separate cohesive units. **Cohesion is the driver, not line count:** do NOT over-split into shrapnel (tiny files, indirection for its own sake, a flow you must chase across a dozen files). Size limits (`domain-size-limit`) are a proxy that must pass as a CONSEQUENCE of real cohesion — never satisfied by reclassifying nodes to hide a monster file.

This goes into the CORE `dev` role (design rule) + the CORE `review` role (review check), recomposed into the adapters (drift-guarded), exactly where DDD/TDD already live.

## What changed from the previous draft (owner feedback)

The first draft optimized for the `domain-size-limit` symbol-count and proposed shrinking `application` by **reclassifying `site_*.py` onto another node** — that gamed the lint without shrinking any file. Rejected. This draft:
- Decomposes the actual large, low-cohesion modules by responsibility.
- **Fixes the layering inversion** (`graph` → `application.reindex` reverse imports) instead of declaring it out of scope.
- Treats `domain-size-limit` as a consequence, never a driver.
- Guards against over-splitting (cohesion > line count).

## Decomposition targets (by responsibility — dev confirms exact boundaries with review)

> Proposed responsibility maps from the structural survey. Each is a hypothesis the dev bead validates against actual cohesion; the rule is "one nameable responsibility per module", not a line target.

**`graph/rule_engine.py` (2,249 LOC) → `rules/` package:**
- `rules/types.py` — rule dataclasses + `NodeMatcher` + `Violation` (the model).
- `rules/loader.py` — `load_rules` / `validate_rules` (YAML → typed rules).
- `rules/evaluators.py` — per-rule-type evaluation (deny/require/forbid/layers/import/cardinality).
- `rules/cycles.py` — cycle detection (rewritten, see #124).
- `rules/__init__.py` — `evaluate_all` orchestration + public re-exports (stable API).

**`graph/federation.py` (1,000 LOC) → `federation/` package:**
- `federation/refs.py` — `FederatedRef` / `parse_ref` / `FederationRefError` (cross-repo identity).
- `federation/export.py` — `build_export` / `serialize_export` (deterministic satellite artifact).
- `federation/reconcile.py` — landscape reconciliation (consumes `graph/contracts.py`, which STAYS as the shared model).

**`services/cli.py` (monolith of all commands) → `services/commands/` package:** one cohesive module per command group (e.g. `commands/graph.py`, `commands/docs.py`, `commands/federation.py`, `commands/setup.py`, `commands/dev_flow.py`), with `cli.py` as the thin Click group wiring. `status`'s business logic → `application/status.py` (own feature node; #126).

**`onboarding/scanner.py` (~2,500 LOC) → `onboarding/scanner/` package:** `detect.py` (dir/preset/framework detection), `classify.py` (node-kind classification), `bootstrap.py` (`bootstrap_project` orchestration), `interactive.py` (`interactive_init` prompts). Business logic out of the prompt loop (testable without stdin).

**`application/reindex.py` (1,371 LOC) → `application/reindex/` package:** `full.py`, `incremental.py`, `fingerprint.py` (parser fingerprints + change detection), `__init__.py` (orchestration + stable API).

**`application/debt_report.py` (1,109) + `application/site_dashboard.py` (845):** split collection / scoring / formatting (debt) and data-build / render (dashboard) into cohesive modules.

**Left as-is (cohesive at their size — NOT split for the metric):** `contracts.py` (402), `loader.py` (457), `c4.py` (662, renderers), `diff.py`, `snapshot.py`, `linter.py`, etc. Splitting these would be over-splitting.

## Decisions on the open questions

1. **`application` / `graph` size → consequence of real decomposition.** After the cohesion splits above, the `graph` and `application` graph nodes are re-classified to mirror the NEW real structure (`rules`, `federation`, `status`, decomposed reindex, etc. as their own nodes) — and `domain-size-limit` passes because the modules are genuinely smaller, not because we hid them. **No reclassification-without-decomposition.**
2. **Layering inversion (in scope now).** `graph/linter.py` + `graph/import_resolver.py` import `application.reindex` — a lower layer reaching up. Fix by inverting the dependency: the reindex-orchestration entry these need moves to (or is invoked from) the `services`/`application` layer, or is passed in via a narrow interface, so `graph` stops importing `application`. Verified by `beadloom lint --strict` (architecture-layers + forbid_import) going clean WITHOUT the lazy-import workaround.
3. **Cycle detection — WHITE/GREY/BLACK + path-as-set (NOT Tarjan).** Preserve output ("all unique normalized cycles", `seen_cycles`, `max_depth`); replace per-node re-exploration + O(n) `neighbor in path` with explicit coloring + global visited + set membership. Golden-output test pins equivalence.
4. **Repository seam (#122).** `infrastructure/db.py` gains a connection context-manager (no bare `open_db`); new `infrastructure/repository.py` centralizes the repeated queries; `tui/` consumes application/repository read functions (no direct `.execute()` — closes the presentation→SQLite leak). Cohesion-driven: `repository.py` is split if it grows multi-responsibility (e.g. node/edge/sync/symbol query groups).
5. **Slicing — S0..S5, sequenced.** Behavior-preserving, one green PR each.

## Slices

- **S0 — Codify cohesion-driven principle.** Add it to CORE `dev` + `review` roles (`onboarding/templates/roles/core/`), recompose adapters (`setup-agentic-flow`), drift-guard green. Update CONTEXT. (Tiny; governs everything after.)
- **S1 — Test decoupling + hygiene (#129d + #129a-f).** Decouple the ~90 genuine production-internal couplings (TUI props, `Doctor`) — leave test-internal fixture helpers; db yield/finally fixtures (ResourceWarnings); `pytest-randomly`; tree-sitter grammar CI guard. Keystone for safe refactor.
- **S2 — Data-access seam + N+1 (#122 + #123).** Connection context-manager; `repository.py`; TUI through application; rewrite `check_source_coverage` (single CTE/JOIN, drop non-indexable `LIKE`). Golden-output test.
- **S3 — Decompose `graph/` by cohesion + fix layering + cycles (#125-graph + #124 + layering).** `rules/` + `federation/` packages by responsibility; invert the `graph`→`application` deps; WHITE/GREY/BLACK cycles. `beadloom lint --strict` clean, no `domain-size-limit` warning on `graph`, no lazy-import workaround.
- **S4 — Decompose `services`/`application`/`onboarding` monsters (#126 + big files).** `cli.py` → `commands/`; `reindex.py` → `reindex/`; `scanner.py` → `scanner/`; `debt_report.py` / `site_dashboard.py` split; `cli:status` → `application/status.py`. Node re-classification mirrors the new structure.
- **S5 — Cache + types tail (#128 + #127).** Wire `build_context` through `SqliteCache`; TypedDict/dataclasses for onboarding `Any`; narrow `git_activity` `except`.

## Behavior-preservation discipline (every slice)

- **Golden tests before refactor** (coverage results #123, cycle violations #124, bundle contents #128) — capture current output, assert identical after.
- Full `pytest` + `beadloom ci` rc 0 per slice; before/after spot-check of `beadloom ci` / `status` / `ctx` on the dogfood repo (no diff).
- No public API / output change; new modules are internal, carry `# beadloom:` annotations + graph nodes (module-coverage stays error-clean).
- `git mv` for extractions (preserve history); package `__init__.py` keeps the prior public import paths stable (re-export) so callers don't churn.

## Alternatives considered

- **Reclassify nodes to satisfy `domain-size-limit`** → REJECTED (gaming the metric; the owner's core objection). Decompose for real.
- **Move big files into new packages without splitting them** → REJECTED (a monster in a new folder is still a monster).
- **Tarjan SCC for cycles** → REJECTED (changes output semantics).
- **Over-decompose to minimize line count** → REJECTED (anti-pattern; cohesion is the driver — the S0 principle guards both directions).
- **Raise `domain-size-limit`** → REJECTED (hides the smell).
- **One mega-PR** → REJECTED (un-reviewable; trunk-based slices).

## Risks & mitigations

- **Scope is large** (cohesion decomposition of ~7 monster modules across 4 packages). Mitigation: strict slicing + behavior-preservation + per-slice green gate; each slice independently valuable and mergeable; can pause between slices.
- **Silent behavior change** → golden-output tests + green-gate-per-slice + review wave per slice.
- **Over-splitting** (the opposite failure) → the S0 principle is an explicit review check ("one nameable responsibility; no shrapnel"); review rejects both monsters and over-fragmentation.
- **Circular imports on package extraction** (loader↔contracts↔federation) → contracts stays put; federation/rules extracted as leaf consumers; `beadloom lint --strict` after each split.
- **Public-API churn from moved modules** → `__init__.py` re-exports keep import paths stable; CLI/MCP surface untouched.
- **Decoupling removes a test that encoded real behavior** → replace each private-attr assertion with the equivalent observable-behavior assertion, never just delete.

## Rollout

One epic, one PR per slice → `main`, green-gated, S0→S1→S2→S3→S4→S5 (the bead DAG enforces order; S0+S1 are the keystones). dev→test→review per slice; tech-writer where docs reference changed internals (mainly `docs/architecture.md` + the domain READMEs/SPECs for the new `rules`/`federation`/`status`/`reindex` structure). Pure internal refactor → likely no version bump (or a PATCH after S5). Cohesion-driven becomes a permanent flow principle from S0 onward.
