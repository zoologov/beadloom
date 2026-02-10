"""Tests for beadloom.cache — L1 in-memory cache for context bundles."""

from __future__ import annotations

from beadloom.cache import ContextCache, compute_etag


class TestContextCache:
    def test_get_miss(self) -> None:
        cache = ContextCache()
        result = cache.get("PROJ-1", 2, 20, 10)
        assert result is None

    def test_put_and_get(self) -> None:
        cache = ContextCache()
        bundle = {"version": 1, "focus": {"ref_id": "PROJ-1"}}
        cache.put("PROJ-1", 2, 20, 10, bundle, graph_mtime=1000.0, docs_mtime=1000.0)
        result = cache.get("PROJ-1", 2, 20, 10)
        assert result is not None
        assert result["version"] == 1

    def test_different_params_are_different_keys(self) -> None:
        cache = ContextCache()
        bundle1 = {"version": 1, "depth": 1}
        bundle2 = {"version": 1, "depth": 2}
        cache.put("A", 1, 20, 10, bundle1, graph_mtime=1000.0, docs_mtime=1000.0)
        cache.put("A", 2, 20, 10, bundle2, graph_mtime=1000.0, docs_mtime=1000.0)

        r1 = cache.get("A", 1, 20, 10)
        r2 = cache.get("A", 2, 20, 10)
        assert r1 is not None
        assert r2 is not None
        assert r1["depth"] == 1
        assert r2["depth"] == 2

    def test_invalidate_by_graph_mtime(self) -> None:
        cache = ContextCache()
        bundle = {"version": 1}
        cache.put("A", 2, 20, 10, bundle, graph_mtime=1000.0, docs_mtime=1000.0)

        # Same mtime → hit.
        assert cache.get("A", 2, 20, 10, graph_mtime=1000.0) is not None

        # Newer mtime → miss (invalidated).
        assert cache.get("A", 2, 20, 10, graph_mtime=2000.0) is None

    def test_invalidate_by_docs_mtime(self) -> None:
        cache = ContextCache()
        bundle = {"version": 1}
        cache.put("A", 2, 20, 10, bundle, graph_mtime=1000.0, docs_mtime=1000.0)

        # Newer docs mtime → miss.
        assert cache.get("A", 2, 20, 10, docs_mtime=2000.0) is None

    def test_clear(self) -> None:
        cache = ContextCache()
        cache.put("A", 2, 20, 10, {"v": 1}, graph_mtime=1.0, docs_mtime=1.0)
        cache.put("B", 2, 20, 10, {"v": 2}, graph_mtime=1.0, docs_mtime=1.0)
        cache.clear()
        assert cache.get("A", 2, 20, 10) is None
        assert cache.get("B", 2, 20, 10) is None

    def test_clear_ref(self) -> None:
        cache = ContextCache()
        cache.put("A", 2, 20, 10, {"v": 1}, graph_mtime=1.0, docs_mtime=1.0)
        cache.put("B", 2, 20, 10, {"v": 2}, graph_mtime=1.0, docs_mtime=1.0)
        cache.clear_ref("A")
        assert cache.get("A", 2, 20, 10) is None
        assert cache.get("B", 2, 20, 10) is not None

    def test_stats(self) -> None:
        cache = ContextCache()
        cache.put("A", 2, 20, 10, {"v": 1}, graph_mtime=1.0, docs_mtime=1.0)
        stats = cache.stats()
        assert stats["entries"] == 1

    def test_no_mtime_check_on_get(self) -> None:
        """If no mtime is provided on get, return cached value regardless."""
        cache = ContextCache()
        cache.put("A", 2, 20, 10, {"v": 1}, graph_mtime=1000.0, docs_mtime=1000.0)
        # No mtime args → always hit (no invalidation check).
        assert cache.get("A", 2, 20, 10) is not None

    def test_get_entry_returns_cache_entry(self) -> None:
        cache = ContextCache()
        bundle = {"version": 1}
        cache.put("A", 2, 20, 10, bundle, graph_mtime=1.0, docs_mtime=1.0)
        entry = cache.get_entry("A", 2, 20, 10)
        assert entry is not None
        assert entry.bundle == bundle
        assert entry.created_at_iso != ""

    def test_get_entry_miss(self) -> None:
        cache = ContextCache()
        assert cache.get_entry("NOPE", 2, 20, 10) is None

    def test_get_entry_stale_graph(self) -> None:
        cache = ContextCache()
        cache.put("A", 2, 20, 10, {"v": 1}, graph_mtime=1.0, docs_mtime=1.0)
        assert cache.get_entry("A", 2, 20, 10, graph_mtime=2.0) is None

    def test_get_entry_stale_docs(self) -> None:
        cache = ContextCache()
        cache.put("A", 2, 20, 10, {"v": 1}, graph_mtime=1.0, docs_mtime=1.0)
        assert cache.get_entry("A", 2, 20, 10, docs_mtime=2.0) is None

    def test_created_at_iso_populated(self) -> None:
        cache = ContextCache()
        cache.put("A", 2, 20, 10, {"v": 1}, graph_mtime=1.0, docs_mtime=1.0)
        entry = cache.get_entry("A", 2, 20, 10)
        assert entry is not None
        assert "T" in entry.created_at_iso  # ISO 8601 format


class TestComputeEtag:
    def test_deterministic(self) -> None:
        bundle = {"version": 1, "focus": {"ref_id": "A"}}
        assert compute_etag(bundle) == compute_etag(bundle)

    def test_prefix(self) -> None:
        assert compute_etag({"v": 1}).startswith("sha256:")

    def test_different_bundles_different_etags(self) -> None:
        e1 = compute_etag({"v": 1})
        e2 = compute_etag({"v": 2})
        assert e1 != e2
