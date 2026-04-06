# RFC: BDL-038 — F2: Cross-Service Contract Graph

> **Status:** Approved
> **Created:** 2026-06-01

---

## Summary

Promote the cross-service contract from an edge-buried `extra.contract` blob (F1) into a **first-class, protocol-agnostic, language-neutral contract graph** computed at the hub. Add **GraphQL SDL** alongside AMQP as a contract source, with a UI/mobile client as a legitimate consumer. Compute **contract-level** intent-vs-reality verdicts (drift, orphaned consumer, undeclared producer, GraphQL breaking-shape) on top of F1's per-edge verdicts. Make the model survive arbitrary paradigms (FSD kinds), tag non-indexed nodes `external`/`unmapped` instead of dropping them into drift noise, and scope reconciliation by **landscape** so unrelated products in a company-landscape never cross-pollute each other's verdicts.

This is **purely additive and backward-compatible** with F1: a v1 export still federates; an AMQP-only landscape behaves as before; refs without `@` stay local; nodes/edges without `lifecycle` default to `active`.

## Design principles (carried from STRATEGY-3)

1. **Intent vs Reality is the moat** — the *diff* between declared contracts and both-sides reality is the product.
2. **Honest unknowns** — a present-but-unmapped node is `external`, never a fake DRIFT; an unparseable SDL is reported, never silently "confirmed".
3. **Deterministic artifacts** — sorted keys, byte-identical output, reviewable diffs (extends F1).
4. **Satellite stays dumb, hub stays smart** — satellites declare + parse local sources at `reindex`/`export`; all cross-repo reconciliation happens at `federate`. The hub never needs a satellite's files.
5. **Paradigm/language-agnostic by construction** — `kind`/`edge_kind`/`contract_key` are free-form; no DDD assumption anywhere in the contract path.

---

## Architecture

### Module layout

`graph/federation.py` is already 693 LOC and the `graph` domain is near the `domain-size-limit`. F2 splits the new surface into focused modules (keeps lint green):

| Module | Responsibility |
|--------|----------------|
| `graph/federation.py` (existing) | Identity (`FederatedRef`), export, `aggregate_exports` orchestration, provenance/staleness. **Delegates** contract reconciliation to `contracts.py`. |
| `graph/contracts.py` (**new**) | First-class `Contract` model, `ContractVerdict` enum, protocol-agnostic reconciliation (`reconcile_contracts`), language-neutral `contract_key` derivation. |
| `graph/sdl.py` (**new**) | Minimal, dependency-free GraphQL SDL **surface extractor**: parse `schema.graphql` → exposed operation/type/field names. No full schema validation (non-goal). |

`infrastructure/db.py` gets one additive migration (lifecycle `external`); `graph/loader.py` gets a protocol-aware `_contract_key` + SDL-surface folding; `services/cli.py` `federate`/`export` gain the `landscape` flag + the richer report. The contract path touches **no** DDD-specific code.

### 1. Contract as a first-class object (G1)

Authors keep declaring contracts **on edges** in YAML (no satellite-side migration — F1 wire format is preserved). The hub *projects* those edges into first-class `Contract` objects during `federate`:

```python
# graph/contracts.py
@dataclass
class Contract:
    contract_key: str                 # language-neutral identity (see §3)
    protocol: str                     # "amqp" | "graphql"
    name: str                         # human label (message type / schema name)
    producers: list[ContractEndpoint] # repo + ref_id + source_file (+ exposed surface for graphql)
    consumers: list[ContractEndpoint] # repo + ref_id + source_file (+ referenced surface)
    lifecycle: str                    # most-significant declared lifecycle across endpoints
    verdict: ContractVerdict
```

`FederatedGraph.contracts` becomes `list[Contract]` (serialized to dicts), replacing F1's flat `{message_type, confirmed, ...}` entries. The F1 fields are preserved as a subset for backward-compatible report rendering. The per-edge `EdgeVerdict` (F1) stays — contracts are an *additional* projection, not a replacement.

### 2. GraphQL SDL contract source (G2)

- **Producer side (satellite, at `reindex`/`export`):** a node/edge declares `produces` with `contract: {protocol: graphql, source_file: schema.graphql}`. `graph/sdl.py` parses the SDL and folds the **exposed surface** (top-level `Query`/`Mutation`/`Subscription` field names + type names) into the contract payload as `exposed: [...]`. Parsing happens satellite-side so the export is self-contained (hub needs no files — principle 4). An unparseable SDL records an error and emits `exposed: []` (honest, not silently confirmed).
- **Consumer side (satellite):** a client repo declares `consumes @backend:<SchemaNode>` with `contract: {protocol: graphql, references: [op/type/field, ...]}` — the operations/types it actually uses. This is the **first UI client as a consumer** in federation; the consumer is TS/FSD, the producer is the backend — they meet only via the contract name (§3), never a code symbol.

> **SDL parser decision:** a minimal in-house extractor (regex/line-scan over `type Query {...}`, `type Mutation {...}`, `type X {...}`) — **no new runtime dependency**. Scope = name-presence only, which is all the presence-based breaking check (§5) needs. `graphql-core` is noted as a future upgrade path if field-type/argument-level diffing is ever required (F3+), but is out of scope here.

### 3. Language-neutral `contract_key` / `FederatedRef` (G3 + G4)

F1's `_contract_key` returns the bare AMQP `message_type`. F2 generalizes it to a protocol-prefixed, discriminator-rich key so cross-language and cross-exchange contracts resolve correctly:

```
amqp:    "amqp:<exchange>/<routing_key>:<message_type>"   # G4 — exchange/routing folded in
graphql: "graphql:<schema_name>"                          # G3 — resolves TS client ↔ backend SDL
```

- **G3:** the key is derived purely from contract *names*, never a code symbol, so a TS consumer and a Python producer reconcile across the language boundary.
- **G4:** two services sharing a message *name* under a different exchange/routing are no longer falsely "confirmed both-sides" — the exchange is part of the key. (F1 non-goal "queue/exchange identity matching deferred to F2" — closed here.)

Backward compat: a v1 export whose AMQP contract carries only `message_type` (no exchange) derives `amqp:*:<message_type>` (wildcard exchange) and still reconciles with another v1 side — no regression.

### 4. Reconciliation algorithm (hub, `contracts.py`)

```
group edges that carry a contract by (landscape, contract_key)       # §6 scopes the group
for each group:
    producers = endpoints whose contract.direction == "produces"
    consumers = endpoints whose contract.direction == "consumes"
    verdict   = classify(producers, consumers, lifecycle, protocol)
    emit Contract(...)
```

`classify` (the moat — §5). Explicit `@repo:` edges always resolve cross-landscape; **implicit** same-key matching is scoped *within a landscape* (§6) so unrelated products don't auto-confirm on a coincidental same name.

### 5. Contract-level intent-vs-reality verdicts (G5)

```python
class ContractVerdict(enum.Enum):
    CONFIRMED          # producers ∧ consumers present, shapes compatible
    DRIFT              # declared active, present on only one side (the killer signal)
    ORPHANED_CONSUMER  # consumes a contract nobody produces
    UNDECLARED_PRODUCER# produces a contract nobody consumes
    BREAKING           # graphql: a consumer 'references' an op/type absent from producer 'exposed'
    EXPECTED           # lifecycle planned / deprecated-and-gone (intentional, not drift)
    EXTERNAL           # the contract target is an external/unmapped node (§7) — never DRIFT
    DEAD               # declared dead
```

`BREAKING` is the new GraphQL signal: `references ⊄ exposed` ⇒ the consumer relies on something the producer's current SDL no longer offers — a break caught *before it ships* (the F2 success criterion). It is **presence-based** (name in/out of the SDL surface), not a historical schema-version diff (non-goal). F1's AMQP "confirmed both-sides" maps onto `CONFIRMED`; "one-sided" splits into `ORPHANED_CONSUMER` / `UNDECLARED_PRODUCER`.

### 6. Nested landscapes — product vs company (G8 / U5)

- Add an optional **`landscape`** field to the export provenance (resolved like `repo`: `.beadloom/config.yml` `landscape:` key > falls back to `repo`). It names the product a satellite belongs to.
- `federate` composes either **one product-landscape** (all satellites share a `landscape`) or a **company-landscape** (several). Implicit contract matching (§4) groups by `(landscape, contract_key)`, so two unrelated products **never** auto-confirm or auto-DRIFT on a coincidental same name. A **real** cross-product contract is expressed explicitly with `@otherrepo:` and always resolves regardless of landscape.
- Result (US-3 acceptance): two contract-less products in one `federate` run produce **zero** mutual DRIFT/UNDECLARED; a genuine cross-product edge still appears with a both-sides verdict.

### 7. `external` / `unmapped` lifecycle (G7 / U4)

- Extend `VALID_LIFECYCLES` with **`external`** (a node the author declares as present-but-not-ours, e.g. a native Swift/Kotlin/ObjC++/C++ bridge in `modules/`). An edge whose target is `external` → `ContractVerdict.EXTERNAL` / `EdgeVerdict` suppresses DRIFT.
- **`unmapped`** is a **hub-assigned** classification for a foreign ref that resolves to a node present in the union but exported without a describable surface — reported, never DRIFT.
- DB: SQLite cannot `ALTER` a `CHECK` constraint in place, so the migration **rebuilds** the `nodes`/`edges` `lifecycle` CHECK to include `external` (table-rebuild pattern via `ensure_schema_migrations`, `SCHEMA_VERSION` bump, additive — existing rows untouched, default still `active`).

### 8. Paradigm-agnostic round-trip (G6 / U1)

`kind`/`edge_kind` are already free-form strings (loader: `node.get("kind", "")`, `edge.get("kind", "")` — no enum). F2's work here is **guarantee + proof**, not a rewrite:

- Audit `federation.py` / `contracts.py` / `linter.py` for any hard-coded DDD kind (`domain`/`service`) assumption on the export/federate/contract path; remove or generalize any found.
- Add round-trip tests with FSD kinds (`page`/`feature`/`entity`/`repository`) asserting zero loss/rejection through `export → federate`.
- Dogfood on Product-B's real FSD mobile graph (G9, anonymized).

---

## Schema & versioning

| Artifact | F1 | F2 | Reason |
|----------|----|----|--------|
| `EXPORT_SCHEMA_VERSION` | 1 | **2** | New `protocol: graphql` contracts + `exposed`/`references`/`exchange` contract fields + optional `landscape` provenance. v1 exports still read (missing fields default). |
| `FEDERATION_SCHEMA_VERSION` | 1 | **2** | `contracts` becomes `list[Contract]` with verdicts; new `ContractVerdict` values. |
| DB `SCHEMA_VERSION` | 3 | **4** | `lifecycle` CHECK rebuilt to include `external`. |

**Backward compatibility (hard requirement):** a v1 export federates without error (AMQP `message_type`-only → `amqp:*:<mt>` key); a graph with no contracts/`landscape`/`external` behaves exactly as F1. All three version bumps are independent and read older inputs.

## Determinism

All new collections (`contracts`, endpoint lists, exposed/reference name sets) are **sorted** before serialization; JSON keys stay `sort_keys=True`. Identical input ⇒ byte-identical `federated.json` (extends F1 invariant; injected `now`/`exported_at` keep tests deterministic).

## Build order (waves — detail in PLAN)

1. **Contract model + protocol-aware `contract_key`** (`contracts.py`, loader) — foundation; refactor F1 reconciliation onto it (no behavior change yet).
2. **AMQP enrichment (G4)** — exchange/routing into the key.
3. **GraphQL SDL (G2/G3)** — `sdl.py` + producer/consumer wiring.
4. **Contract-level verdicts (G5)** — `ContractVerdict`, classify, report/JSON.
5. **`external`/`unmapped` (G7)** — DB migration + verdict suppression.
6. **Nested landscapes (G8)** — `landscape` provenance + scoped matching.
7. **U1 round-trip hardening (G6)** — audit + guards.
8. **Dogfood (G9)** — live mismatch + Product-B FSD round-trip.

Then the standard test → review → tech-writer (README RELEASE GATE) waves.

## Risks & mitigations

| Risk | Mitigation |
|------|------------|
| In-house SDL parser too weak / mis-parses real schemas | Scope to name-presence only; dogfood on the real `schema.graphql`; record unparsed constructs honestly (`exposed: []` + error), never fake-confirm. `graphql-core` is the documented upgrade path. |
| CHECK-constraint rebuild migration corrupts data | Table-rebuild is additive + idempotent + covered by `test_db.py`; existing rows default `active`; run on a copy in tests first. |
| Landscape scoping breaks F1's single-product dogfood | `landscape` defaults to `repo`; a single-product run is one landscape — identical to F1 behavior; explicit regression test. |
| Cross-language `contract_key` mismatch (TS vs backend naming) | Key is the *contract name* both sides write by hand; dogfood proves the real Product-B client ↔ backend names align; mismatches surface as ORPHANED/UNDECLARED (honest), not silent. |
| Scope creep (REST/gRPC/schema-diff pulled in) | Hard non-goals in PRD; presence-based only; REST/gRPC explicitly F3+. |

## Out of scope (→ F3/F4)

REST/OpenAPI + gRPC sources; historical schema-version diffing; CI wiring & PR gates; VitePress visual map; AI-tech-writer-in-CI; SaaS hub; live-server introspection.
