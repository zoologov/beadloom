"""Tests for _quick_import_scan() — import-based depends_on edge inference.

The third parameter is the ref_id each cluster was WRITTEN under, keyed by
cluster name. It was a set of ref_ids until BDL-069, when a cluster stopped
always being written under its own sanitized name: on the `src/<project>/`
layout the root service takes the project name and the package is written as
`<project>-<kind>`. A function that recomputed the name from the directory
then built an edge naming no node at all, so the mapping is passed in and
`TestTheEdgeNamesTheRefIdTheClusterWasWrittenUnder` is the case that holds it.
"""

from __future__ import annotations

import builtins
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest

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

        result = _quick_import_scan(tmp_path, {}, {})
        assert result == []

    def test_single_cluster_no_self_edges(self, tmp_path: Path) -> None:
        """A single cluster importing its own name must not create self-edges."""
        from beadloom.onboarding.scanner import _quick_import_scan

        clusters = _make_clusters(
            tmp_path,
            {"models": ["src/models/user.py"]},
        )
        refs = {"models": "models"}

        # Patch extract_imports at its source module (lazy import target).
        with patch(
            "beadloom.graph.import_resolver.extract_imports",
            return_value=[_fake_import("models.base")],
        ):
            result = _quick_import_scan(tmp_path, clusters, refs)

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
        refs = {"api": "api", "models": "models"}

        # api/views.py imports from models.
        def fake_extract(file_path: Path) -> list[MagicMock]:
            if "api" in str(file_path):
                return [_fake_import("models.user")]
            return []

        with patch(
            "beadloom.graph.import_resolver.extract_imports",
            side_effect=fake_extract,
        ):
            result = _quick_import_scan(tmp_path, clusters, refs)

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
        refs = {"api": "api", "models": "models"}

        # Both api files import models.
        with patch(
            "beadloom.graph.import_resolver.extract_imports",
            return_value=[_fake_import("models.user")],
        ):
            result = _quick_import_scan(tmp_path, clusters, refs)

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
        refs = {"api": "api", "models": "models"}

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
            result = _quick_import_scan(tmp_path, clusters, refs)

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
        refs = {f"pkg{i}": f"pkg{i}" for i in range(60)}

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
            result = _quick_import_scan(tmp_path, clusters, refs)

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
        refs = {"api": "api"}

        def _raise_for_import_resolver(name: str, *args: Any, **kwargs: Any) -> Any:
            if name == "beadloom.graph.import_resolver":
                raise ImportError("No module named 'tree_sitter'")
            return _original_import(name, *args, **kwargs)

        # Simulate ImportError when trying to import extract_imports.
        with patch(
            "builtins.__import__",
            side_effect=_raise_for_import_resolver,
        ):
            result = _quick_import_scan(tmp_path, clusters, refs)

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
        refs = {"api": "api", "models": "models"}

        def failing_extract(file_path: Path) -> list[MagicMock]:
            raise RuntimeError("tree-sitter crash")

        with patch(
            "beadloom.graph.import_resolver.extract_imports",
            side_effect=failing_extract,
        ):
            result = _quick_import_scan(tmp_path, clusters, refs)

        assert result == []


class TestQuickImportScanUnknownImports:
    """An import that names no cluster is not an edge."""

    def test_an_import_naming_no_cluster_creates_no_edge(self, tmp_path: Path) -> None:
        """Every third-party import reaches this, and the graph holds no node for it.

        Until BDL-069 the same case was stated as "a cluster the caller did not
        list in `seen_ref_ids`", which the caller could not produce: the bootstrap
        writes a node for every cluster it passes in. What the guard genuinely
        covers is an import whose path matches nothing the graph holds.
        """
        from beadloom.onboarding.scanner import _quick_import_scan

        clusters = _make_clusters(tmp_path, {"api": ["src/api/views.py"]})
        refs = {"api": "api"}

        with patch(
            "beadloom.graph.import_resolver.extract_imports",
            return_value=[_fake_import("requests.sessions")],
        ):
            result = _quick_import_scan(tmp_path, clusters, refs)

        assert result == []


class TestTheEdgeNamesTheRefIdTheClusterWasWrittenUnder:
    """BDL-069, BDL-UX #214 — the half of the fix that is not the node itself."""

    def test_a_cluster_written_under_a_qualified_ref_id_is_named_by_that_ref_id(
        self, tmp_path: Path
    ) -> None:
        """`src/ledger/` in a project called `ledger` is written as `ledger-domain`.

        Both ends of the edge are affected, and for different reasons: the source
        was recomputed from the directory name unconditionally, so it named no
        node, and the destination was looked up in a set of ref_ids that no longer
        holds the name an import spells.
        """
        from beadloom.onboarding.scanner import _quick_import_scan

        clusters = _make_clusters(
            tmp_path,
            {
                "ledger": ["src/ledger/book.py"],
                "shared": ["src/shared/money.py"],
            },
        )
        refs = {"ledger": "ledger-domain", "shared": "shared"}

        def fake_extract(file_path: Path) -> list[MagicMock]:
            if "ledger" in str(file_path):
                return [_fake_import("shared.money")]
            return [_fake_import("ledger.book")]

        with patch(
            "beadloom.graph.import_resolver.extract_imports",
            side_effect=fake_extract,
        ):
            result = _quick_import_scan(tmp_path, clusters, refs)

        assert {(e["src"], e["dst"]) for e in result} == {
            ("ledger-domain", "shared"),
            ("shared", "ledger-domain"),
        }, result


class TestQuickImportScanSampleLimit:
    """Only 10 files per cluster are sampled."""

    def test_samples_at_most_10_files(self, tmp_path: Path) -> None:
        from beadloom.onboarding.scanner import _quick_import_scan

        # Create a cluster with 15 files.
        files = [f"src/api/file{i}.py" for i in range(15)]
        clusters = _make_clusters(tmp_path, {"api": files})
        refs = {"api": "api", "models": "models"}

        call_count = 0

        def counting_extract(file_path: Path) -> list[MagicMock]:
            nonlocal call_count
            call_count += 1
            return []

        with patch(
            "beadloom.graph.import_resolver.extract_imports",
            side_effect=counting_extract,
        ):
            _quick_import_scan(tmp_path, clusters, refs)

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


def _go_available() -> bool:
    try:
        import tree_sitter_go  # noqa: F401
    except ImportError:
        return False
    return True


def _go_project(tmp_path: Path, files: dict[str, str]) -> dict[str, dict[str, Any]]:
    """Write a Go project and return its clusters, one per ``<source dir>/<name>`` folder."""
    clusters: dict[str, dict[str, Any]] = {}
    for rel_path, text in files.items():
        path = tmp_path / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        parts = rel_path.split("/")
        if rel_path.endswith(".go") and len(parts) >= 3:
            entry = clusters.setdefault(
                parts[1], {"files": [], "children": {}, "source_dir": parts[0]}
            )
            entry["files"].append(rel_path)
    return clusters


def _go_imports(*paths: str) -> str:
    return "package x\n\nimport (\n" + "".join(f'\t"{p}"\n' for p in paths) + ")\n"


@pytest.mark.skipif(not _go_available(), reason="tree-sitter-go not installed")
class TestAGoImportNamesThePackageItsModulePathNames:
    """BDL-076 B5: a Go import is read through the module path ``go.mod`` declares.

    Measured by B3 on the Go adopter fixture: the scan took the first segment of
    ``example.org/tidewater/internal/catalog`` that named a cluster, and on the
    standard layout ``cmd/tidewater/`` names the module, so every internal import
    landed on the entry point.
    """

    def test_the_entry_point_named_after_the_module_attracts_no_internal_import(
        self, tmp_path: Path
    ) -> None:
        from beadloom.onboarding.scanner import _quick_import_scan

        clusters = _go_project(
            tmp_path,
            {
                "go.mod": "module example.org/tidewater\n",
                "cmd/tidewater/main.go": _go_imports(
                    "net/http", "example.org/tidewater/internal/api"
                ),
                "internal/api/api.go": _go_imports(
                    "encoding/json", "example.org/tidewater/internal/catalog"
                ),
                "internal/catalog/catalog.go": _go_imports(
                    "example.org/tidewater/internal/catalog/search"
                ),
                "internal/catalog/search/search.go": "package search\n",
            },
        )
        refs = {name: f"{name}-node" for name in clusters}

        edges = _quick_import_scan(tmp_path, clusters, refs)

        assert {(e["src"], e["dst"]) for e in edges} == {
            ("tidewater-node", "api-node"),
            ("api-node", "catalog-node"),
        }

    def test_a_module_from_elsewhere_whose_segment_names_a_cluster_is_no_edge(
        self, tmp_path: Path
    ) -> None:
        from beadloom.onboarding.scanner import _quick_import_scan

        clusters = _go_project(
            tmp_path,
            {
                "go.mod": "module example.org/tidewater\n",
                "internal/api/api.go": _go_imports("github.com/acme/storage/client", "net/http"),
                "internal/storage/storage.go": "package storage\n",
                "internal/http/http.go": "package http\n",
            },
        )
        refs = {name: name for name in clusters}

        assert _quick_import_scan(tmp_path, clusters, refs) == []


def _jvm_available() -> bool:
    try:
        import tree_sitter_java  # noqa: F401
        import tree_sitter_kotlin  # noqa: F401
    except ImportError:
        return False
    return True


def _java(package: str, *imports: str) -> str:
    lines = "".join(f"import {name};\n" for name in imports)
    return f"package {package};\n\n{lines}\nclass X {{}}\n"


@pytest.mark.skipif(not _jvm_available(), reason="tree-sitter-java or -kotlin not installed")
class TestAJvmImportNamesAPackageUnderTheSourceRoots:
    """BDL-076 B6: a Java or Kotlin import is read as a package path under the source roots.

    The segment reading took the first segment of an import naming a cluster, so
    ``org.springframework.web.client.RestClient`` named a package ``web`` of the
    project's own. Read under ``src/main/java`` it names no folder of the project.
    """

    def _scan(self, tmp_path: Path, files: dict[str, str]) -> set[tuple[str, str]]:
        from beadloom.onboarding.scanner import _quick_import_scan
        from beadloom.onboarding.scanner.jvm_layout import cluster_packages, read_jvm_layout

        for rel_path, text in files.items():
            path = tmp_path / rel_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        layout = read_jvm_layout(tmp_path)
        clusters = cluster_packages(layout)
        refs = {name: name for name in clusters}
        edges = _quick_import_scan(tmp_path, clusters, refs, jvm=layout)
        return {(e["src"], e["dst"]) for e in edges}

    def test_a_third_party_import_sharing_a_package_name_is_no_edge(self, tmp_path: Path) -> None:
        shop = "src/main/java/org/acme/shop"
        edges = self._scan(
            tmp_path,
            {
                f"{shop}/web/Controller.java": _java(
                    "org.acme.shop.web", "org.acme.shop.model.Item"
                ),
                f"{shop}/model/Item.java": _java(
                    "org.acme.shop.model", "org.springframework.web.client.RestClient"
                ),
            },
        )

        assert edges == {("web", "model")}

    def test_an_import_of_another_modules_package_joins_the_two_modules(
        self, tmp_path: Path
    ) -> None:
        edges = self._scan(
            tmp_path,
            {
                "core/src/main/java/org/acme/core/geo/Point.java": _java("org.acme.core.geo"),
                "app/src/main/kotlin/org/acme/app/Main.kt": (
                    "package org.acme.app\n\nimport org.acme.core.geo.Point\n\nfun main() {}\n"
                ),
            },
        )

        assert edges == {("app", "core")}
