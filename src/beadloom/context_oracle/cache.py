"""L1 in-memory cache for context bundles."""

# beadloom:domain=context-oracle
# beadloom:feature=cache

from __future__ import annotations

import hashlib
import json as _json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path

# Cache key: (ref_id, depth, max_nodes, max_chunks)
CacheKey = tuple[str, int, int, int]


def compute_etag(bundle: dict[str, Any]) -> str:
    """Compute SHA-256 etag for a context bundle."""
    raw = _json.dumps(bundle, sort_keys=True, ensure_ascii=False)
    return f"sha256:{hashlib.sha256(raw.encode()).hexdigest()[:16]}"


@dataclass
class CacheEntry:
    """A cached context bundle with mtime metadata."""

    bundle: dict[str, Any]
    created_at: float
    graph_mtime: float
    docs_mtime: float
    created_at_iso: str = field(default="")


class ContextCache:
    """In-memory LRU-style cache for context bundles.

    Invalidation is based on file mtimes of graph and docs directories.
    Full cache is cleared on reindex.
    """

    def __init__(self) -> None:
        self._store: dict[CacheKey, CacheEntry] = {}

    def get(
        self,
        ref_id: str,
        depth: int,
        max_nodes: int,
        max_chunks: int,
        *,
        graph_mtime: float | None = None,
        docs_mtime: float | None = None,
    ) -> dict[str, Any] | None:
        """Get a cached bundle, or None if miss or stale.

        If graph_mtime or docs_mtime are provided, the cache entry is
        invalidated if the stored mtime is older than the provided one.
        If no mtimes are provided, returns the cached value without checking.
        """
        key: CacheKey = (ref_id, depth, max_nodes, max_chunks)
        entry = self._store.get(key)
        if entry is None:
            return None

        # Check staleness if mtimes provided.
        if graph_mtime is not None and entry.graph_mtime < graph_mtime:
            del self._store[key]
            return None
        if docs_mtime is not None and entry.docs_mtime < docs_mtime:
            del self._store[key]
            return None

        return entry.bundle

    def get_entry(
        self,
        ref_id: str,
        depth: int,
        max_nodes: int,
        max_chunks: int,
        *,
        graph_mtime: float | None = None,
        docs_mtime: float | None = None,
    ) -> CacheEntry | None:
        """Get the full cache entry, or None if miss or stale.

        Same invalidation logic as ``get()``, but returns the
        :class:`CacheEntry` instead of just the bundle dict.
        """
        key: CacheKey = (ref_id, depth, max_nodes, max_chunks)
        entry = self._store.get(key)
        if entry is None:
            return None

        if graph_mtime is not None and entry.graph_mtime < graph_mtime:
            del self._store[key]
            return None
        if docs_mtime is not None and entry.docs_mtime < docs_mtime:
            del self._store[key]
            return None

        return entry

    def put(
        self,
        ref_id: str,
        depth: int,
        max_nodes: int,
        max_chunks: int,
        bundle: dict[str, Any],
        *,
        graph_mtime: float,
        docs_mtime: float,
    ) -> None:
        """Store a bundle in cache."""
        key: CacheKey = (ref_id, depth, max_nodes, max_chunks)
        self._store[key] = CacheEntry(
            bundle=bundle,
            created_at=time.monotonic(),
            graph_mtime=graph_mtime,
            docs_mtime=docs_mtime,
            created_at_iso=datetime.now(tz=timezone.utc).isoformat(),
        )

    def clear(self) -> None:
        """Clear all cached entries (e.g., after reindex)."""
        self._store.clear()

    def clear_ref(self, ref_id: str) -> None:
        """Remove all entries for a specific ref_id."""
        keys_to_remove = [k for k in self._store if k[0] == ref_id]
        for k in keys_to_remove:
            del self._store[k]

    def stats(self) -> dict[str, int]:
        """Return cache statistics."""
        return {"entries": len(self._store)}


class SqliteCache:
    """L2 persistent cache backed by SQLite ``bundle_cache`` table.

    Survives MCP server restarts.  Invalidation via mtime comparison.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def get(
        self,
        cache_key: str,
        *,
        graph_mtime: float = 0.0,
        docs_mtime: float = 0.0,
    ) -> tuple[dict[str, Any], str, str] | None:
        """Get cached entry.  Returns ``(bundle, etag, created_at)`` or *None*."""
        row = self._conn.execute(
            "SELECT bundle_json, etag, created_at, graph_mtime, docs_mtime "
            "FROM bundle_cache WHERE cache_key = ?",
            (cache_key,),
        ).fetchone()
        if row is None:
            return None
        if row["graph_mtime"] < graph_mtime or row["docs_mtime"] < docs_mtime:
            self._conn.execute(
                "DELETE FROM bundle_cache WHERE cache_key = ?",
                (cache_key,),
            )
            self._conn.commit()
            return None
        return (
            _json.loads(row["bundle_json"]),
            str(row["etag"]),
            str(row["created_at"]),
        )

    def put(
        self,
        cache_key: str,
        bundle: dict[str, Any],
        *,
        graph_mtime: float,
        docs_mtime: float,
    ) -> None:
        """Store a bundle in L2 cache."""
        etag = compute_etag(bundle)
        now = datetime.now(tz=timezone.utc).isoformat()
        bundle_json = _json.dumps(bundle, sort_keys=True, ensure_ascii=False)
        self._conn.execute(
            "INSERT OR REPLACE INTO bundle_cache "
            "(cache_key, bundle_json, etag, graph_mtime, docs_mtime, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (cache_key, bundle_json, etag, graph_mtime, docs_mtime, now),
        )
        self._conn.commit()

    def clear(self) -> None:
        """Clear all L2 cache entries."""
        self._conn.execute("DELETE FROM bundle_cache")
        self._conn.commit()

    def clear_ref(self, ref_id: str) -> None:
        """Remove L2 entries containing *ref_id* in their cache key."""
        self._conn.execute(
            "DELETE FROM bundle_cache WHERE cache_key LIKE ?",
            (f"%{ref_id}%",),
        )
        self._conn.commit()


def _dir_mtime(directory: Path) -> float:
    """Return the max mtime of all files under *directory* (0.0 if absent)."""
    max_mtime = 0.0
    if not directory.exists():
        return max_mtime
    for f in directory.rglob("*"):
        if f.is_file():
            try:
                mt = f.stat().st_mtime
            except OSError:
                continue
            max_mtime = max(max_mtime, mt)
    return max_mtime


def compute_bundle_mtimes(project_root: Path) -> tuple[float, float]:
    """Compute ``(graph_mtime, docs_mtime)`` used for bundle-cache freshness."""
    graph_dir = project_root / ".beadloom" / "_graph"
    docs_dir = project_root / "docs"
    return _dir_mtime(graph_dir), _dir_mtime(docs_dir)


def bundle_cache_key(
    ref_ids: list[str],
    depth: int,
    max_nodes: int,
    max_chunks: int,
) -> str:
    """Build the canonical L2 cache key for a context bundle.

    Matches the ``ref_id:depth:max_nodes:max_chunks`` scheme the MCP server
    already uses for single-focus bundles; for multi-focus requests the focus
    ref_ids are joined with ``,`` so distinct focus sets never collide.
    """
    focus = ",".join(ref_ids)
    return f"{focus}:{depth}:{max_nodes}:{max_chunks}"


def build_context_cached(
    conn: sqlite3.Connection,
    cache: SqliteCache,
    ref_ids: list[str],
    *,
    depth: int,
    max_nodes: int,
    max_chunks: int,
    graph_mtime: float = 0.0,
    docs_mtime: float = 0.0,
) -> dict[str, Any]:
    """Build a context bundle, going through the L2 :class:`SqliteCache`.

    Transparent cache: returns byte-identical bundles whether served from
    cache (hit) or freshly built (miss).  On a miss the freshly built bundle
    is written back so repeated builds for the same focus/params hit the
    cache.  Stale entries (mtime advanced) are invalidated by the cache.

    Raises :class:`LookupError` (from :func:`build_context`) for unknown
    focus ref_ids; misses are never written for failed builds.
    """
    # Imported lazily to keep this module free of a hard builder dependency
    # at import time (builder imports remain one-directional).
    from beadloom.context_oracle.builder import build_context

    cache_key = bundle_cache_key(ref_ids, depth, max_nodes, max_chunks)

    cached = cache.get(cache_key, graph_mtime=graph_mtime, docs_mtime=docs_mtime)
    if cached is not None:
        return cached[0]

    bundle = build_context(
        conn,
        ref_ids,
        depth=depth,
        max_nodes=max_nodes,
        max_chunks=max_chunks,
    )
    cache.put(cache_key, bundle, graph_mtime=graph_mtime, docs_mtime=docs_mtime)
    return bundle
