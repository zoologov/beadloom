"""Tests for _quick_import_scan() — import-based depends_on edge inference."""

from __future__ import annotations

import builtins
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

if TYPE_CHECKING:
    from pathlib import Path

# Save the original __import__ for the graceful-import test.
_original_import = builtins.__import__


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_clusters(
    tmp_path: Path,
    cluster_map: dict[str, list[str]],
    source_dir: str = "src",
) -> dict[str, dict[str, Any]]:
    """Create cluster dict and write dummy files on disk.

    *cluster_map* maps cluster name -> list of relative file paths
    (relative to *tmp_path*).  Files are created as empty on disk.
    """
    clusters: dict[str, dict[str, Any]] = {}
    for name, files in cluster_map.items():
        written: list[str] = []
        for rel in files:
            fp = tmp_path / rel
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text("", encoding="utf-8")
            written.append(rel)
        clusters[name] = {
            "files": written,
            "children": {},
            "source_dir": source_dir,
        }
    return clusters


def _fake_import(import_path: str) -> MagicMock:
    """Create a mock ImportInfo with the given import_path."""
    info = MagicMock()
    info.import_path = import_path
    return info


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestQuickImportScanEmpty:
    """Empty / trivial inputs."""

    def test_empty_clusters_returns_empty(self, tmp_path: Path) -> None:
        from beadloom.onboarding.scanner import _quick_import_scan

        result = _quick_import_scan(tmp_path, {}, set())
        assert result == []

    def test_single_cluster_no_self_edges(self, tmp_path: Path) -> None:
        """A single cluster importing its own name must not create self-edges."""
        from beadloom.onboarding.scanner import _quick_import_scan

        clusters = _make_clusters(
            tmp_path,
            {"models": ["src/models/user.py"]},
        )
        seen = {"models"}

        # Patch extract_imports at its source module (lazy import target).
        with patch(
            "beadloom.graph.import_resolver.extract_imports",
            return_value=[_fake_import("models.base")],
        ):
            result = _quick_import_scan(tmp_path, clusters, seen)

        assert result == []


class TestQuickImportScanCrossCluster:
    """Cross-cluster dependency detection."""

    def test_cross_cluster_creates_edge(self, tmp_path: Path) -> None:
        from beadloom.onboarding.scanner import _quick_import_scan

        clusters = _make_clusters(
            tmp_path,
            {
                "api": ["src/api/views.py"],
                "models": ["src/models/user.py"],
            },
        )
        seen = {"api", "models"}

        # api/views.py imports from models.
        def fake_extract(file_path: Path) -> list[MagicMock]:
            if "api" in str(file_path):
                return [_fake_import("models.user")]
            return []

        with patch(
            "beadloom.graph.import_resolver.extract_imports",
            side_effect=fake_extract,
        ):
            result = _quick_import_scan(tmp_path, clusters, seen)

        assert len(result) == 1
        assert result[0] == {"src": "api", "dst": "models", "kind": "depends_on"}

    def test_deduplication(self, tmp_path: Path) -> None:
        """Same src->dst should appear only once even when multiple files import it."""
        from beadloom.onboarding.scanner import _quick_import_scan

        clusters = _make_clusters(
            tmp_path,
            {
                "api": ["src/api/views.py", "src/api/routes.py"],
                "models": ["src/models/user.py"],
            },
        )
        seen = {"api", "models"}

        # Both api files import models.
        with patch(
            "beadloom.graph.import_resolver.extract_imports",
            return_value=[_fake_import("models.user")],
        ):
            result = _quick_import_scan(tmp_path, clusters, seen)

        # Exactly one edge, not two.
        assert len(result) == 1
        assert result[0]["src"] == "api"
        assert result[0]["dst"] == "models"

    def test_bidirectional_edges(self, tmp_path: Path) -> None:
        """api->models and models->api should both appear."""
        from beadloom.onboarding.scanner import _quick_import_scan

        clusters = _make_clusters(
            tmp_path,
            {
                "api": ["src/api/views.py"],
                "models": ["src/models/user.py"],
            },
        )
        seen = {"api", "models"}

        def fake_extract(file_path: Path) -> list[MagicMock]:
            if "api" in str(file_path):
                return [_fake_import("models.user")]
            if "models" in str(file_path):
                return [_fake_import("api.client")]
            return []

        with patch(
            "beadloom.graph.import_resolver.extract_imports",
            side_effect=fake_extract,
        ):
            result = _quick_import_scan(tmp_path, clusters, seen)

        srcs_dsts = {(e["src"], e["dst"]) for e in result}
        assert ("api", "models") in srcs_dsts
        assert ("models", "api") in srcs_dsts
        assert len(result) == 2


class TestQuickImportScanCap:
    """Edge cap at _MAX_IMPORT_EDGES (50)."""

    def test_cap_at_50_edges(self, tmp_path: Path) -> None:
        from beadloom.onboarding.scanner import _MAX_IMPORT_EDGES, _quick_import_scan

        # Create 60 clusters, each with one file importing the next.
        cluster_map: dict[str, list[str]] = {}
        for i in range(60):
            name = f"pkg{i}"
            cluster_map[name] = [f"src/{name}/main.py"]

        clusters = _make_clusters(tmp_path, cluster_map)
        seen = {f"pkg{i}" for i in range(60)}

        # Each cluster's file imports the next cluster.
        def fake_extract(file_path: Path) -> list[MagicMock]:
            # Extract the cluster number from path like src/pkg5/main.py
            parts = str(file_path).split("/")
            for p in parts:
                if p.startswith("pkg"):
                    idx = int(p[3:])
                    next_idx = (idx + 1) % 60
                    return [_fake_import(f"pkg{next_idx}.module")]
            return []

        with patch(
            "beadloom.graph.import_resolver.extract_imports",
            side_effect=fake_extract,
        ):
            result = _quick_import_scan(tmp_path, clusters, seen)

        assert len(result) == _MAX_IMPORT_EDGES
        assert len(result) == 50


class TestQuickImportScanGraceful:
    """Graceful handling of missing tree-sitter."""

    def test_graceful_when_tree_sitter_unavailable(self, tmp_path: Path) -> None:
        from beadloom.onboarding.scanner import _quick_import_scan

        clusters = _make_clusters(
            tmp_path,
            {"api": ["src/api/views.py"]},
        )
        seen = {"api"}

        def _raise_for_import_resolver(name: str, *args: Any, **kwargs: Any) -> Any:
            if name == "beadloom.graph.import_resolver":
                raise ImportError("No module named 'tree_sitter'")
            return _original_import(name, *args, **kwargs)

        # Simulate ImportError when trying to import extract_imports.
        with patch(
            "builtins.__import__",
            side_effect=_raise_for_import_resolver,
        ):
            result = _quick_import_scan(tmp_path, clusters, seen)

        assert result == []

    def test_extract_imports_exception_skipped(self, tmp_path: Path) -> None:
        """If extract_imports raises, the file is skipped gracefully."""
        from beadloom.onboarding.scanner import _quick_import_scan

        clusters = _make_clusters(
            tmp_path,
            {
                "api": ["src/api/views.py"],
                "models": ["src/models/user.py"],
            },
        )
        seen = {"api", "models"}

        def failing_extract(file_path: Path) -> list[MagicMock]:
            raise RuntimeError("tree-sitter crash")

        with patch(
            "beadloom.graph.import_resolver.extract_imports",
            side_effect=failing_extract,
        ):
            result = _quick_import_scan(tmp_path, clusters, seen)

        assert result == []


class TestQuickImportScanSeenRefIds:
    """Only create edges to ref_ids that are in seen_ref_ids."""

    def test_ignores_clusters_not_in_seen(self, tmp_path: Path) -> None:
        from beadloom.onboarding.scanner import _quick_import_scan

        clusters = _make_clusters(
            tmp_path,
            {
                "api": ["src/api/views.py"],
                "models": ["src/models/user.py"],
            },
        )
        # Only "api" is in seen_ref_ids, "models" is not.
        seen = {"api"}

        with patch(
            "beadloom.graph.import_resolver.extract_imports",
            return_value=[_fake_import("models.user")],
        ):
            result = _quick_import_scan(tmp_path, clusters, seen)

        assert result == []


class TestQuickImportScanSampleLimit:
    """Only 10 files per cluster are sampled."""

    def test_samples_at_most_10_files(self, tmp_path: Path) -> None:
        from beadloom.onboarding.scanner import _quick_import_scan

        # Create a cluster with 15 files.
        files = [f"src/api/file{i}.py" for i in range(15)]
        clusters = _make_clusters(tmp_path, {"api": files})
        seen = {"api", "models"}

        call_count = 0

        def counting_extract(file_path: Path) -> list[MagicMock]:
            nonlocal call_count
            call_count += 1
            return []

        with patch(
            "beadloom.graph.import_resolver.extract_imports",
            side_effect=counting_extract,
        ):
            _quick_import_scan(tmp_path, clusters, seen)

        # Should have been called at most 10 times (sample limit).
        assert call_count <= 10


class TestBootstrapProjectIntegration:
    """Integration: bootstrap_project() includes import-based edges."""

    def test_bootstrap_includes_import_edges(self, tmp_path: Path) -> None:
        """bootstrap_project on a two-cluster project picks up import edges."""
        import yaml

        from beadloom.onboarding.scanner import bootstrap_project

        # Create a minimal project structure.
        src = tmp_path / "src"
        api_dir = src / "api"
        models_dir = src / "models"
        api_dir.mkdir(parents=True)
        models_dir.mkdir(parents=True)

        # Create Python files with actual import statements.
        (api_dir / "views.py").write_text(
            "from models import user\n",
            encoding="utf-8",
        )
        (models_dir / "user.py").write_text(
            "class User:\n    pass\n",
            encoding="utf-8",
        )

        # Run bootstrap.
        result = bootstrap_project(tmp_path)
        assert result["nodes_generated"] >= 2

        # Read the generated graph.
        graph_file = tmp_path / ".beadloom" / "_graph" / "services.yml"
        assert graph_file.exists()
        data = yaml.safe_load(graph_file.read_text(encoding="utf-8"))

        edges = data.get("edges", [])
        depends_on_edges = [e for e in edges if e["kind"] == "depends_on"]

        # We expect at least one depends_on edge from api -> models
        # (if tree-sitter is available).
        # This test is conditional: if tree-sitter-python is not installed,
        # we still expect the test to pass (just no import edges).
        try:
            import tree_sitter_python  # noqa: F401

            has_ts = True
        except ImportError:
            has_ts = False

        if has_ts:
            api_to_models = [
                e for e in depends_on_edges if e["src"] == "api" and e["dst"] == "models"
            ]
            assert len(api_to_models) >= 1, f"Expected api->models edge, got: {depends_on_edges}"
