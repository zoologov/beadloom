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
  `symbols_hash` (plus git state), and reports each pair with one of four
  verdicts — `ok`, `stale`, `missing`, `unverified`.
- **The declared surface** is checked against the tree, so a doc the graph names
  and the tree does not hold is a failure rather than one less thing to check.
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

The owned-file fallback reads **`file_index`**, not `code_symbols`
(BDL-061.50). Keyed on symbols, the #146 fallback carried the very blindness it
was written to close: a module holding no top-level `def`/`class` — a pure
re-export facade — has no symbol row, so it was unreachable through BOTH the
annotation path and the fallback. On this repository that module was
`application/graph_reads.py`, 75 lines and fully indexed, and `sync-check`
reported its node as unchecked with the reason `no_indexed_code`, sending the
reader to look for code the index already held (review `.7` MAJOR 3). A file
with no symbol is still a file whose content can change under a doc.

Because a node's owned files are now read from `file_index`, a full `reindex` —
which drops every table first — populates `file_index` **before** it builds
`sync_state`, not at the end of the run. Populated after, the very first build
of a fresh index saw an empty table and produced those pairs only on the SECOND
reindex: a checker whose input arrives after it runs reports clean because there
was nothing there.

`build_sync_state` records the baseline doc and symbol hashes for each pair;
`check_sync` re-reads files from disk to detect changes since the last sync,
independently of reindex, and also runs source-coverage and doc-coverage checks
to catch untracked files and missing module mentions. `mark_synced` (and
`mark_synced_by_ref`) re-baselines a pair once its doc is brought up to date.
`check_sync_since` compares against a git ref for diff-based checks.

### The four verdicts — unverifiable is not clean

`ok` and `stale` are outcomes of a comparison that HAPPENED. The other two are
states in which the checker cannot know, and they exist because they used to
print `ok`:

| Verdict | Reason | Meaning | Exit |
|---|---|---|---|
| `ok` | `ok` | compared against a baseline and unchanged | 0 |
| `stale` | `hash_changed`, `symbols_changed`, `hash_changed_since_head`, `untracked_files`, `missing_modules` | compared and drifted | 2 |
| `missing` | `doc_missing`, `code_missing`, `declared_doc_missing` | the thing to check is not there | 2 |
| `unverified` | `no_baseline` | there was nothing to compare against | 0, reported by name |

Every result also carries `baseline` — `index`, `git:HEAD` or `none` — so a green
result says what it was green against (BDL-UX #175).

`missing` blocks. Deleting a document was the cheapest way to satisfy a gate
whose whole promise is that docs stay current: the pair simply stopped existing
and every count still read fresh (BDL-UX #174, measured `275 → 269 pair(s)
fresh`, `beadloom ci` exit 0). The pair-level check catches a doc deleted since
the last index; `declared_doc_missing` catches it after a reindex, because the
declaration lives in the committed graph YAML and a deleted file cannot remove
it.

`unverified` does not block, and is never counted as fresh. `beadloom ci` prints
the sync-check step as **WARN** with the count, rather than `PASS`.

### Where the baseline lives

**Not in the database.** `.beadloom/beadloom.db` is a derived cache: git-ignored,
per-machine, dropped by every rebuild and absent on every fresh CI checkout. A
baseline kept only there is destroyed by the act that most needs it — a rebuild
records the tree it is indexing AS the baseline, and nothing can be stale
relative to a baseline created a second ago (BDL-UX #175).

Two baselines live outside it, and both are committed:

1. **Freshness — git.** Each pair's stored baseline carries its provenance
   (`baseline_source`): `index_build` (copied from the tree at build time, worth
   nothing on its own), `carried` (inherited from an earlier index generation),
   or `attested` (`sync-update`, or an observed doc edit). A pair whose baseline
   is `index_build` and which would otherwise read `ok` is corroborated against
   git — code that differs from `HEAD` while its doc does not is drift the
   rebuild absorbed. Where git cannot answer (no repository, no commit, no git),
   the pair is `unverified`.
   Provenance is carried verbatim across a reindex and never promoted: a
   fabricated baseline does not become earned by being copied.
2. **Surface size — `.beadloom/sync-surface.json`**, committed. It records how
   many pairs and declared docs there were, so a run whose count FELL can say so
   instead of printing a smaller number. Written only by
   `sync-check --record-surface`: a check that silently re-records the number it
   is checking against re-attests without evidence (BDL-UX #163).

The database still holds the working baseline and stays the fast path; it is a
cache of a fact recorded elsewhere, not the record.

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

> **`--check` does not hold on this path (BDL-UX #189).** In
> `services/commands/docsync.py` the reference-doc branch is reached *before* the
> `check_only` guard, so `beadloom sync-update <doc-path> --check` re-baselines
> the doc and prints `Re-baselined reference doc <path>`. Measured: the drift
> count fell from 7 to 6 on a run whose flag asked for a report. `--check` is
> honoured only for symbol pairs (`sync-update <ref-id> --check`).

## Invariants

- Baselining is explicit (`mark_synced` / `sync-update`); the engine never
  silently marks a stale doc fresh.
- Symbol-pair `sync_state` logic and its reason-masking / fixpoint behaviour are
  untouched by Layer 2, which lives in its own `reference_state` table and is
  additive in output.
- `sync-check` exits non-zero on symbol-pair staleness AND on `missing`;
  `surface_drift`, `unverified` and the unchecked accounting are warnings and
  never change the exit code.
- A pair reads `ok` only when a comparison happened. Nothing that was not
  checked prints the word a checked pair prints.
- A declared doc that is not on disk fails, whether or not a reindex has
  removed its pairs.
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

### What a green result proves, and what it still does not

Both gaps recorded here previously — a rebuilt index reporting every pair fresh
(BDL-UX #175) and a missing file reading `ok` (BDL-UX #174) — are CLOSED by the
four verdicts and the git corroboration above. What remains true and is stated
rather than left to be discovered:

- The git leg compares the working tree against `HEAD`. It catches drift the
  rebuild absorbed, including uncommitted work; it does not judge whether a doc
  committed long ago still describes its code. That question is answered by
  `--since <ref>` (which the CI harness passes on a fresh checkout) and by the
  carried index baseline on a machine that has one.
- A project that is not a git repository and has just been indexed has no
  baseline at all. It reports `unverified` and says so; `sync-update` is the way
  back to a checkable state.

## API

Module `src/beadloom/doc_sync/engine.py`:

- `build_sync_state(conn) -> list[SyncPair]` — record symbol-pair baselines.
- `check_sync(conn, project_root=None) -> list[dict]` — report per-pair
  verdicts, plus source/doc coverage findings.
- `check_sync_since(conn, project_root, ref) -> list[dict]` — diff-based check
  against a git ref.
- `find_unchecked_doc_nodes(conn) -> list[dict]` — nodes that declare a doc but
  contribute no pair, each with the reason. Advisory. Three reasons, all asked
  of `file_index` since BDL-061.50 so that each is TRUE of the index rather than
  of the symbol table:
  - `no_source` — the node declares no `source` at all.
  - `files_owned_by_nested_nodes` — files are indexed under it, but every one
    belongs to a more specific node. Nothing to do.
  - `no_indexed_code` — the index holds no code file under the declared source.
    Index the code (or check the path: a `source` naming no path on disk is
    reported by `reindex` as a warning).
- `STATUS_OK` / `STATUS_STALE` / `STATUS_MISSING` / `STATUS_UNVERIFIED`,
  `BLOCKING_STATUSES`, `BASELINE_INDEX` / `BASELINE_GIT` / `BASELINE_NONE`,
  `BASELINE_SOURCE_INDEX_BUILD` / `_CARRIED` / `_ATTESTED` — the verdict and
  baseline vocabulary, owned by the domain that interprets it.
- `mark_synced(...)` / `mark_synced_by_ref(...)` — re-baseline a symbol pair.
- `build_reference_state(conn, project_root) -> int` — baseline every
  `watches`-annotated reference doc; returns the count recorded.
- `check_reference_drift(conn, project_root) -> list[dict]` — recompute and
  report reference surface drift (warning severity).
- `mark_reference_synced(conn, doc_path, project_root, *, all_docs=False) -> int`
  — re-baseline a reference doc, clearing its drift.

Module `src/beadloom/doc_sync/declared_docs.py` — the declared surface vs disk:

- `count_declared_docs(conn) -> int` — how many docs the graph declares.
- `find_missing_declared_docs(conn, project_root) -> list[dict]` — declarations
  the tree no longer satisfies (re-exported from `engine`).

Module `src/beadloom/doc_sync/git_baseline.py` — the baseline that cannot be lost:

- `changed_paths(project_root) -> frozenset[str] | None` — project-relative paths
  differing from `HEAD`; `None` means *git could not answer*, never *nothing
  changed*.

Module `src/beadloom/doc_sync/surface_ledger.py` — the committed surface record:

- `read_ledger(project_root) -> SurfaceLedger | None`
- `write_ledger(project_root, *, declared_pairs, declared_docs, recorded_at="")`
- `compare_surface(ledger, *, declared_pairs, declared_docs) -> SurfaceVerdict`
  — `recorded` / `shrank` / `message` / `headline`; an absent ledger says "not
  recorded". The headline rides on the gate's sync-check line even when the step
  FAILS, because the run that deleted a doc is the run whose count fell.

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
