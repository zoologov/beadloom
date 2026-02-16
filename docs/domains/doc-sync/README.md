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

### Modules

- **engine.py** -- Core sync engine: sync state building, multi-phase sync checking, hash computation, coverage analysis
- **doc_indexer.py** -- Markdown scanning, chunking by H2 headings, section classification, and SQLite population
- **cli.py** (in `services/cli.py`) -- `beadloom sync-check` CLI command with `--porcelain`, `--json`, `--report`, `--ref` options

### Git Hook Integration

Beadloom can install a pre-commit hook for automatic checking:

```bash
# Warning mode (does not block commit)
beadloom install-hooks --mode warn

# Blocking mode (blocks commit on stale docs)
beadloom install-hooks --mode block
```

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
- `mark_synced_by_ref(conn: sqlite3.Connection, ref_id: str, project_root: Path) -> int` -- Mark all doc-code pairs for a ref_id as synced. Returns the number of rows updated.
- `check_source_coverage(conn: sqlite3.Connection, project_root: Path) -> list[dict[str, Any]]` -- Check if all source files in a node's directory are tracked. Returns list of dicts with `ref_id`, `doc_path`, `untracked_files`.
- `check_doc_coverage(conn: sqlite3.Connection, project_root: Path) -> list[dict[str, Any]]` -- Check if documentation mentions module names from the source directory. Returns list of dicts with `ref_id`, `doc_path`, `missing_modules`.

### Module `src/beadloom/doc_sync/doc_indexer.py`

- `classify_section(heading: str) -> str` -- Classify a section heading into: `spec`, `invariants`, `api`, `tests`, `constraints`, or `other`.
- `chunk_markdown(text: str) -> list[dict[str, Any]]` -- Split Markdown text into chunks by H2 headings. Each chunk contains `heading`, `section`, `content`, `chunk_index`. Chunks exceeding `MAX_CHUNK_SIZE` (2000 chars) are split by paragraphs.
- `index_docs(docs_dir: Path, conn: sqlite3.Connection, *, ref_id_map: dict[str, str] | None = None) -> DocIndexResult` -- Scan a directory for `.md` files, chunk them, and insert into SQLite.

### CLI (`beadloom sync-check`)

```
beadloom sync-check [--porcelain] [--json] [--report] [--ref REF_ID] [--project DIR]
```

| Flag | Description |
|------|----------|
| `--porcelain` | TAB-separated machine-readable output |
| `--json` | Structured JSON output with summary and pairs |
| `--report` | Markdown report for CI posting |
| `--ref` | Filter results by ref_id |
| `--project` | Project root (default: current directory) |

Exit codes: `0` = all ok, `1` = error, `2` = stale pairs found.

## Testing

Tests: `tests/test_sync_engine.py`, `tests/test_cli_sync_check.py`, `tests/test_cli_sync_update.py`, `tests/test_source_coverage.py`, `tests/test_doc_coverage.py`
