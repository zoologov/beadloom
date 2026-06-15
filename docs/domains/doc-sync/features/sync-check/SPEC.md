# Sync Check

The doc-code synchronization engine for the doc-sync domain.

**Source:** `src/beadloom/doc_sync/engine.py`

---

## Specification

### Purpose

Track whether each documentation file is still in sync with the code it
describes, and warn when a high-traffic overview doc may have drifted from a
broad interface surface. Two layers cooperate without interfering:

- **Symbol-pair freshness** pairs a node's `docs:` entries with the source files
  attributed to that node, computes a freshness signal from the code
  `symbols_hash` (plus git state), and reports each pair as `ok` or stale.
- **Reference surface drift** (BDL-057 Layer 2) watches a few hand-declared
  overview docs against a coarse interface surface and emits an advisory warning
  when the surface changes.

### Symbol-pair freshness

`build_sync_state` records the baseline doc and symbol hashes for each pair;
`check_sync` re-reads files from disk to detect changes since the last sync,
independently of reindex, and also runs source-coverage and doc-coverage checks
to catch untracked files and missing module mentions. `mark_synced` (and
`mark_synced_by_ref`) re-baselines a pair once its doc is brought up to date.
`check_sync_since` compares against a git ref for diff-based checks.

### Reference surface drift

A reference doc opts in with an in-doc annotation declaring a coarse `watches:`
surface — `<!-- beadloom:watches=cli,graph,flow.yml -->`. On reindex,
`build_reference_state` records the aggregate hash of the declared surfaces in a
separate `reference_state` table; the baseline is preserved across reindex for a
doc already tracked with the same `watches` set, so a routine reindex after a
surface change cannot silently re-baseline and swallow the warning.
`check_reference_drift` recomputes the current aggregate hash and reports
`status='surface_drift'` with `reason='surface_drift'` and **severity =
warning** when it differs. `mark_reference_synced` re-baselines a reference doc
(via `sync-update <doc>`), clearing the drift. The signatures themselves live in
`surface.py` (coarse identity sets, not file content).

## Invariants

- Baselining is explicit (`mark_synced` / `sync-update`); the engine never
  silently marks a stale doc fresh.
- Symbol-pair `sync_state` logic and its reason-masking / fixpoint behaviour are
  untouched by Layer 2, which lives in its own `reference_state` table and is
  additive in output.
- `sync-check` exits non-zero on symbol-pair staleness; `surface_drift` is a
  warning and never changes the exit code.
- The reference baseline survives reindex for an unchanged `watches` set, so a
  drift accrued since the last `sync-update` is still reported.

## API

Module `src/beadloom/doc_sync/engine.py`:

- `build_sync_state(conn) -> list[SyncPair]` — record symbol-pair baselines.
- `check_sync(conn, project_root=None) -> list[dict]` — report per-pair
  verdicts, plus source/doc coverage findings.
- `check_sync_since(conn, project_root, ref) -> list[dict]` — diff-based check
  against a git ref.
- `mark_synced(...)` / `mark_synced_by_ref(...)` — re-baseline a symbol pair.
- `build_reference_state(conn, project_root) -> int` — baseline every
  `watches`-annotated reference doc; returns the count recorded.
- `check_reference_drift(conn, project_root) -> list[dict]` — recompute and
  report reference surface drift (warning severity).
- `mark_reference_synced(conn, doc_path, project_root, *, all_docs=False) -> int`
  — re-baseline a reference doc, clearing its drift.

Module `src/beadloom/doc_sync/surface.py`:

- `parse_watches(text) -> list[str] | None` — parse the `watches` annotation.
- `cli_signature()` / `graph_signature(conn)` / `flow_signature(project_root)`
  — coarse identity signatures for the watched surfaces.
- `aggregate_hash(watches, conn, project_root) -> str` — SHA-256 of the
  declared surfaces' signatures, concatenated in declared order.

## Testing

Tests: `tests/test_sync_engine.py`, `tests/test_sync_since.py`,
`tests/test_surface.py`, `tests/test_reference_drift.py`,
`tests/test_cli_reference_drift.py`,
`tests/test_integration_reference_freshness.py`,
`tests/test_e2e_sync_honest.py`
