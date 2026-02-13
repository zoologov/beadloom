# Cache

Two-tier caching layer for context bundles: L1 in-memory dict and L2 SQLite persistent store.

Source: `src/beadloom/context_oracle/cache.py`

## Specification

### Purpose

Context bundle construction involves BFS graph traversal, chunk collection, code symbol lookup, and sync-state checks. The cache avoids repeating this work for identical requests. L1 provides zero-cost in-process lookups for the lifetime of the MCP server. L2 survives server restarts by persisting bundles in the SQLite `bundle_cache` table.

### Cache Key

Both tiers key on the same four parameters that fully determine a context bundle:

```python
CacheKey = tuple[str, int, int, int]  # (ref_id, depth, max_nodes, max_chunks)
```

L1 uses the tuple directly as a dict key. L2 serializes it to a string column `cache_key`.

### Data Structures

#### CacheEntry (dataclass)

| Field | Type | Description |
|-------|------|-------------|
| `bundle` | `dict[str, Any]` | The full context bundle JSON structure |
| `created_at` | `float` | `time.monotonic()` timestamp at insertion |
| `graph_mtime` | `float` | mtime of graph directory at insertion time |
| `docs_mtime` | `float` | mtime of docs directory at insertion time |
| `created_at_iso` | `str` | UTC ISO-8601 timestamp (default `""`) |

### Invalidation Algorithm

Both L1 and L2 use the same mtime-based invalidation strategy. No TTL is involved.

On `get()`:

1. Look up entry by cache key.
2. If `graph_mtime` is provided and `entry.graph_mtime < graph_mtime`, the entry is stale -- delete it, return `None`.
3. If `docs_mtime` is provided and `entry.docs_mtime < docs_mtime`, the entry is stale -- delete it, return `None`.
4. If no mtimes are provided, return the cached value without staleness check.
5. Otherwise, return the cached bundle.

On full reindex, both caches are cleared entirely via `clear()`.

### ETag Computation

```python
def compute_etag(bundle: dict[str, Any]) -> str
```

1. JSON-serialize the bundle with `sort_keys=True, ensure_ascii=False`.
2. Compute SHA-256 of the UTF-8 encoded string.
3. Truncate the hex digest to 16 characters.
4. Return `"sha256:<truncated_hex>"`.

The etag is stored in L2 and can be used by MCP clients for conditional requests.

### L1: ContextCache

In-memory cache backed by a plain `dict[CacheKey, CacheEntry]`.

#### Lifecycle

- Created once per MCP server process.
- Entries accumulate until a reindex triggers `clear()`.
- No size limit or eviction policy -- relies on reindex as the clearing event.

#### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `get` | `(ref_id, depth, max_nodes, max_chunks, *, graph_mtime=None, docs_mtime=None) -> dict \| None` | Return cached bundle or `None` on miss/stale |
| `get_entry` | `(ref_id, depth, max_nodes, max_chunks, *, graph_mtime=None, docs_mtime=None) -> CacheEntry \| None` | Return full `CacheEntry` or `None` on miss/stale |
| `put` | `(ref_id, depth, max_nodes, max_chunks, bundle, *, graph_mtime, docs_mtime) -> None` | Store a bundle with current monotonic + UTC timestamps |
| `clear` | `() -> None` | Remove all entries |
| `clear_ref` | `(ref_id: str) -> None` | Remove all entries whose key tuple has `k[0] == ref_id` |
| `stats` | `() -> dict[str, int]` | Return `{"entries": <count>}` |

### L2: SqliteCache

Persistent cache backed by the `bundle_cache` table in the beadloom SQLite database.

#### Table Schema

```sql
CREATE TABLE IF NOT EXISTS bundle_cache (
    cache_key   TEXT PRIMARY KEY,
    bundle_json TEXT NOT NULL,
    etag        TEXT NOT NULL,
    graph_mtime REAL NOT NULL,
    docs_mtime  REAL NOT NULL,
    created_at  TEXT NOT NULL
);
```

#### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `get` | `(cache_key, *, graph_mtime=0.0, docs_mtime=0.0) -> tuple[dict, str, str] \| None` | Return `(bundle, etag, created_at)` or `None`. Deletes stale rows on read. |
| `put` | `(cache_key, bundle, *, graph_mtime, docs_mtime) -> None` | `INSERT OR REPLACE` with computed etag and UTC ISO timestamp |
| `clear` | `() -> None` | `DELETE FROM bundle_cache` |
| `clear_ref` | `(ref_id: str) -> None` | `DELETE FROM bundle_cache WHERE cache_key LIKE '%<ref_id>%'` |

#### L2 Read-Through Behavior

When L2 `get()` detects a stale row (stored mtime < provided mtime), it deletes the row and commits immediately, then returns `None`. This means a stale L2 hit has the side effect of cleaning up the persistent store.

## API

### Public Functions

```python
def compute_etag(bundle: dict[str, Any]) -> str
```

Compute a deterministic etag for a context bundle. Used by `SqliteCache.put()` and available for external consumers (e.g., MCP `If-None-Match` support).

### Public Classes

```python
class ContextCache:
    """L1 in-memory cache."""
    def __init__(self) -> None: ...
    def get(self, ref_id, depth, max_nodes, max_chunks, *, graph_mtime=None, docs_mtime=None) -> dict | None: ...
    def get_entry(self, ref_id, depth, max_nodes, max_chunks, *, graph_mtime=None, docs_mtime=None) -> CacheEntry | None: ...
    def put(self, ref_id, depth, max_nodes, max_chunks, bundle, *, graph_mtime, docs_mtime) -> None: ...
    def clear(self) -> None: ...
    def clear_ref(self, ref_id: str) -> None: ...
    def stats(self) -> dict[str, int]: ...

class SqliteCache:
    """L2 persistent cache."""
    def __init__(self, conn: sqlite3.Connection) -> None: ...
    def get(self, cache_key, *, graph_mtime=0.0, docs_mtime=0.0) -> tuple[dict, str, str] | None: ...
    def put(self, cache_key, bundle, *, graph_mtime, docs_mtime) -> None: ...
    def clear(self) -> None: ...
    def clear_ref(self, ref_id: str) -> None: ...
```

## Invariants

- A cache hit never returns a bundle produced from an older graph or docs mtime than the caller provides.
- `put()` always overwrites any existing entry for the same key (L1 dict assignment, L2 `INSERT OR REPLACE`).
- `clear()` leaves both caches completely empty -- no residual state.
- `compute_etag` is deterministic: identical bundles produce identical etags.
- L1 `created_at` uses `time.monotonic()`, not wall-clock time, to avoid clock-skew issues.

## Constraints

- No TTL-based expiration -- invalidation is strictly mtime-based.
- L1 has no size limit. It relies on `clear()` being called on reindex. In long-running servers with diverse queries, memory usage grows linearly with distinct cache keys.
- L2 `clear_ref` uses `LIKE '%<ref_id>%'` pattern matching, which is conservative: it may match and delete extra keys if `ref_id` is a substring of an unrelated cache key.
- L2 commits after every `put()`, `clear()`, and stale-delete. There is no batching.
- ETag truncation to 16 hex characters (64 bits) provides collision resistance sufficient for cache validation, not for cryptographic purposes.

## Testing

Tests are located in `tests/test_cache.py`. Key scenarios:

- **L1 hit/miss**: Verify `get()` returns the bundle after `put()`, and `None` for unknown keys.
- **Mtime invalidation**: Verify that providing a newer `graph_mtime` or `docs_mtime` causes a miss and deletes the entry.
- **No-mtime passthrough**: Verify that `get()` without mtime arguments returns the cached value regardless of stored mtimes.
- **`clear()` and `clear_ref()`**: Verify complete and per-ref clearing.
- **`get_entry()`**: Verify it returns the full `CacheEntry` with correct metadata.
- **`stats()`**: Verify entry count reflects insertions and deletions.
- **L2 round-trip**: Verify `put()` then `get()` returns identical bundle, correct etag, and ISO timestamp.
- **L2 stale delete**: Verify stale reads delete the row and return `None`.
- **ETag determinism**: Verify `compute_etag` produces the same result for the same input and different results for different inputs.
