<!-- beadloom:badge-start -->
> ✅ **fresh**
> 
> last synced 2026-06-13T22:53:18.143877+00:00 · coverage 100% (`federation`)
> 
> _Validation by Beadloom `doc_sync` — same source as `sync-check`._
<!-- beadloom:badge-end -->

# Federation

Cross-repo architecture federation: stable cross-repo node identity, a `lifecycle` field on nodes and edges, a deterministic satellite **export** artifact, a hub **federate** aggregation that composes the per-repo graphs into one federated graph, and — the F2 moat — a **first-class cross-service contract graph** with contract-level intent-vs-reality verdicts (drift, breaking-change, orphaned-consumer detection) across a multi-paradigm, multi-language, product- and company-scoped microservices landscape.

**Source:** `src/beadloom/graph/federation.py` (identity + export + hub aggregation), `src/beadloom/graph/contracts.py` (first-class `Contract` model, language-neutral `contract_key`, `classify`/`reconcile_contracts`), `src/beadloom/graph/sdl.py` (GraphQL SDL surface extraction), `src/beadloom/graph/loader.py` (foreign-ref parsing, `lifecycle` load, `foreign_edges`, contract-key unification), `src/beadloom/infrastructure/db.py` (`lifecycle` columns, `foreign_edges` table, paradigm-agnostic kinds), `src/beadloom/services/cli.py` (`export` / `federate` commands).

This SPEC covers two delivered slices:

- **F1 — Federation Foundation (BDL-037):** `@repo:` identity, the `lifecycle` field, deterministic `export` (schema v1), and `federate` with three-valued edge-level `EdgeVerdict`s + both-sides AMQP reconciliation. Purely additive.
- **F2 — Cross-Service Contract Graph (BDL-038):** a first-class `Contract` model with a protocol-prefixed, language-neutral `contract_key` (AMQP exchange identity + GraphQL SDL); contract-level `ContractVerdict`s (CONFIRMED / DRIFT / ORPHANED_CONSUMER / UNDECLARED_PRODUCER / BREAKING / EXTERNAL / DEAD / EXPECTED); the `external` / `unmapped` lifecycle (U4); nested product-vs-company landscapes (U5); and paradigm-agnostic node/edge kinds (U1, DDD *and* FSD). Three version bumps — EXPORT `1 → 2`, FEDERATION `1 → 2`, DB SCHEMA `3 → 4` — all backward-compatible: a v1 export still federates, an older DB migrates idempotently.

It remains purely additive — single-repo behavior is unchanged: refs without `@` stay local, nodes/edges without `lifecycle` default to `active`, and an undeclared-landscape single-product run is byte-identical to F1.

> **Contract-level DRIFT note (BEAD-10 review):** contract-level `DRIFT` is intentionally **subsumed** by `ORPHANED_CONSUMER` / `UNDECLARED_PRODUCER` — a missing producer or missing consumer is the precise contract-level signal. `DRIFT` remains the edge-level `EdgeVerdict` (an `active` edge whose target does not resolve).

---

## Specification

### 1. Cross-repo node identity (`@repo:ref_id`)

A graph reference may name a node in *another* repository using the `@<repo>:<ref_id>` form, e.g. `@integration-service:plans`. A plain reference (no leading `@`) is local, exactly as before.

#### `FederatedRef`

Frozen dataclass representing a reference that may point at another repo.

| Field    | Type          | Description                                              |
|----------|---------------|----------------------------------------------------------|
| `repo`   | `str \| None` | `None` for a local ref; the satellite repo name for foreign. |
| `ref_id` | `str`         | The node identifier within `repo`.                       |

| Property      | Returns | Description                                                       |
|---------------|---------|-------------------------------------------------------------------|
| `is_foreign`  | `bool`  | `True` when `repo is not None` (the ref targets another repo).     |
| `qualified`   | `str`   | Canonical form: `@repo:ref_id` (foreign) or `ref_id` (local).      |

#### `parse_ref(raw: str) -> FederatedRef`

Parses a graph ref into a `FederatedRef`:

- `"routing"` → local `FederatedRef(None, "routing")`.
- `"@repo:plans"` → foreign `FederatedRef("repo", "plans")`.
- Malformed `@...` → raises `FederationRefError`.

Only the **first** `:` after the marker separates `repo` from `ref_id`, so a foreign `ref_id` may itself contain colons (`@repo:ns:thing` → `repo="repo"`, `ref_id="ns:thing"`). A plain ref containing a colon and no leading `@` stays local untouched. An empty string raises `FederationRefError`.

#### `FederationRefError`

`ValueError` subclass raised when a `@...` foreign ref is malformed. A leading `@` signals the author *intended* a cross-repo reference, so a broken shape is surfaced as an error (recorded in `GraphLoadResult.errors` by the loader) — never silently accepted as a local ref. Malformed examples: `@:x` (empty repo), `@repo:` (empty ref_id), `@repo` (no separator), `@`.

#### `is_foreign_ref(raw: str) -> bool`

Cheap check: does `raw` start with `@`? Does not validate the shape — use `parse_ref` for that.

#### Foreign edges in the loader

When the loader (`graph/loader.py`) classifies an edge endpoint:

- Both endpoints local → exact original behavior (insert into `edges`, or warn on dangling node).
- A malformed `@...` endpoint → recorded in `GraphLoadResult.errors`; the edge is skipped.
- A foreign endpoint (src or dst) → the edge is **not** inserted into the local `edges` table (its endpoint cannot satisfy the local foreign-key) and is **not** treated as a dangling-node warning. It is persisted in a dedicated `foreign_edges` table (no FK) so the declared cross-repo link survives into the export artifact and resolves/drifts at the hub.

### 2. The `lifecycle` field

Every node and edge carries a `lifecycle` status. It is a first-class SQLite column (not stored in the `extra` JSON), so it is type-checked, SQL-queryable, and visible to the rule engine.

| Value        | Meaning                                                      |
|--------------|--------------------------------------------------------------|
| `active`     | Default. The node/edge is live and real.                     |
| `planned`    | Declared intent; not built yet.                              |
| `deprecated` | On its way out; still present.                               |
| `dead`       | Declared dead; not treated as live.                          |
| `external`   | Present-but-not-ours (e.g. a native bridge); dependents suppress DRIFT (BDL-038 G7). |

Loading rules (`graph/loader.py`):

- Absent `lifecycle:` → defaults to `active`.
- An invalid value is recorded loudly in `GraphLoadResult.errors` and falls back to `active` (never silently dropped).
- `lifecycle` is excluded from the `extra` JSON (no duplication).

Rule-engine awareness (`graph/rule_engine.py`): only `active` edges are counted as "live" for the `no-dependency-cycles` and `architecture-layers` rules. `planned` / `deprecated` / `dead` edges are not counted as live cycle/layer violations. If the `lifecycle` column is absent (an older DB), the engine degrades gracefully and treats all edges as live.

Migration (`infrastructure/db.py`): the `lifecycle TEXT NOT NULL DEFAULT 'active' CHECK(...)` column is added to both `nodes` and `edges`, in the fresh schema and via an idempotent `ALTER TABLE ADD COLUMN` migration. Existing rows default to `active` (no regression). BDL-038 G7 adds `external` to the CHECK on `nodes` / `edges` / `foreign_edges`; since SQLite cannot ALTER a CHECK in place, the migration **rebuilds** each table (table-rebuild pattern, `DB SCHEMA_VERSION` 3 → 4 — additive, idempotent, no data loss, composes with the dropped DDD-only `kind` CHECK).

### 3. `beadloom export` — satellite export artifact

```
beadloom export [--out FILE] [--project DIR]
```

Reads the indexed graph from SQLite (read-only) and emits a deterministic, self-describing JSON artifact that a hub aggregates. With `--out` it writes to a file; otherwise it prints to stdout.

#### Artifact schema (`schema_version: 2`)

```json
{
  "schema_version": 1,
  "repo": "<repo name>",
  "commit_sha": "<git HEAD sha or null>",
  "exported_at": "<ISO-8601 UTC timestamp>",
  "generator": "beadloom <version>",
  "nodes": [
    { "ref_id": "...", "kind": "...", "summary": "...", "lifecycle": "...", "source": "..." }
  ],
  "edges": [
    { "src": "...", "dst": "...", "kind": "...", "lifecycle": "...",
      "contract": { "protocol": "amqp", "source_file": "...", "direction": "...", "message_type": "..." } }
  ]
}
```

- Nodes are sorted by `ref_id`; edges by `(src, dst, kind)`; JSON keys are sorted (`sort_keys=True`, 2-space indent) — so identical graphs serialize **byte-identically** (reviewable diffs).
- The `edges` array unions the local `edges` table **and** the `foreign_edges` table, so declared cross-repo `@repo:` links reach the artifact.
- An edge's optional `contract` metadata (carried under the `contract` key of the edge's `extra` JSON) is surfaced as a top-level `contract` field; edges without it omit the key entirely. Two protocols are carried: AMQP (`protocol: amqp` + `exchange` / `routing_key` / `message_type` / `direction`) and GraphQL (`protocol: graphql` + `schema` + the producer's `exposed` SDL surface / a consumer's `references`). The protocol-prefixed `contract_key` is derived at the hub.

#### Provenance fields (`commit_sha`, `exported_at`)

The hub cannot know a satellite's live HEAD, so the export records its own provenance:

- `repo` — resolved by `resolve_repo_name()`: `.beadloom/config.yml` `repo:` key > git `origin` remote basename > project directory name.
- `commit_sha` — resolved by `current_commit_sha()`: the git HEAD sha, or `null` when the project root is **not** itself the git toplevel (an honest "unknown HEAD" beats leaking an enclosing repo's sha).
- `exported_at` — ISO-8601 UTC timestamp (injected as a parameter for deterministic tests; the CLI passes wall-clock UTC).
- `landscape` (optional, BDL-038 / U5) — resolved by `resolve_landscape()`: `.beadloom/config.yml` `landscape:` key > the resolved repo name. The CLI emits it **only when explicitly configured** (≠ the repo default), so an undeclared-landscape export keeps the F1 wire shape (no `landscape` key). Names the *product* the satellite belongs to; the hub scopes implicit contract matching by `(landscape, contract_key)`.

The CLI exits `1` with an error if the database is not found (`beadloom reindex` first).

#### Public API (`graph/federation.py`)

```python
EXPORT_SCHEMA_VERSION: int  # = 2  (GraphQL SDL `contract` meta on edges; v1 still ingested by federate)

def build_export(conn, *, repo: str, commit_sha: str | None,
                 exported_at: str, generator: str) -> dict[str, object]
def serialize_export(export: dict[str, object]) -> str   # deterministic JSON
def resolve_repo_name(project_root: Path) -> str
def current_commit_sha(project_root: Path) -> str | None
```

### 4. `beadloom federate` — hub aggregation

```
beadloom federate <export1.json> <export2.json> [...] [--project DIR] [--fail-on <csv>]
```

Ingests **≥ 2** satellite export artifacts and composes one federated graph. Writes `.beadloom/federated.json` (deterministic) + `.beadloom/federated.txt` (human-readable report) into the hub project root and echoes the report (plus any DRIFT) to stdout. Fewer than two artifacts, or a file that is not a JSON object, exits `1`.

**Landscape gate — `--fail-on` (BDL-039 / F3).** With `--fail-on`, the run also acts as a CI gate: it **still writes the artifact and prints the report first**, THEN exits `1` if any edge `EdgeVerdict` or contract `ContractVerdict` (matched case-insensitively against the enum value) is in the fail-set — so CI always has `federated.json` to upload even when the gate fails. The failing verdicts (each with its `src → dst` / `contract_key` identity, and for `BREAKING` the missing GraphQL names) are printed to stderr. Exit `0` when clean. A bare `--fail-on` or the token `default` uses the **safe-default fail-set** `breaking,drift,orphaned_consumer,undeclared_producer` (plus the edge-level `undeclared`, the AMQP equivalent of `undeclared_producer`). The pure, testable `gate_failures(fed, fail_on) -> list[GateFailure]` scans the already-computed verdicts and returns deterministically-sorted findings.

**No false gates (principle 3 — a noisy gate gets disabled).** The fail-set **never** includes `external` / `expected` / `dead` / `unmapped` / `confirmed` / `ok` / `cleanup_candidate` (`NEVER_FAIL_VERDICTS`): these are intentional, honest-unknown, or healthy states (`cleanup_candidate` is a warning, not a block). Passing one of them to `--fail-on` is **rejected** with a clear error (exit `2`) so a user cannot arm a false gate. `SAFE_DEFAULT_FAIL_ON` and `NEVER_FAIL_VERDICTS` are disjoint by construction; without `--fail-on`, `federate` is pure reporting (exit `0` regardless of drift).

Aggregation (`aggregate_exports`):

- **Namespaced union.** Every node id is qualified as `@repo:ref_id`. The same `ref_id` in two repos stays distinct.
- **Endpoint resolution.** A local edge endpoint is namespaced under the edge's own repo; a foreign endpoint (`@other:ref`) keeps its own namespace. A foreign target that does not resolve in the union is recorded in `unresolved_refs` (reported, never dropped); the edge is still present.
- **Three-valued intent-vs-reality verdict** assigned to every edge (`EdgeVerdict`), reconciling its declared `lifecycle` against whether its target resolves:

  | `lifecycle` | target present | Verdict             | Meaning                                            |
  |-------------|----------------|---------------------|----------------------------------------------------|
  | `active`    | yes            | `OK`                | Declared and present.                              |
  | `active`    | no             | `DRIFT`             | A real, broken cross-repo dependency (the killer signal). |
  | `planned`   | (either)       | `EXPECTED`          | Intentional — the target is not built yet.         |
  | `deprecated`| yes            | `CLEANUP_CANDIDATE` | The dependency outlived its declared death.        |
  | `deprecated`| no             | `EXPECTED`          | Deprecated and already gone.                       |
  | `dead`      | (either)       | `DEAD`              | Declared dead; not treated as live.                |
  | `external`  | (either)       | `EXTERNAL`          | The edge **or its target node** is declared `external` (present-but-not-ours, e.g. a native bridge) — never DRIFT (BDL-038 G7). |
  | `active`    | yes, undescribed | `UNMAPPED`        | The target **resolves** in the union but is present-without-a-usable-surface (empty summary) — reported honestly, never DRIFT (BDL-038 U4). |
  | —           | —              | `UNDECLARED`        | A present AMQP producer whose `message_type` has no matching consumer across the union (emitting into the void). |

  **`external` vs `unmapped` vs `unresolved_refs` (BDL-038 G7/U4) — three honest categories, never conflated:**
  - `external` — the author *declares* a node present-but-not-ours (`lifecycle: external`, e.g. a native Swift/Kotlin/ObjC++/C++ bridge). The dependent → `EdgeVerdict.EXTERNAL` / `ContractVerdict.EXTERNAL`. Suppresses DRIFT.
  - `unmapped` — a foreign ref that **resolves** to a node present in the union but exported **without a usable surface** (undescribed — empty summary; also covers a present node no satellite describes). The dependent → `EdgeVerdict.UNMAPPED`. Reported, never DRIFT, and **not** an unresolved ref (it resolved).
  - `unresolved_refs` — a genuinely-**absent** foreign target (resolved to nothing). Still `DRIFT` (active) and recorded in `unresolved_refs`. Distinct from `unmapped` (present).

- **First-class contract reconciliation + verdicts** (`_reconcile_contracts` → `contracts.reconcile_contracts` + `classify`; BDL-038 / F2). AMQP **and** GraphQL contract edges are grouped by protocol-prefixed `contract_key` across the union into first-class `Contract`s, each assigned a **contract-level** `ContractVerdict` (intent-vs-reality — the F2 moat). The most-significant declared edge `lifecycle` (`external` > `dead` > `deprecated` > `planned` > `active`) folds onto the contract; lifecycle intent dominates the shape check. Surfaced in `FederatedGraph.contracts` (sorted by `contract_key` for deterministic diffs; F1's flat `{message_type, directions, repos, confirmed}` keys kept as a subset).

  | Condition | `ContractVerdict` | Meaning |
  |-----------|-------------------|---------|
  | lifecycle `external` | `EXTERNAL` | Target declared present-but-not-ours (a native bridge); the `external` edge `lifecycle` folds onto the contract (`external` is the most-significant lifecycle) → `EXTERNAL`, never DRIFT (BDL-038 G7). |
  | lifecycle `dead` | `DEAD` | Declared dead; not live. |
  | lifecycle `planned` / `deprecated` | `EXPECTED` | Intentional — not built yet / retiring. Not drift. |
  | producers ∧ consumers; GraphQL `references ⊄ exposed` | `BREAKING` | A consumer relies on a name the producer's current SDL no longer exposes — caught before it ships (presence-based, not version-diff). |
  | producers ∧ consumers (compatible) | `CONFIRMED` | Both sides present and compatible (F1's "confirmed both-sides"). |
  | consumers, no producers | `ORPHANED_CONSUMER` | Consumes a contract nobody produces (F1 "one-sided", consumer side). |
  | producers, no consumers | `UNDECLARED_PRODUCER` | Produces a contract nobody consumes (F1 "one-sided", producer side). |

  The contract-level `UNDECLARED_PRODUCER` is **complementary** to F1's edge-level `EdgeVerdict.UNDECLARED` (an additional projection over the same fact, not a replacement); both stay intact and never contradict. For GraphQL, a contract dict also carries `exposed` / `references` / `missing` (the names that triggered `BREAKING`).
- **Landscape scoping — product vs company (BDL-038 / U5).** An optional `landscape` provenance (resolved like `repo`: config `landscape:` key > repo name) names the *product* a satellite belongs to. `reconcile_contracts` groups by `(landscape, contract_key)`, so **implicit** same-key matching is scoped *within* a landscape: two unrelated products that happen to share a coincidental `message_type` / schema name reconcile in separate groups → **zero** mutual DRIFT / UNDECLARED / false-CONFIRMED. A **genuine** cross-product contract is declared with an explicit `@otherrepo:<ref>` consumer edge — its `contract_key` is promoted *cross-landscape* (one shared, landscape-agnostic group via `cross_landscape_keys` / `edge_group_key`) and resolves with a both-sides verdict regardless of landscape. An export with no declared landscape (or one equal to its repo) shares a single default group, so a single-product run is byte-identical to F1. The hub's edge-level UNDECLARED sweep (`_mark_undeclared`) uses the same `(landscape, contract_key)` group scope, so a producer is UNDECLARED only when *its own* landscape has no consumer (honest per-product signal, never silenced by an unrelated product's coincidental consumer). `federate` composes either one product-landscape (all satellites share/omit a landscape) or a company-landscape (several); the text report groups satellites by landscape with a `product`/`company`-landscape label.
- **Per-satellite staleness** (`_repo_provenance`). For each satellite: `repo`, `commit_sha`, `exported_at`, `schema_version`, and `age_seconds` = `now − exported_at` in whole seconds. An unparseable/missing timestamp yields `None` (honest unknown); a missing `commit_sha` is reported, never faked. `now` is injectable for deterministic tests; the CLI passes wall-clock UTC.

#### `FederatedGraph`

| Field             | Type                       | Description                                              |
|-------------------|----------------------------|----------------------------------------------------------|
| `nodes`           | `list[dict]`               | Namespaced node union (each carries `ref_id` + `repo`).  |
| `edges`           | `list[dict]`               | Edge union with resolved endpoints + `verdict`.          |
| `repos`           | `list[dict]`               | Per-satellite provenance + staleness + `landscape` (defaults to `repo` when undeclared). |
| `unresolved_refs` | `list[str]`                | Foreign targets that did not resolve (sorted, deduped).  |
| `contracts`       | `list[dict]`               | First-class AMQP + GraphQL contracts with a contract-level `ContractVerdict` (sorted by `contract_key`). |

#### `EdgeVerdict` (enum)

`OK` · `DRIFT` · `EXPECTED` · `CLEANUP_CANDIDATE` · `UNDECLARED` · `DEAD` · `EXTERNAL` · `UNMAPPED` (serialized as the lowercase value). Edge-level; complementary to the contract-level `ContractVerdict` (see `contracts.py`). `EXTERNAL` / `UNMAPPED` (BDL-038 G7/U4) both suppress DRIFT.

#### Enforcement (F3 / BDL-039)

`gate_failures(fed, fail_on) -> list[GateFailure]` is a pure, deterministic
function over an already-aggregated `FederatedGraph`: it scans each edge
`EdgeVerdict` and each contract `ContractVerdict` (matched case-insensitively
against the enum value) and returns a sorted `GateFailure` per verdict in
`fail_on` (`kind` = `"edge"`/`"contract"`, `identity` = `src --> dst` /
`contract_key`, `verdict`, and `missing` GraphQL names for a `BREAKING`). It is
reused by both `federate --fail-on` and the `beadloom ci` orchestrator, so the
gate is testable without the CLI.

Two module-level frozensets bound the gate (principle 3 — a noisy gate gets
disabled):

- `SAFE_DEFAULT_FAIL_ON` = `breaking, drift, orphaned_consumer,
  undeclared_producer, undeclared` — the set a bare `--fail-on` / `default`
  arms (the edge-level `undeclared` is the AMQP equivalent of
  `undeclared_producer`).
- `NEVER_FAIL_VERDICTS` = `external, expected, dead, unmapped, confirmed, ok,
  cleanup_candidate` — intentional, honest-unknown, or healthy states. These can
  never enter a fail-set; passing one to `--fail-on` is rejected (exit `2`).
  The two sets are disjoint by construction.

`federate --fail-on` and `beadloom ci` **write the federated artifact (and print
the report) before exiting non-zero**, so CI always has `federated.json` to
upload even when the gate blocks. `beadloom ci` composes the landscape gate as
its final step (after reindex → lint → sync-check → config-check → doctor); see
`docs/guides/ci-setup.md`.

#### Public API (`graph/federation.py`)

```python
FEDERATION_SCHEMA_VERSION: int  # = 2  (independent of EXPORT_SCHEMA_VERSION = 2)

SAFE_DEFAULT_FAIL_ON: frozenset[str]   # bare --fail-on / "default" arms this set
NEVER_FAIL_VERDICTS: frozenset[str]    # never gated (rejected by --fail-on)

class EdgeVerdict(enum.Enum): ...
@dataclass
class FederatedGraph: ...
@dataclass(frozen=True)
class GateFailure: ...   # kind, identity, verdict, missing

def aggregate_exports(exports: list[dict], *, now: str | None = None) -> FederatedGraph
def serialize_federation(fed: FederatedGraph) -> str        # deterministic JSON
def render_federation_report(fed: FederatedGraph) -> str    # human-readable text
def gate_failures(fed: FederatedGraph, fail_on: set[str]) -> list[GateFailure]
```

The federated JSON envelope: `{ schema_version, repos, nodes, edges, contracts, unresolved_refs }` (sorted keys). The text report lists the satellites (with sha + age), the edge-verdict counts, an explicit DRIFT list, the contract-verdict counts plus explicit `BREAKING` / `DRIFT` / `ORPHANED_CONSUMER` / `UNDECLARED_PRODUCER` call-outs (with the missing GraphQL names), and any unresolved foreign refs.

**Schema v2 (BDL-038 / BEAD-04):** each `contracts` entry gains a contract-level `verdict` (`ContractVerdict`) plus `protocol` / `contract_key` / `lifecycle` and, for GraphQL, `exposed` / `references` / `missing`. F1's flat keys are kept as a subset. The bump is on the hub OUTPUT only — `federate` still ingests v1 AND v2 satellite *exports* (`FEDERATION_SCHEMA_VERSION` and `EXPORT_SCHEMA_VERSION` are independent).

---

## Invariants

- Single-repo behavior is unchanged: a ref without `@` is local; a node/edge without `lifecycle` defaults to `active`.
- A malformed `@...` ref is always surfaced (parse error / `GraphLoadResult.errors`), never silently accepted.
- Export and federated artifacts are deterministic: sorted node/edge arrays + sorted JSON keys → byte-identical output for identical input (injected `exported_at` / `now`).
- A foreign ref that does not resolve at the hub is recorded in `unresolved_refs`, not dropped.
- An `external` target (declared) and an `unmapped` target (present-but-undescribed) never DRIFT, and `unmapped` is kept distinct from `unresolved_refs` (present vs absent) — honest unknowns, never faked (BDL-038 G7/U4).
- `commit_sha` is reported honestly: `null` when it cannot be verified, never an unrelated repo's HEAD.
- `EXPORT_SCHEMA_VERSION` and `FEDERATION_SCHEMA_VERSION` are independent; each is bumped only on a breaking shape change. F2 bumps EXPORT `1 → 2`, FEDERATION `1 → 2`, DB SCHEMA `3 → 4` — all backward-compatible: `federate` ingests v1 **and** v2 exports, and an older DB migrates idempotently (no data loss).
- `contract_key` is language-neutral: contracts resolve on the contract name (AMQP exchange/routing/message_type, GraphQL schema), never a code symbol — so a cross-language edge (TS client ↔ backend) reconciles across the boundary.
- Contract-level `DRIFT` is subsumed by `ORPHANED_CONSUMER` / `UNDECLARED_PRODUCER`; `DRIFT` is the edge-level `EdgeVerdict` only.

---

## Constraints & non-goals (F2 delivered)

**Delivered in F2 (BDL-038):**

- **AMQP + GraphQL contracts.** AMQP reconciles on full exchange identity (`amqp:<exchange>/<routing>:<mt>`, not just `message_type`); GraphQL reconciles on `graphql:<schema>` with a **presence-based** `BREAKING` check (consumer `references ⊄` producer `exposed` SDL surface — caught before it ships, not a version diff).
- **Paradigm-agnostic.** Arbitrary node/edge `kind` round-trips through `export`/`federate` without loss or rejection (DDD `domain/service` *and* FSD `page/feature/entity/repository`; the DDD-only DB CHECK was dropped, U1).
- **Nested landscapes.** A single product-landscape *or* a company-landscape composing several products; contract-less products never cross-pollute verdicts (U5).
- **`external` / `unmapped` lifecycle.** Present-but-not-ours (native bridges) and present-but-undescribed nodes are honest categories, never silent DRIFT (U4).

**Still non-goals (deferred):**

- **REST / OpenAPI and gRPC contracts** (lowest priority — runtime-generated, no static source files; future F-phase).
- **CI gating** — **delivered in F3 (BDL-039):** the landscape gate (`federate --fail-on`), the unified `beadloom ci` orchestrator (reindex → lint → sync-check → config-check → doctor → optional federate gate), and a reusable composite GitHub Action + GitLab template, dogfooded on Beadloom's own CI. The **pull-based hub** plumbing (SHA-tagged export publishing + fetch) is a documented pattern run by the satellites' ops — no SaaS hub, no satellite auto-bootstrap is Beadloom-built. See `docs/guides/ci-setup.md`.
- **Visual landscape map** — **delivered in F4 (BDL-040):** the `federate` hub artifact (`federated.json`) is consumed by `beadloom docs site --federated` to render the 🌟 cross-repo landscape map (a clickable Mermaid diagram of the contract graph, edges labelled by their `ContractVerdict`/`EdgeVerdict`, a health overlay) in the published VitePress knowledge base. The map carries the hub verdicts verbatim — Beadloom produces, VitePress renders. A richer JS graph library (Cytoscape / D3) remains a follow-up. See `docs/guides/vitepress-site.md`. No semantic layer yet.
- Hub needs **≥ 2** satellite exports.

---

## Testing

Test files: `tests/test_graph_federation.py` (`FederatedRef` + `parse_ref` local/foreign/malformed), `tests/test_graph_contracts.py` (first-class `Contract`, protocol-prefixed `contract_key`, `classify` truth table incl. GraphQL `BREAKING`, lifecycle folding, landscape-scoped `reconcile_contracts`), `tests/test_graph_sdl.py` (GraphQL SDL surface extraction — `exposed` / `references`), `tests/test_graph_loader.py` (foreign-edge recording, `lifecycle` load/default/invalid, contract-key unification), `tests/test_lifecycle_rules.py` (cycle/layer rule lifecycle-awareness), `tests/test_db.py` (`lifecycle` column + `foreign_edges` migrations + paradigm-agnostic kinds + schema 3→4 rebuild, additive + idempotent), `tests/test_export.py` (envelope fields, sorting, lifecycle + AMQP/GraphQL contract carry, deterministic byte-identical output, `resolve_repo_name` precedence, CLI stdout/`--out`/no-db error), `tests/test_federate.py` (namespacing, foreign-ref resolution + unresolved reporting, every `EdgeVerdict`, both-sides confirmed vs one-sided, contract-level verdicts, staleness incl. unknown sha / unparseable date, serialization determinism, report content, CLI ≥2 requirement + DRIFT in stdout), `tests/test_federate_f2_gate.py` (contract-level verdicts + nested-landscape scoping + `external`/`unmapped` integration), `tests/test_federate_dogfood_amqp.py` + `tests/test_federate_roundtrip_db.py` (real YAML → reindex → export → federate path through the DB).

### Key cases

- **Local-only no-regression.** A graph with only plain refs and no `lifecycle:` loads exactly as before; all defaults are `active`.
- **Foreign edge survives to the artifact.** A declared `@repo:` edge is persisted in `foreign_edges` and unioned into `build_export`'s `edges`.
- **All verdicts.** Each `lifecycle × target-present` combination yields the documented `EdgeVerdict`; a producer with no consumer becomes `UNDECLARED`.
- **Both-sides confirmation.** Matching `produces` + `consumes` for one `message_type` across two satellites → `confirmed: true`.
- **Staleness honesty.** Missing `commit_sha` and unparseable `exported_at` are reported as unknown, not faked.
