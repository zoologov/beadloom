# Doc Sync Engine

Mechanism for tracking synchronization between documentation and code.

## Specification

### How It Works

Doc Sync Engine compares document and code hashes to detect desynchronization through a multi-phase pipeline:

1. **build_sync_state** -- finds doc-code pairs that share the same ref_id
2. **check_sync** -- compares current file hashes and symbol signatures against stored baselines, then runs source coverage and doc coverage checks

The sync check pipeline operates in three phases:

- **Phase 1: Hash and symbol drift detection.** For each sync_state entry, compares on-disk file hashes against stored hashes. Also computes a symbols hash (SHA-256 of sorted code_symbols rows) and compares against the stored `symbols_hash`. Detects `hash_changed` and `symbols_changed` drift reasons.
- **Phase 2: Source coverage checks** (`check_source_coverage`). For each graph node with a directory-based `source` (ending in `/`), verifies that all Python files on disk are tracked in sync_state or code_symbols. Reports `untracked_files` when gaps are found.
- **Phase 3: Doc coverage checks** (`check_doc_coverage`). For each graph node with a directory-based `source`, verifies that the linked documentation mentions all Python module names (file stems). Reports `missing_modules` when the doc does not reference a module.

### Sync Pair

```python
@dataclass
class SyncPair:
    ref_id: str
    doc_path: str
    code_path: str
    doc_hash: str
    code_hash: str
```

### Statuses

| Status | Description |
|--------|----------|
| `ok` | Document and code are synchronized |
| `stale` | Hash has changed -- update needed |

### Stale Reasons

| Reason | Description |
|--------|----------|
| `ok` | No drift detected |
| `hash_changed` | File hash on disk differs from stored hash |
| `symbols_changed` | Code symbols (function/class signatures) changed while doc hash remained the same |
| `untracked_files` | Python files in the node's source directory are not tracked in sync_state or code_symbols |
| `missing_modules` | The linked documentation does not mention one or more module names from the source directory |
| `surface_drift` | **Advisory warning** (severity `warning`, never a hard failure / exit 2). A reference / overview doc that declared `<!-- beadloom:watches=... -->` has had a watched surface (`cli` / `graph` / `flow.yml`) change since its baseline. Stored in the separate `reference_state` table; cleared with `beadloom sync-update <doc> --yes`. |

### Modules

- **engine.py** -- Core sync engine: sync state building, multi-phase sync checking, hash computation, coverage analysis, and reference-doc surface-drift state (build/check/clear)
- **surface.py** -- Layer 2 reference surface-drift: parses the in-doc `<!-- beadloom:watches=cli,graph,flow.yml -->` annotation and computes coarse, deterministic per-surface signatures (`cli` command+flag tree, `graph` node+edge identity set, normalized `flow.yml`) plus the order-sensitive aggregate hash
- **doc_indexer.py** -- Markdown scanning, chunking by H2 headings, section classification, and SQLite population
- **audit.py** -- Documentation audit: fact registry, comparator, and audit facade for detecting stale numeric facts
- **scanner.py** -- Document scanner: keyword-proximity extraction of numeric fact mentions from markdown files
- **docsync.py** (in `services/commands/`) -- CLI commands: `beadloom sync-check`, `beadloom sync-update`, `beadloom install-hooks`, and `beadloom active-sync` (the ACTIVE-table reconcile command; annotated as `component=active-table` but housed in this module after the BDL-059 split of `services/cli.py` into `services/commands/`)

### Features

- **[Sync Check](features/sync-check/SPEC.md)** -- The doc-code synchronization engine (`beadloom sync-check` / `sync-update`).
- **[Docs Audit](features/docs-audit/SPEC.md)** -- Zero-config meta-doc staleness detection via keyword-proximity matching. CLI: `beadloom docs audit`.

### Components

- **[Doc Indexer](components/doc-indexer/DOC.md)** -- Markdown scan + chunk + `docs`/`chunks` population; the doc half of every sync-check pair.

### Git Hook Integration

Beadloom installs **two** git hooks by default: a pre-commit hook (lighter check) and a pre-push hook (the authoritative blocking Beadloom Gate). Use `--pre-commit` or `--pre-push` to select one.

```bash
# Install both hooks in warning mode (default)
beadloom install-hooks --mode warn

# Install both hooks in blocking mode
beadloom install-hooks --mode block

# Install only the pre-commit hook
beadloom install-hooks --pre-commit

# Install only the pre-push Gate hook
beadloom install-hooks --pre-push

# Remove the installed hook(s)
beadloom install-hooks --remove
```

**Pre-commit hook** runs:
- Ruff lint check (via `uv run ruff check`)
- Mypy type check (via `uv run mypy`)
- `beadloom sync-check --porcelain` (stale doc detection)
- `beadloom active-sync --stage` (ACTIVE/table coherence; guarded no-op when `bd` is unavailable)

In `warn` mode, violations print warnings but do not block the commit. In `block` mode, ruff/mypy/sync-check violations exit non-zero and prevent the commit.

**Pre-push hook** runs the full Beadloom Gate (`beadloom ci`): incremental reindex → lint → coverage-lint → sync-check → doctor. This is the authoritative blocking gate; it exits non-zero on any failure, preventing the push. Fail-safe: if `beadloom` is not on PATH, the hook is a no-op.

## Invariants

- A doc-code pair is determined by a shared ref_id
- doc_path is taken from the docs table (linked to a node via ref_id)
- code_path is taken from code_symbols (via annotations pointing to a ref_id)
- When staleness is detected, the status is updated in the sync_state table
- `_compute_symbols_hash` returns an empty string when no symbols are annotated with the given ref_id, allowing callers to skip drift checks for unlinked nodes
- Source coverage excludes boilerplate files: `__init__.py`, `conftest.py`, `__main__.py`
- Doc coverage uses word-boundary matching (`\b<stem>\b`, case-insensitive) for module name detection

## API

### Module `src/beadloom/doc_sync/engine.py`

- `build_sync_state(conn: sqlite3.Connection) -> list[SyncPair]` -- Build sync pairs from docs and code_symbols sharing a ref_id.
- `check_sync(conn: sqlite3.Connection, project_root: Path | None = None) -> list[dict[str, Any]]` -- Multi-phase sync check. Returns list of dicts with fields: `doc_path`, `code_path`, `ref_id`, `status`, `reason`, and optional `details`. Runs hash comparison, symbol drift detection, source coverage, and doc coverage checks.
- `mark_synced(conn: sqlite3.Connection, doc_path: str, code_path: str, project_root: Path) -> None` -- Recompute hashes for a doc-code pair and mark as synced. Updates `symbols_hash` baseline.
- `mark_synced_by_ref(conn: sqlite3.Connection, ref_id: str, project_root: Path) -> int` -- Mark all doc-code pairs for a ref_id as synced. Returns the number of rows updated. (Backs `beadloom sync-update --yes`/`--all`.)
- `check_sync_since(conn: sqlite3.Connection, *, project_root: Path, since: str) -> list[dict[str, Any]]` -- Report doc-code pairs that drifted **relative to a git ref baseline** (instead of the stored `sync_state`). A pair is stale-since-ref iff its code file changed between `since` and the working tree **and** its linked doc was *not* correspondingly updated since `since` (if the doc also changed, the dev already touched it → `ok`). Reads git (`git show <ref>:<path>`) + disk only; mutates neither `sync_state` nor the working tree; result shape mirrors `check_sync` so the JSON/porcelain renderers are shared. This is what makes drift detection survive a fresh CI checkout (a clean clone re-baselines `sync_state` to the just-pushed code, masking per-push drift).
- `_validate_git_ref(project_root: Path, ref: str) -> bool` -- `git rev-parse --verify <ref>`; an all-zero SHA (force-push / first-push sentinel) never resolves so it is rejected. Mirrors `graph.diff._validate_git_ref`.
- `check_source_coverage(conn: sqlite3.Connection, project_root: Path) -> list[dict[str, Any]]` -- Check if all source files in a node's directory are tracked. Returns list of dicts with `ref_id`, `doc_path`, `untracked_files`.
- `check_doc_coverage(conn: sqlite3.Connection, project_root: Path) -> list[dict[str, Any]]` -- Check if documentation mentions module names from the source directory. Returns list of dicts with `ref_id`, `doc_path`, `missing_modules`.
- `build_reference_state(conn: sqlite3.Connection, project_root: Path) -> int` -- (BDL-057 Layer 2) Discover `watches`-annotated reference docs and baseline each one's aggregate surface hash into the `reference_state` table. The baseline is **preserved across reindex** for docs already tracked with the same `watches` set (so accrued surface drift survives a routine reindex, mirroring the symbol-pair fixpoint concern); a fresh baseline is taken only for newly-discovered docs or when the declared `watches` set changes. Docs whose annotation was removed are dropped. Idempotent. Returns the number of reference docs recorded.
- `check_reference_drift(conn: sqlite3.Connection, project_root: Path) -> list[dict[str, Any]]` -- (BDL-057 Layer 2) Recompute each reference doc's aggregate hash and report drift. Returns one dict per reference doc with `doc_path`, `watches`, `status` (`ok`/`surface_drift`), `reason`, and `severity` (always `warning`). Persists the new status; never affects the `sync-check` exit code.
- `mark_reference_synced(conn: sqlite3.Connection, doc_path: str | None, project_root: Path, *, all_docs: bool = False) -> int` -- (BDL-057 Layer 2) Re-baseline a reference doc's aggregate hash (or every reference doc when `all_docs`), clearing surface drift. Returns the number of rows re-baselined. (Backs `beadloom sync-update <doc> --yes` / `--all`.)

### Module `src/beadloom/doc_sync/surface.py`

- `VALID_SURFACES: tuple[str, ...]` -- The known coarse surfaces: `("cli", "graph", "flow.yml")`.
- `parse_watches(text: str) -> list[str] | None` -- Parse the `<!-- beadloom:watches=cli,graph,flow.yml -->` annotation; returns the ordered, de-duplicated list of *known* surfaces in declared order, or `None` when absent / no known surface (unknown tokens are silently dropped).
- `cli_signature() -> str` -- SHA-256 of the sorted Click command + option-flag tree (command paths + flag names), so adding/removing a command or flag moves it but help-text edits do not.
- `graph_signature(conn: sqlite3.Connection) -> str` -- SHA-256 of the sorted node `ref_id|kind` set plus the sorted edge `src|dst|kind|contract_key` set (a coarse identity set, not node content).
- `flow_signature(project_root: Path) -> str` -- SHA-256 of `.beadloom/flow.yml` re-serialized canonically (sorted keys), or `""` when absent/invalid; comments and key order do not move it.
- `surface_signature(surface: str, conn: sqlite3.Connection, project_root: Path) -> str` -- Dispatch to the per-surface signature; raises `ValueError` for an unknown surface.
- `aggregate_hash(watches: list[str], conn: sqlite3.Connection, project_root: Path) -> str` -- SHA-256 of the watched surfaces' signatures concatenated in declared order (order-sensitive by design).

### Module `src/beadloom/doc_sync/doc_indexer.py`

- `classify_section(heading: str) -> str` -- Classify a section heading into: `spec`, `invariants`, `api`, `tests`, `constraints`, or `other`.
- `chunk_markdown(text: str) -> list[dict[str, Any]]` -- Split Markdown text into chunks by H2 headings. Each chunk contains `heading`, `section`, `content`, `chunk_index`. Chunks exceeding `MAX_CHUNK_SIZE` (2000 chars) are split by paragraphs.
- `index_docs(docs_dir: Path, conn: sqlite3.Connection, *, ref_id_map: dict[str, str] | None = None) -> DocIndexResult` -- Scan a directory for `.md` files, chunk them, and insert into SQLite.

### Module `src/beadloom/services/commands/docsync.py`

CLI commands for doc-sync operations. This module was split from `services/cli.py` in BDL-059.

- `sync_check(*, porcelain: bool, output_json: bool, output_report: bool, ref_filter: str | None, since_ref: str | None, project: Path | None) -> None` -- Check doc-code synchronization status. Exit codes: 0 = all ok, 1 = error, 2 = stale pairs found.
- `install_hooks(*, mode: str, remove: bool, pre_commit: bool, pre_push: bool, project: Path | None) -> None` -- Install or remove beadloom git hooks. By default installs BOTH pre-commit and pre-push hooks. Use `--pre-commit` / `--pre-push` to select one.
- `active_sync(*, epic: str | None, check_only: bool, output_json: bool, no_export: bool, stage: bool, project: Path | None) -> None` -- Reconcile ACTIVE.md bead-status tables from `bd` (the source of truth). No-op when `bd` is unavailable or no ACTIVE table exists.
- `sync_update(ref_id: str | None, *, check_only: bool, assume_yes: bool, all_refs: bool, project: Path | None) -> None` -- Show sync status and update docs for a ref_id. Supports interactive editor mode, non-interactive re-baseline (`--yes`), and batch re-baseline (`--all`).

### CLI (`beadloom sync-check`)

```
beadloom sync-check [--porcelain] [--json] [--report] [--ref REF_ID] [--since GIT_REF] [--project DIR]
```

| Flag | Description |
|------|----------|
| `--porcelain` | TAB-separated machine-readable output |
| `--json` | Structured JSON output: `summary` (incl. advisory `surface_drift` count), the symbol-pair `pairs` array (unchanged), and an additive `references` array for reference-doc surface drift |
| `--report` | Markdown report for CI posting |
| `--ref` | Filter results by ref_id |
| `--since` | Baseline = code state at this git ref (e.g. the push's parent) instead of the stored `sync_state`; reports pairs whose code drifted since the ref while the doc was not correspondingly updated. Delegates to `check_sync_since`; invalid/zero refs are rejected via `_validate_git_ref`. |
| `--project` | Project root (default: current directory) |

Exit codes: `0` = all ok, `1` = error, `2` = stale pairs found.

### CLI (`beadloom sync-update`)

```
beadloom sync-update [REF_ID] [--check] [--yes|-y] [--all] [--project DIR]
```

Show sync status and update docs for a ref_id. In interactive mode (default), displays stale pairs and opens each stale doc in `$EDITOR` for manual correction, then marks them synced via `mark_synced`. In non-interactive mode (`--yes`), delegates to `_mark_synced_noninteractive` which calls `mark_synced_by_ref` to re-baseline hashes without prompting.

| Argument/Flag | Description |
|---------------|----------|
| `REF_ID` | Optional positional argument; the symbol-pair ref to update, **or** a reference doc's path (e.g. `docs/architecture.md`) to clear its surface drift. Required unless `--all` is used. |
| `--check` | Only show status, don't open editor. |
| `--yes` / `-y` | Non-interactive: re-baseline freshness without an editor or prompt. |
| `--all` | With `--yes`: re-baseline every currently-stale ref (for the fixpoint loop). Requires `--yes`; mutually exclusive with an explicit `REF_ID`. |
| `--project` | Project root (default: current directory). |

### CLI (`beadloom install-hooks`)

```
beadloom install-hooks [--mode {warn,block}] [--remove] [--pre-commit] [--pre-push] [--project DIR]
```

Installs or removes beadloom git hooks. By default installs **both** the pre-commit hook (lighter warn/block check) and the pre-push hook (the authoritative blocking Beadloom Gate). Use `--pre-commit` or `--pre-push` to select one. The `--remove` flag deletes the selected hook(s).

| Flag | Description |
|------|----------|
| `--mode` | Hook mode: `warn` (default) or `block`. In warn mode, violations print warnings but do not block. In block mode, violations exit non-zero and prevent the commit/push. |
| `--remove` | Remove the selected hook(s). |
| `--pre-commit` | Operate on the pre-commit hook only. |
| `--pre-push` | Operate on the pre-push Gate hook only. |
| `--project` | Project root (default: current directory). |

### CLI (`beadloom active-sync`)

```
beadloom active-sync [--epic EPIC] [--check] [--json] [--no-export] [--stage] [--project DIR]
```

Reconcile ACTIVE.md bead-status tables from `bd` (the source of truth). For each epic's ACTIVE.md, rewrites the bead-status table's Status cells to match `bd` (rich coordinator notes are preserved when the state agrees). Default = fix mode (writes + syncs the tracked `.beads/issues.jsonl` via `bd export`); `--check` reports drift without writing (exit 1 on drift).

No-op contract: if `bd` is unavailable OR there is no ACTIVE file with a bead-status table, this exits 0 and writes nothing (a non-flow repo is never affected). With `--stage` (fix mode), `git add` is run on EXACTLY the reconciled ACTIVE.md paths + the exported jsonl — nothing else.

| Flag | Description |
|------|----------|
| `--epic` | Reconcile only this epic's ACTIVE.md. |
| `--check` | Report drift without writing; exit 1 if any drift, 0 if clean. |
| `--json` | Machine-readable JSON output. |
| `--no-export` | Skip the `bd export` jsonl sync (fix mode only). |
| `--stage` | `git add` EXACTLY the reconciled ACTIVE.md(s) + the exported jsonl (fix mode only); never stages unrelated files. Best-effort (no git → skip). |
| `--project` | Project root (default: current directory). |

## Testing

Tests: `tests/test_sync_engine.py`, `tests/test_cli_sync_check.py`, `tests/test_cli_sync_update.py`, `tests/test_source_coverage.py`, `tests/test_doc_coverage.py`, `tests/test_surface.py`, `tests/test_reference_drift.py`, `tests/test_cli_reference_drift.py`
