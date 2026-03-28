# Federation

Cross-repo architecture federation: stable cross-repo node identity, a `lifecycle` field on nodes and edges, a deterministic satellite **export** artifact, and a hub **federate** aggregation that composes the per-repo graphs into one federated graph with three-valued intent-vs-reality drift detection and per-satellite staleness.

**Source:** `src/beadloom/graph/federation.py` (identity + export + hub aggregation), `src/beadloom/graph/loader.py` (foreign-ref parsing, `lifecycle` load, `foreign_edges`), `src/beadloom/infrastructure/db.py` (`lifecycle` columns, `foreign_edges` table), `src/beadloom/services/cli.py` (`export` / `federate` commands).

This is the F1 (Federation Foundation) thin slice (BDL-037). It is purely additive — single-repo behavior is unchanged: refs without `@` stay local, nodes/edges without `lifecycle` default to `active`.

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

Loading rules (`graph/loader.py`):

- Absent `lifecycle:` → defaults to `active`.
- An invalid value is recorded loudly in `GraphLoadResult.errors` and falls back to `active` (never silently dropped).
- `lifecycle` is excluded from the `extra` JSON (no duplication).

Rule-engine awareness (`graph/rule_engine.py`): only `active` edges are counted as "live" for the `no-dependency-cycles` and `architecture-layers` rules. `planned` / `deprecated` / `dead` edges are not counted as live cycle/layer violations. If the `lifecycle` column is absent (an older DB), the engine degrades gracefully and treats all edges as live.

Migration (`infrastructure/db.py`): the `lifecycle TEXT NOT NULL DEFAULT 'active' CHECK(...)` column is added to both `nodes` and `edges`, in the fresh schema and via an idempotent `ALTER TABLE ADD COLUMN` migration. Existing rows default to `active` (no regression).

### 3. `beadloom export` — satellite export artifact

```
beadloom export [--out FILE] [--project DIR]
```

Reads the indexed graph from SQLite (read-only) and emits a deterministic, self-describing JSON artifact that a hub aggregates. With `--out` it writes to a file; otherwise it prints to stdout.

#### Artifact schema (`schema_version: 1`)

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
- An edge's optional AMQP `contract` metadata (carried under the `contract` key of the edge's `extra` JSON) is surfaced as a top-level `contract` field; edges without it omit the key entirely.

#### Provenance fields (`commit_sha`, `exported_at`)

The hub cannot know a satellite's live HEAD, so the export records its own provenance:

- `repo` — resolved by `resolve_repo_name()`: `.beadloom/config.yml` `repo:` key > git `origin` remote basename > project directory name.
- `commit_sha` — resolved by `current_commit_sha()`: the git HEAD sha, or `null` when the project root is **not** itself the git toplevel (an honest "unknown HEAD" beats leaking an enclosing repo's sha).
- `exported_at` — ISO-8601 UTC timestamp (injected as a parameter for deterministic tests; the CLI passes wall-clock UTC).

The CLI exits `1` with an error if the database is not found (`beadloom reindex` first).

#### Public API (`graph/federation.py`)

```python
EXPORT_SCHEMA_VERSION: int  # = 1

def build_export(conn, *, repo: str, commit_sha: str | None,
                 exported_at: str, generator: str) -> dict[str, object]
def serialize_export(export: dict[str, object]) -> str   # deterministic JSON
def resolve_repo_name(project_root: Path) -> str
def current_commit_sha(project_root: Path) -> str | None
```

### 4. `beadloom federate` — hub aggregation

```
beadloom federate <export1.json> <export2.json> [...] [--project DIR]
```

Ingests **≥ 2** satellite export artifacts and composes one federated graph. Writes `.beadloom/federated.json` (deterministic) + `.beadloom/federated.txt` (human-readable report) into the hub project root and echoes the report (plus any DRIFT) to stdout. Fewer than two artifacts, or a file that is not a JSON object, exits `1`.

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
  | —           | —              | `UNDECLARED`        | A present AMQP producer whose `message_type` has no matching consumer across the union (emitting into the void). |

- **Both-sides AMQP contract reconciliation** (`_reconcile_contracts`). AMQP contract edges (`contract.protocol == "amqp"`) are grouped by `message_type` across the union. A contract is **confirmed** when both a `produces` and a `consumes` direction exist for that message type; otherwise it is **one-sided**. Surfaced in `FederatedGraph.contracts`.
- **Per-satellite staleness** (`_repo_provenance`). For each satellite: `repo`, `commit_sha`, `exported_at`, `schema_version`, and `age_seconds` = `now − exported_at` in whole seconds. An unparseable/missing timestamp yields `None` (honest unknown); a missing `commit_sha` is reported, never faked. `now` is injectable for deterministic tests; the CLI passes wall-clock UTC.

#### `FederatedGraph`

| Field             | Type                       | Description                                              |
|-------------------|----------------------------|----------------------------------------------------------|
| `nodes`           | `list[dict]`               | Namespaced node union (each carries `ref_id` + `repo`).  |
| `edges`           | `list[dict]`               | Edge union with resolved endpoints + `verdict`.          |
| `repos`           | `list[dict]`               | Per-satellite provenance + staleness.                    |
| `unresolved_refs` | `list[str]`                | Foreign targets that did not resolve (sorted, deduped).  |
| `contracts`       | `list[dict]`               | AMQP reconciliation (confirmed both-sides vs one-sided). |

#### `EdgeVerdict` (enum)

`OK` · `DRIFT` · `EXPECTED` · `CLEANUP_CANDIDATE` · `UNDECLARED` · `DEAD` (serialized as the lowercase value).

#### Public API (`graph/federation.py`)

```python
FEDERATION_SCHEMA_VERSION: int  # = 1

class EdgeVerdict(enum.Enum): ...
@dataclass
class FederatedGraph: ...

def aggregate_exports(exports: list[dict], *, now: str | None = None) -> FederatedGraph
def serialize_federation(fed: FederatedGraph) -> str        # deterministic JSON
def render_federation_report(fed: FederatedGraph) -> str    # human-readable text
```

The federated JSON envelope: `{ schema_version, repos, nodes, edges, contracts, unresolved_refs }` (sorted keys). The text report lists the satellites (with sha + age), the edge-verdict counts, an explicit DRIFT list, the AMQP contracts (confirmed/one-sided), and any unresolved foreign refs.

---

## Invariants

- Single-repo behavior is unchanged: a ref without `@` is local; a node/edge without `lifecycle` defaults to `active`.
- A malformed `@...` ref is always surfaced (parse error / `GraphLoadResult.errors`), never silently accepted.
- Export and federated artifacts are deterministic: sorted node/edge arrays + sorted JSON keys → byte-identical output for identical input (injected `exported_at` / `now`).
- A foreign ref that does not resolve at the hub is recorded in `unresolved_refs`, not dropped.
- `commit_sha` is reported honestly: `null` when it cannot be verified, never an unrelated repo's HEAD.
- `EXPORT_SCHEMA_VERSION` and `FEDERATION_SCHEMA_VERSION` are independent; each is bumped only on a breaking shape change.

---

## Constraints & non-goals (F1 thin slice)

- **AMQP contracts only.** Contract reconciliation matches purely on `message_type` (queue/exchange identity matching deferred to F2).
- **Manual aggregation.** `federate` is run by hand on collected export files; no CI wiring, no SaaS hub, no satellite auto-bootstrap.
- No VitePress / visual landscape map (F4), no semantic layer.
- Hub needs **≥ 2** satellite exports.

---

## Testing

Test files: `tests/test_graph_federation.py` (`FederatedRef` + `parse_ref` local/foreign/malformed), `tests/test_graph_loader.py` (foreign-edge recording, `lifecycle` load/default/invalid), `tests/test_lifecycle_rules.py` (cycle/layer rule lifecycle-awareness), `tests/test_db.py` (`lifecycle` column + `foreign_edges` migrations, additive + idempotent), `tests/test_export.py` (envelope fields, sorting, lifecycle + contract carry, deterministic byte-identical output, `resolve_repo_name` precedence, CLI stdout/`--out`/no-db error), `tests/test_federate.py` (namespacing, foreign-ref resolution + unresolved reporting, every `EdgeVerdict`, both-sides confirmed vs one-sided, staleness incl. unknown sha / unparseable date, serialization determinism, report content, CLI ≥2 requirement + DRIFT in stdout), `tests/test_federate_roundtrip_db.py` (real YAML → reindex → export → federate path through the DB).

### Key cases

- **Local-only no-regression.** A graph with only plain refs and no `lifecycle:` loads exactly as before; all defaults are `active`.
- **Foreign edge survives to the artifact.** A declared `@repo:` edge is persisted in `foreign_edges` and unioned into `build_export`'s `edges`.
- **All verdicts.** Each `lifecycle × target-present` combination yields the documented `EdgeVerdict`; a producer with no consumer becomes `UNDECLARED`.
- **Both-sides confirmation.** Matching `produces` + `consumes` for one `message_type` across two satellites → `confirmed: true`.
- **Staleness honesty.** Missing `commit_sha` and unparseable `exported_at` are reported as unknown, not faked.
