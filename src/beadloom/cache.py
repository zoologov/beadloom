"""L1 in-memory cache for context bundles."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

# Cache key: (ref_id, depth, max_nodes, max_chunks)
CacheKey = tuple[str, int, int, int]


@dataclass
class CacheEntry:
    """A cached context bundle with mtime metadata."""

    bundle: dict[str, Any]
    created_at: float
    graph_mtime: float
    docs_mtime: float


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
