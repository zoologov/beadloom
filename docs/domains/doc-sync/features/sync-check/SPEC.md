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
- **Unchecked accounting** names every node that declares a doc but contributes
  no pair, so a green verdict can never be read as "checked" when it means
  "nothing was looked at".
- **Reference surface drift** (BDL-057 Layer 2) watches a few hand-declared
  overview docs against a coarse interface surface and emits an advisory warning
  when the surface changes.

### Symbol-pair freshness

A node's source files are found first through symbol annotations
(`# beadloom:<kind>=<ref>`) and, when those yield none, through the files the
node's declared `source` **owns** (most-specific-source wins, so a container
never claims a nested node's files). Pairing on annotations alone left any node
whose annotation is not a comment tree-sitter reads — or which declares only
`source:` — with no pairs at all, kind-independent, and a freshness gate with no
pairs reported "clean" for files it never opened (BDL-UX #146).

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
- `sync-check` exits non-zero on symbol-pair staleness; `surface_drift` and the
  unchecked accounting are warnings and never change the exit code.
- An empty `sync_state` is not a clean verdict: the source-coverage and
  doc-coverage phases still run, and any node that declares a doc without
  contributing a pair is listed with the reason it could not be checked.
- The reference baseline survives reindex for an unchanged `watches` set, so a
  drift accrued since the last `sync-update` is still reported.
- **Both sides of a hash comparison are decoded by the same stated rule**
  (`utf-8` + `errors="surrogateescape"`, `_TEXT_CODEC` / `_TEXT_ERRORS`): the
  working tree via `read_text`, the content at a ref via `git show`. Neither
  side consults the image's locale, so a verdict cannot be an artefact of the
  environment — MEASURED before the fix on this repo with `docs/architecture.md`
  unchanged at `HEAD`: an ambient `latin-1` made `sync-check --since` report
  drift in a file nobody touched, and an ambient `ascii` raised an uncaught
  `UnicodeDecodeError` out of a command that runs inside `beadloom ci`.
- A file whose bytes are not UTF-8 still has a digest (the bytes round-trip), so
  one latin-1 source file cannot crash the Gate. `_file_content_at_ref` returns
  `None` for *absent at that ref* and for nothing else: an unreachable `git` is
  not caught into `None`, because that would report drift in an untouched file.

## API

Module `src/beadloom/doc_sync/engine.py`:

- `build_sync_state(conn) -> list[SyncPair]` — record symbol-pair baselines.
- `check_sync(conn, project_root=None) -> list[dict]` — report per-pair
  verdicts, plus source/doc coverage findings.
- `check_sync_since(conn, project_root, ref) -> list[dict]` — diff-based check
  against a git ref.
- `find_unchecked_doc_nodes(conn) -> list[dict]` — nodes that declare a doc but
  contribute no pair, each with the reason (`no_indexed_code`,
  `files_owned_by_nested_nodes`, `no_source`). Advisory.
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
`tests/test_e2e_sync_honest.py`, `tests/test_s2_lying_checks.py`
