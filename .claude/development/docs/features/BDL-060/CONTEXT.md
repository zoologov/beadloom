# CONTEXT: BDL-060 — Integration Map with Data

> **Status:** Approved
> **Created:** 2026-06-17
> **Type:** epic
> **PRD:** ./PRD.md (Approved) · **RFC:** ./RFC.md (Approved)

---

## Core decisions (owner-approved, the single source of truth for this epic)

- **Scope = GraphQL (incl. subscriptions) + AMQP, done maximally.** One epic, six dependency-ordered slices, one PR each, "spokojno / max quality."
- **Viz = Cytoscape.js + `cytoscape-elk`, layout computed at build time → `preset` positions** in `landscape.data.json`. Renderer-agnostic data model; themeable (colors/fonts via a theme config); byte-stable page.
- **GraphQL = native + strict.** Typed Tier-A surface (queries/mutations/subscriptions; fields `{name,type+nullability+list,args}`; nested types) via `graphql-core` (optional extra, honest degradation). Beadloom computes the breaking verdict itself; no external GraphQL tool. **Hive/The Guild:** integrate GraphQL rigor INTO the federated multi-transport landscape, do NOT reimplement their registry; interop is future.
- **AMQP = strict JSON-Schema `body`** + optional AsyncAPI ingestion adapter (source-only; internal model stays JSON-Schema).
- **`unverified` = a new `lifecycle` value** (not a new node-state); reconciler treats it like `planned` for DRIFT, surfaced as a distinct "needs review" bucket.
- **DEFERRED (future epic):** external cross-protocol verdict federation (`buf`/protobuf, Pact, REST/OpenAPI), full AsyncAPI, live web hub, Backstage replacement, model tiering.

## Engineering standards (NON-NEGOTIABLE for every slice — copied from CLAUDE.md §0.1 + owner emphasis)

- **Stack:** Python 3.10+, SQLite, Click, Rich, tree-sitter. Tests: pytest + pytest-cov + pytest-randomly. Linter/formatter: ruff. Types: `mypy --strict` (no `Any` / `# type: ignore` without a stated reason).
- **TDD** — write the test first; RED→GREEN; coverage ≥ 80% on touched code; golden-output tests for any extraction/verdict/serialization change.
- **DDD layering** — respect the domain packages (`ai_agents/`, `application/`, `context_oracle/`, `doc_sync/`, `graph/`, `infrastructure/`, `onboarding/`, `services/`, `tui/`); no layer inversions (`beadloom lint --strict` is the enforcement); presentation never reads SQLite directly (go through the application/repository seam from BDL-059 S2).
- **Cohesion-driven design** (first-class, peer to DDD/TDD/TBD) — one nameable responsibility per module; no monster files, no over-splitting; `domain-size-limit` is a consequence, recalibrated openly if a domain is legitimately large (never gamed by reclassification). New protocol extractors live in cohesive modules under `graph/`.
- **Data strictness (the Beadloom core value)** — extraction and verdicts must be rigorous and honest: no fake fields, no false-CONFIRMED; a verdict is only as strong as the data behind it; honest degradation when an optional dep/source is absent (never a silent pass). Determinism: every emitted payload (typed fields, body schema, `landscape.data.json`, federated verdicts) is sorted/deduped + golden-tested; byte-stable export/federate/site regeneration preserved.
- **Behavior-preserving on existing surfaces** — no CLI/MCP output, gate-verdict, or graph-semantics change except the intended additive deepening; schema-version bumps stay additive (older readers tolerate missing typed `fields`/`body`).
- **Gate-green per slice** — `beadloom reindex && lint --strict && sync-check && docs audit && config-check && doctor` (i.e. `beadloom ci` rc 0) + full `pytest` green under multiple `--randomly-seed`s; **dogfood = acceptance** (the anonymized landscape fixture exercises the slice end-to-end before it's "done").
- **Optional deps** — `graphql-core` (GraphQL), AsyncAPI parsing (AMQP) are optional extras; absent → fall back honestly, never hard-fail.

## Dogfood fixture (acceptance substrate)

The anonymized multi-service corpus already in the test suite (`catalog-service` / `storefront-web` + the 4 AMQP contracts + the GraphQL `WebAPI` producer/consumer from BDL-038). Each slice must prove its capability on this fixture: real fields in a pop-up; a seeded field-level break caught by name; a cross-repo `ctx` neighbour; a seeded undeclared integration surfaced as `unverified`.

## Key seams (to be confirmed against HEAD per slice via `beadloom ctx`/`why` — coordinator does NOT read raw source)

- GraphQL surface: `graph/sdl.py`. Contract reconciliation/verdicts: `graph/contracts.py`. Export/reconcile: `graph/federation/{export,reconcile}.py` (federation became a package in BDL-059 S3).
- Lifecycle/verdict enums: `graph/federation/reconcile.py` (`EdgeVerdict`) + `graph/contracts.py` (`ContractVerdict`); rule handling: `graph/rules/` (package, BDL-059 S3).
- Site generation: `application/site_landscape.py` + `application/site.py` (+ VitePress theme under `site/.vitepress/`); dashboard data pattern: `application/site_dashboard/` (package, BDL-059 S4).
- Context bundles: `context_oracle/builder.py` (+ `context_oracle/cache.py` — the `SqliteCache` wired in BDL-059 S5; its etag must fold in the federation artifact identity for G3).
- Graph YAML writes: the loader/patchers in `graph/` + onboarding `services.yml` patchers → all route through the new `write_yaml_atomic` (G6/S1).
- CLI commands: `services/commands/` (package, BDL-059 S4); MCP: `services/mcp_server.py`.

## Process / lessons carried from BDL-059

- One PR per slice on `features/BDL-060` (trunk-based; `main` protected; squash-merge; the PR-triggered AI tech-writer + CI are the gate).
- Heavy/parallel dev uses worktree isolation; integrate by **file-checkout + 3-way only on the shared seam** (NOT branch-merge — avoids bd-jsonl conflicts); **re-baseline `sync-update --yes --all` to fixpoint after integration** (#133, per-worktree DB).
- Recompose role adapters WITHOUT `--force` (#132); `cp` live→vendored to re-vendor.
- `surface_drift` on `reference` docs is warn-only and may not fixpoint (#134) — `beadloom ci` rc0 is the real signal.
- Verify refactors/extractions under multiple `--randomly-seed`s (a single seed hides order-dependence).
- Generated `site/` is gitignored — do NOT commit generated pages (only the hand-authored shell).
