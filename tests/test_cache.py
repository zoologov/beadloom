"""Tests for beadloom.cache — L1 in-memory and L2 SQLite caches."""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.cache import ContextCache, SqliteCache, compute_etag

if TYPE_CHECKING:
    from pathlib import Path


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


class TestSqliteCache:
    """Tests for L2 persistent SQLite cache."""

    @staticmethod
    def _make_conn(tmp_path: Path) -> object:
        from beadloom.db import create_schema, open_db

        db_path = tmp_path / "test.db"
        conn = open_db(db_path)
        create_schema(conn)
        return conn

    def test_get_miss(self, tmp_path: Path) -> None:
        conn = self._make_conn(tmp_path)
        l2 = SqliteCache(conn)  # type: ignore[arg-type]
        assert l2.get("key:1:2:3") is None

    def test_put_and_get(self, tmp_path: Path) -> None:
        conn = self._make_conn(tmp_path)
        l2 = SqliteCache(conn)  # type: ignore[arg-type]
        bundle = {"version": 1, "data": "hello"}
        l2.put("key:1:2:3", bundle, graph_mtime=1.0, docs_mtime=1.0)

        result = l2.get("key:1:2:3", graph_mtime=1.0, docs_mtime=1.0)
        assert result is not None
        assert result[0] == bundle
        assert result[1].startswith("sha256:")
        assert "T" in result[2]  # ISO datetime

    def test_stale_graph_invalidates(self, tmp_path: Path) -> None:
        conn = self._make_conn(tmp_path)
        l2 = SqliteCache(conn)  # type: ignore[arg-type]
        l2.put("k", {"v": 1}, graph_mtime=1.0, docs_mtime=1.0)

        # Newer graph_mtime → stale
        assert l2.get("k", graph_mtime=2.0, docs_mtime=1.0) is None

    def test_stale_docs_invalidates(self, tmp_path: Path) -> None:
        conn = self._make_conn(tmp_path)
        l2 = SqliteCache(conn)  # type: ignore[arg-type]
        l2.put("k", {"v": 1}, graph_mtime=1.0, docs_mtime=1.0)

        # Newer docs_mtime → stale
        assert l2.get("k", graph_mtime=1.0, docs_mtime=2.0) is None

    def test_clear(self, tmp_path: Path) -> None:
        conn = self._make_conn(tmp_path)
        l2 = SqliteCache(conn)  # type: ignore[arg-type]
        l2.put("a", {"v": 1}, graph_mtime=1.0, docs_mtime=1.0)
        l2.put("b", {"v": 2}, graph_mtime=1.0, docs_mtime=1.0)
        l2.clear()
        assert l2.get("a") is None
        assert l2.get("b") is None

    def test_clear_ref(self, tmp_path: Path) -> None:
        conn = self._make_conn(tmp_path)
        l2 = SqliteCache(conn)  # type: ignore[arg-type]
        l2.put("FEAT-1:2:20:10", {"v": 1}, graph_mtime=1.0, docs_mtime=1.0)
        l2.put("OTHER:2:20:10", {"v": 2}, graph_mtime=1.0, docs_mtime=1.0)
        l2.clear_ref("FEAT-1")
        assert l2.get("FEAT-1:2:20:10") is None
        assert l2.get("OTHER:2:20:10") is not None

    def test_persists_across_new_cache_instance(self, tmp_path: Path) -> None:
        """L2 data survives creating a new SqliteCache (simulates restart)."""
        conn = self._make_conn(tmp_path)
        l2a = SqliteCache(conn)  # type: ignore[arg-type]
        l2a.put("k", {"v": 42}, graph_mtime=1.0, docs_mtime=1.0)

        # New instance, same connection
        l2b = SqliteCache(conn)  # type: ignore[arg-type]
        result = l2b.get("k", graph_mtime=1.0, docs_mtime=1.0)
        assert result is not None
        assert result[0]["v"] == 42
