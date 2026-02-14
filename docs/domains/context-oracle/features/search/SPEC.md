# Search

FTS5 full-text search over architecture graph nodes and their associated documentation chunks.

Source: `src/beadloom/context_oracle/search.py`

## Specification

### Purpose

Provides keyword search across all indexed nodes and their documentation content. The primary engine is SQLite FTS5, which supports ranked full-text matching with snippet extraction. When FTS5 is unavailable (missing SQLite extension or empty index), the CLI falls back to SQL `LIKE` queries.

### FTS5 Virtual Table

The search index is a FTS5 virtual table:

```sql
CREATE VIRTUAL TABLE search_index USING fts5(
    ref_id,
    kind,
    summary,
    content
);
```

| Column | Source | Description |
|--------|--------|-------------|
| `ref_id` | `nodes.ref_id` | Node identifier |
| `kind` | `nodes.kind` | Node kind (domain, feature, service, entity, adr) |
| `summary` | `nodes.summary` | Node summary text |
| `content` | Concatenated chunks | All chunk content for the node, joined with newlines |

Content is assembled by joining `chunks.content` for all chunks linked to a node through the `docs` table: `chunks c JOIN docs d ON c.doc_id = d.id WHERE d.ref_id = ?`.

### Index Population

```python
def populate_search_index(conn: sqlite3.Connection) -> int
```

Algorithm:

1. Delete all existing rows from `search_index`.
2. Fetch all nodes from the `nodes` table.
3. For each node:
   a. Query all chunks linked via `docs` table.
   b. Concatenate chunk content with `"\n"` separator.
   c. Insert `(ref_id, kind, summary, content)` into `search_index`.
4. Commit the transaction.
5. Return the number of rows inserted.

This function is called during `beadloom reindex`. The index is always rebuilt from scratch (delete + re-insert), not incrementally updated.

### Query Escaping

```python
def _escape_fts5_query(query: str) -> str
```

FTS5 query syntax reserves characters like `*`, `-`, `:`, `(`, `)`. To treat user input as literal search terms:

1. Strip leading/trailing whitespace.
2. Split on whitespace into individual words.
3. Double-quote each word: `word` becomes `"word"`.
4. Join with spaces (implicit AND in FTS5).

Example: `mcp-server status` becomes `"mcp-server" "status"`.

An empty or whitespace-only query produces an empty string, which short-circuits `search_fts5` to return `[]`.

### Search Execution

```python
def search_fts5(conn, query, *, kind=None, limit=10) -> list[dict[str, Any]]
```

Parameters:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `conn` | `sqlite3.Connection` | -- | Open database connection |
| `query` | `str` | -- | Raw search query (will be escaped) |
| `kind` | `str \| None` | `None` | Optional node kind filter |
| `limit` | `int` | `10` | Maximum results to return |

Query construction:

- Without `kind`: `WHERE search_index MATCH ? ORDER BY rank LIMIT ?`
- With `kind`: `WHERE search_index MATCH ? AND kind = ? ORDER BY rank LIMIT ?`

The `rank` column is a built-in FTS5 ranking function (BM25 by default). Results are ordered by ascending rank (lower = more relevant).

### Snippet Extraction

Snippets are generated via the FTS5 `snippet()` function:

```sql
snippet(search_index, 3, '<b>', '</b>', '...', 32)
```

| Argument | Value | Description |
|----------|-------|-------------|
| Table | `search_index` | The FTS5 table |
| Column index | `3` | `content` column (0-indexed) |
| Start marker | `<b>` | Bold open tag around matched terms |
| End marker | `</b>` | Bold close tag |
| Ellipsis | `...` | Separator for non-contiguous fragments |
| Max tokens | `32` | Maximum tokens in the snippet |

### Result Format

Each result is a dict:

```python
{
    "ref_id": str,    # Node identifier
    "kind": str,      # Node kind
    "summary": str,   # Node summary
    "snippet": str,   # FTS5 snippet with <b> markers
    "rank": float,    # BM25 relevance score (lower = better)
}
```

### FTS5 Availability Check

```python
def has_fts5(conn: sqlite3.Connection) -> bool
```

Returns `True` if:
1. The `search_index` table exists (no exception on query).
2. The table contains at least one row (`count(*) > 0`).

Returns `False` if the table does not exist or is empty. Used by the CLI to decide between FTS5 and LIKE fallback.

### CLI Integration

```
beadloom search QUERY [--kind KIND] [--limit N] [--json] [--project DIR]
```

The CLI command calls `search_fts5` when `has_fts5()` returns `True`. Otherwise, it falls back to a SQL `LIKE` query against `nodes.summary`.

### MCP Integration

The `search` MCP tool exposes the same parameters (`query`, `kind`, `limit`) and returns the same result structure as JSON.

## API

### Public Functions

```python
def search_fts5(
    conn: sqlite3.Connection,
    query: str,
    *,
    kind: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]
```

Perform FTS5 MATCH search. Returns a list of result dicts ordered by relevance.

```python
def populate_search_index(conn: sqlite3.Connection) -> int
```

Clear and rebuild the `search_index` FTS5 table from `nodes` and `chunks`. Returns the number of rows inserted.

```python
def has_fts5(conn: sqlite3.Connection) -> bool
```

Check whether the FTS5 search index exists and contains data.

### Private Functions

```python
def _escape_fts5_query(query: str) -> str
```

Escape a raw query string for safe use in FTS5 MATCH expressions.

## Invariants

- `populate_search_index` always starts from an empty table (delete-all before insert), ensuring no stale entries persist.
- Every node in the `nodes` table gets exactly one row in `search_index`, even if it has no chunks (content will be an empty string).
- Search results are always ordered by FTS5 rank (BM25 relevance).
- An empty query always returns an empty list without executing a SQL query.

## Constraints

- FTS5 must be compiled into the SQLite library. Most standard distributions include it, but minimal or embedded builds may not.
- Special characters in the query are neutralized by quoting each word, but this means phrase-level operators and boolean syntax (`AND`, `OR`, `NOT`) are not available to end users.
- The search index is not incrementally updated. Any change to nodes or chunks requires a full `beadloom reindex` to refresh the index.
- The `kind` filter uses exact string equality, not FTS5 column filtering, so it filters after the MATCH.
- Maximum result limit is enforced at the SQL level; there is no pagination or offset support.

## Testing

Tests are located in `tests/test_search.py`. Key scenarios:

- **Basic search**: Index nodes with known content, search for a term, verify matching results with correct fields.
- **Kind filtering**: Verify that `kind` parameter restricts results to the specified node kind.
- **Limit**: Verify that `limit` caps the number of returned results.
- **Empty query**: Verify that whitespace-only or empty input returns `[]`.
- **Query escaping**: Verify that special characters (`*`, `-`, `:`) in queries do not cause FTS5 syntax errors.
- **Snippet content**: Verify that snippets contain `<b>`/`</b>` markers around matched terms.
- **`has_fts5` true/false**: Verify correct detection of populated vs. empty/missing index.
- **`populate_search_index` rebuild**: Verify that calling it twice produces the same row count (idempotent rebuild).
