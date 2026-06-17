# RFC: BDL-060 — Integration Map with Data

> **Status:** Approved
> **Created:** 2026-06-17
> **Type:** epic
> **PRD:** ./PRD.md (Approved)

---

## Summary

Deepen the federation layer from *presence* to *data*: extract the real field/type surface of cross-service contracts, render it in an interactive landscape with clickable contract pop-ups, surface cross-repo contracts in `ctx`, raise landscape accuracy (undeclared sweep + `unverified`), federate one external verdict source, and make graph writes atomic. Delivered as **6 dependency-ordered, individually-shippable slices** (one PR each, dogfooded), one epic for coherence.

Design constraints (from the ROADMAP principles): byte-stable export/federate determinism; behavior-preserving on existing surfaces; tool/paradigm/language-agnostic; **single-repo honesty before cross-repo depth** (G1 correct on one service gates G3+); dogfood = acceptance.

## Decisions on the PRD open questions (owner-confirmed 2026-06-17)

- **Viz renderer → Cytoscape.js + the ELK layout extension (`cytoscape-elk`), computed at build time → `preset` positions.** Cytoscape gives interactivity + a fully customizable theme (CSS-like stylesheet: colors/fonts/shapes); **ELK** (Eclipse Layout Kernel) gives the readability the owner requires — non-overlapping node placement + orthogonal edge routing + ports (the built-in `cose` force-layout is NOT sufficient on dense graphs). ELK is deterministic, so we run it at **build time** and store positions in `landscape.data.json`; the page renders with `preset` → byte-stable AND high-quality layout. **The data model is renderer-agnostic** (a `landscape.data.json` of nodes/edges/contracts + positions) so the renderer is swappable (Cytoscape→D3) without re-extracting. A theme config (colors/fonts) is a first-class input.
- **GraphQL → deep, native, rigorous (the priority protocol).** Tier-A covers **queries, mutations, AND subscriptions**; fields → `{name, type (incl. nullability/list), args}`; nested input/object types. Beadloom computes the breaking-change verdict **itself** from the typed surface (a consumer-referenced field/arg absent, type-narrowed, or nullability-broken vs the producer surface → `BREAKING`, naming it; safe additions → benign). This is native + strict — no external GraphQL tool needed (an external `graphql-inspector`/Hive verdict would be *redundant* with this).
  - **Hive / The Guild awareness:** we do NOT reposition as a GraphQL schema-registry competitor (Hive owns that). Our value is GraphQL rigor **inside the multi-transport, intent/lifecycle-aware federated landscape** — the thing single-protocol tools can't do. Optional **interop** (ingest/emit The Guild's format) is a future nicety, NOT reimplementing the registry.
- **AMQP → strict JSON-Schema `body` (the second priority protocol).** An optional `contract.body` (JSON-Schema: properties/types/required/enums/nested) on the producer/consumer edge; the verdict diffs consumer-referenced body fields/types vs the producer's body schema. **Plus an optional AsyncAPI ingestion adapter** (extract the payload JSON-Schema from an AsyncAPI doc) so teams with AsyncAPI aren't left out — the internal model stays the minimal-honest JSON-Schema body; AsyncAPI is a *source*.
- **`unverified` → a new lifecycle value, not a new node-state.** Extend the existing edge/node `lifecycle` set with `unverified`; the hub reconciler treats it like `planned` for verdict purposes (present-or-absent is not DRIFT — "not yet confirmed by a human"), and the report/gate surface it as a distinct, actionable "needs review" bucket. Reuses the lifecycle machinery (no parallel state model).
- **DEFERRED to a future epic (owner-confirmed out of scope here):** external cross-protocol verdict federation (`buf`/protobuf, Pact `can-i-deploy`, REST/OpenAPI). The original G5 is dropped from BDL-060 — GraphQL is covered natively above; the other protocols and the "federate an external verdict source" capability are future work. This sharpens the epic onto **GraphQL + AMQP, done maximally**.

## Architecture by goal

### G1 — Field-level contract data (the spine; split into a GraphQL slice + an AMQP slice)
**G1a — GraphQL Tier-A (deep, native, the priority).** Extend SDL surface extraction (`graph/sdl.py`, today name-level `exposed`/`references` from BDL-038) to a **typed surface over queries, mutations, AND subscriptions**: operation → fields → `{name, type (with nullability + list wrapping), args:[{name,type}]}`, resolving nested input/object types. Parse via **`graphql-core`** behind an optional extra (`beadloom[graphql]`); absent it, fall back to today's name-level surface (honest degradation, no hard dep). Beadloom computes the GraphQL breaking verdict **itself** in `graph/contracts.py`: a consumer-referenced field/arg that is absent, type-narrowed, or nullability-broken vs the producer surface → `BREAKING` naming it; additive producer changes → benign. Subscriptions are first-class (a dropped/retyped subscription field is a break). The export `contract` payload gains a typed `fields` block (sorted/deduped for determinism, mirroring `graph/federation/reconcile.py::_normalize_contract_surface`).

**G1b — AMQP body (strict JSON-Schema).** The contract gains an optional `body` (JSON-Schema: properties/types/required/enums/nested) on the producer/consumer edge; carried verbatim in export, normalized (sorted keys) in reconcile; the verdict diffs consumer-referenced body fields/types vs the producer body schema. **Optional AsyncAPI ingestion adapter** extracts the payload JSON-Schema from an AsyncAPI doc (source-only; internal model stays JSON-Schema body).

- **Verdict:** the existing `EdgeVerdict`/`ContractVerdict` enums are unchanged; only the *matching* gains field/type depth. Byte-stable: golden export/federate artifacts updated once with the richer payload.
- **Touches:** `graph/sdl.py`, `graph/contracts.py`, `graph/federation/{export,reconcile}.py`; export schema version bump (additive — older readers tolerate missing typed `fields`/`body`).

### G2 — Interactive landscape + clickable contracts
- A new site artifact `landscape.data.json` (deterministic: sorted nodes/edges/contracts + preset positions) emitted by the site generators (`application/site_landscape.py` / `site.py`), plus a Cytoscape view page (`landscape.md` embeds the script + loads the JSON). Clicking a node/edge opens a **contract pop-up card**: protocol, routing/message-type, producer↔consumer, verdict, and the **G1 field surface**. Honest degradation: missing data renders "undeclared/unknown", never fake fields.
- **Touches:** `application/site_landscape.py`, `site.py`, the VitePress theme (a Cytoscape component); the existing Mermaid landscape stays as a fallback/secondary or is replaced (decided in the slice). Determinism test + no `ignoreDeadLinks`.

### G3 — Live cross-repo `ctx`
- `context_oracle/builder.py::build_context` gains an **optional federated-neighbour enrichment**: when a federation artifact (`federated.json`) is available (configured path), a node's bundle includes resolved `@repo-B:…` contract neighbours (the edges + their G1 surface). No federation artifact → no change (single-repo bundles byte-identical). Reads through the federation reconcile model, not a re-parse.
- **Touches:** `context_oracle/builder.py`, a config key for the federation artifact path, `services/commands/query.py` (ctx output). Cache-aware (the S5/BDL-059 `SqliteCache` etag must include the federation artifact's identity so a stale bundle isn't served).

### G4 — UNDECLARED sweep + `unverified` lifecycle
- A command (`beadloom sweep` or `federate --suggest`) that scans code-inferred producer/consumer signals with no matching declared edge and **emits suggestions** as `lifecycle: unverified` graph entries (written, never silently activated). Conflicts (an inferred edge contradicting a declared one) are **flagged for human review**, not auto-applied (anti-"MySQL-mistake"). Reconciler + report treat `unverified` as a distinct "needs review" bucket.
- **Touches:** the lifecycle enum (+`unverified`), `graph/rules/` (verdict handling), a new sweep entry under `application/` + a `services/commands/` command, report rendering.

### G5 — Verdict federation — ❌ DEFERRED to a future epic (owner-confirmed)
External cross-protocol verdict federation (`buf`/protobuf, Pact `can-i-deploy`, REST/OpenAPI) is **out of scope for BDL-060**. GraphQL is covered natively (G1a); protobuf/REST and the "ingest an external verdict source" capability are deferred. Not built here.

### G6 — Atomic YAML writes (foundational safety, do first)
- A single `write_yaml_atomic(path, data)` helper (temp file in the same dir + `os.replace`) used by every graph-YAML writer (the loader/patcher in `graph/` + onboarding `services.yml` patchers). Regression test: simulate a crash mid-write → the prior file is intact.
- **Touches:** `infrastructure/` (the helper) + every call-site that writes a graph YAML; behavior-preserving (same final bytes, safe interruption).

## Slice plan (dependency-ordered; one PR each)

```
S1 (G6)  atomic YAML writes              ── independent, small, foundational safety → first
S2 (G1a) GraphQL Tier-A (deep, incl. subscriptions) ── the SPINE; depends on S1
S3 (G1b) AMQP body (JSON-Schema + optional AsyncAPI ingestion) ── depends on S1; sibling of S2 in the contract model
S4 (G2)  interactive viz (Cytoscape + ELK) ── depends on S2 + S3 (renders the field data of both protocols)
S5 (G3)  live cross-repo ctx             ── depends on S2 + S3 (surfaces the field surface in bundles)
S6 (G4)  undeclared sweep + unverified   ── depends on S1; informed by S2 + S3
```

Six slices, one epic. **G5 (external verdict federation) is dropped** (deferred — see above); the data spine is split by protocol (G1a GraphQL / G1b AMQP) for cohesion + manageable, maximally-rigorous PRs. Each slice = the mandatory 4-role bead structure (dev → test → review → tech-writer), TDD, behavior-preserving, `beadloom ci` rc0, dogfooded on the anonymized landscape fixture, merged as its own PR before the next starts (sequencing principle 1 — one thread at a time, no parallel fronts). After S3, the order S4→S5→S6 is the default but they are independent given S2+S3 — still **one at a time**.

## Cross-cutting / risks

- **Determinism:** every new payload (fields, body, landscape.data.json, federated verdicts) is sorted/deduped + golden-tested; preset viz layout (no view-time randomness).
- **Optional deps:** `graphql-core` (G1) and `graphql-inspector` (G5) are optional extras / feature-flagged subprocesses — absent → honest degradation, never a hard failure.
- **Cache correctness (G3):** the bundle cache etag must fold in the federation artifact identity (else a stale cross-repo bundle is served).
- **Schema-version bumps** stay additive (older readers tolerate missing `fields`/`body`); bump only on the producer side, document in the federation SPEC.
- **Viz is a softer one-way door** — mitigated by the renderer-agnostic data model (swap Cytoscape→D3 later without re-extracting).
- **Coordinator boundary:** this RFC is design-level; each dev slice verifies the exact current symbols/call-sites against HEAD (`beadloom ctx`/`why`) before implementing — the module/function names here are the intended seams, to be confirmed per slice.

## Out of scope (per PRD non-goals + owner refocus)
**External cross-protocol verdict federation (`buf`/protobuf, Pact, REST/OpenAPI) — deferred to a future epic** (the original G5). gRPC/proto sources; full AsyncAPI (only optional payload-schema ingestion is in); a live web hub; full bootstrap accuracy; Backstage replacement; model tiering. The epic is sharpened onto **GraphQL (incl. subscriptions) + AMQP, done maximally** — the two protocols the team relies on.
