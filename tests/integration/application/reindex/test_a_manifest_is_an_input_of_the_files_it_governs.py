"""A manifest is an input of every file it governs (``beadloom-jcng``).

Found by BDL-076 (``beadloom-ujzb.14``, ``beadloom-ujzb.16``): a Go import is resolved
through the ``go.mod`` and ``go.work`` that govern the importing file, and a Swift import
through ``Package.swift``, but an incremental reindex re-read a file's imports only when that
file changed. A manifest is not a source file, so an edit to it alone was "nothing changed",
and every import under it kept the answer it had before the edit.

Each case builds the index the way an adopter does, edits only a manifest (or moves one
source file), and compares every row of ``code_imports`` and every derived ``depends_on``
edge with a fresh index of a copy of the same tree.
"""

from __future__ import annotations

import shutil
import sqlite3
from typing import TYPE_CHECKING

import pytest

from beadloom.application.reindex import incremental_reindex, reindex

if TYPE_CHECKING:
    from pathlib import Path

pytest.importorskip("tree_sitter_go")
pytest.importorskip("tree_sitter_swift")


def _graph(nodes: dict[str, str]) -> str:
    """A root service and one node per source folder, each ``part_of`` the root."""
    lines = ["nodes:", "  - ref_id: root", "    kind: service", "    summary: The project."]
    lines.append('    source: ""')
    for ref_id, source in nodes.items():
        lines += [
            f"  - ref_id: {ref_id}",
            "    kind: service",
            f"    summary: The {ref_id} package.",
            f"    source: {source}/",
        ]
    lines.append("edges:")
    lines += [f"  - {{src: {ref_id}, dst: root, kind: part_of}}" for ref_id in nodes]
    return "\n".join(lines) + "\n"


def _project(root: Path, nodes: dict[str, str], config: str, files: dict[str, str]) -> Path:
    graph = root / ".beadloom" / "_graph"
    graph.mkdir(parents=True)
    (graph / "graph.yml").write_text(_graph(nodes), encoding="utf-8")
    (root / ".beadloom" / "config.yml").write_text(config, encoding="utf-8")
    for rel_path, text in files.items():
        _write(root, rel_path, text)
    return root


def _write(root: Path, rel_path: str, text: str) -> None:
    path = root / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


_IMPORTS = "SELECT file_path, line_number, import_path, resolved_ref_id FROM code_imports"
_EDGES = "SELECT src_ref_id, dst_ref_id FROM edges WHERE kind = 'depends_on'"


def _rows(root: Path, sql: str, params: tuple[str, ...] = ()) -> list[tuple[object, ...]]:
    conn = sqlite3.connect(root / ".beadloom" / "beadloom.db")
    try:
        return sorted(tuple(row) for row in conn.execute(sql, params).fetchall())
    finally:
        conn.close()


def _target(root: Path, importer: str, import_path: str) -> object:
    rows = _rows(
        root,
        "SELECT resolved_ref_id FROM code_imports WHERE file_path = ? AND import_path = ?",
        (importer, import_path),
    )
    return rows[0][0] if len(rows) == 1 else rows


def _assert_same_as_fresh(root: Path, tmp_path: Path) -> None:
    fresh = tmp_path / "fresh"
    shutil.copytree(root, fresh, ignore=shutil.ignore_patterns("beadloom.db*"))
    reindex(fresh)
    assert _rows(root, _IMPORTS) == _rows(fresh, _IMPORTS)
    assert _rows(root, _EDGES) == _rows(fresh, _EDGES)


#: A Go service whose ledger imports berths under a module path go.mod does not declare yet.
_GO_NODES = {"berths": "internal/berths", "ledger": "internal/ledger"}
_GO_CONFIG = "scan_paths:\n- internal\nlanguages:\n- .go\n"
_GO_FILES = {
    "go.mod": "module example.org/quay\n",
    "internal/berths/berths.go": "package berths\n",
    "internal/ledger/ledger.go": (
        'package ledger\n\nimport "example.org/harbour/internal/berths"\n'
    ),
}
_LEDGER = "internal/ledger/ledger.go"
_BERTHS_IMPORT = "example.org/harbour/internal/berths"


def _go_project(tmp_path: Path) -> Path:
    return _project(tmp_path / "project", _GO_NODES, _GO_CONFIG, _GO_FILES)


class TestAGoModEdit:
    def test_is_a_change_and_re_resolves_the_imports_it_governs(self, tmp_path: Path) -> None:
        root = _go_project(tmp_path)
        reindex(root)
        assert _target(root, _LEDGER, _BERTHS_IMPORT) is None

        _write(root, "go.mod", "module example.org/harbour\n")
        result = incremental_reindex(root)

        assert result.nothing_changed is False
        assert _target(root, _LEDGER, _BERTHS_IMPORT) == "berths"
        _assert_same_as_fresh(root, tmp_path)

    def test_is_read_once_so_the_next_run_with_no_edit_changes_nothing(
        self, tmp_path: Path
    ) -> None:
        root = _go_project(tmp_path)
        reindex(root)
        _write(root, "go.mod", "module example.org/harbour\n")
        incremental_reindex(root)

        assert incremental_reindex(root).nothing_changed is True

    def test_after_a_full_reindex_an_unedited_manifest_changes_nothing(
        self, tmp_path: Path
    ) -> None:
        root = _go_project(tmp_path)
        reindex(root)

        assert incremental_reindex(root).nothing_changed is True


class TestAPackageSwiftRemoval:
    def test_returns_the_import_to_the_folder_reading_and_equals_a_fresh_index(
        self, tmp_path: Path
    ) -> None:
        manifest = (
            "// swift-tools-version:5.9\nimport PackageDescription\n\n"
            'let package = Package(\n    name: "Tides",\n    targets: [\n'
            '        .executableTarget(name: "App"),\n'
            '        .target(name: "Core", path: "Modules/CoreKit"),\n'
            "    ]\n)\n"
        )
        root = _project(
            tmp_path / "project",
            {"app": "Sources/App", "core": "Modules/CoreKit"},
            "scan_paths:\n- Sources\n- Modules\nlanguages:\n- .swift\n",
            {
                "Package.swift": manifest,
                "Sources/App/main.swift": "import Core\n\nprint(Tide())\n",
                "Modules/CoreKit/Tide.swift": "public struct Tide {}\n",
            },
        )
        reindex(root)
        assert _target(root, "Sources/App/main.swift", "Core") == "core"

        (root / "Package.swift").unlink()
        incremental_reindex(root)

        assert _target(root, "Sources/App/main.swift", "Core") is None
        _assert_same_as_fresh(root, tmp_path)


class TestAJvmSourceSetLayoutChange:
    """A JVM package is read from the files that declare it, so a layout change moves files.

    Green before ``beadloom-jcng``: ``beadloom-nh7h`` made an incremental run resolve every
    stored import again whenever a source file moves. This case holds that for a class
    moved to another folder while its package and its importer stay as they were.
    """

    def test_a_class_moved_to_another_folder_equals_a_fresh_index(self, tmp_path: Path) -> None:
        pytest.importorskip("tree_sitter_kotlin")
        root = _project(
            tmp_path / "project",
            {name: f"src/main/kotlin/{name}" for name in ("app", "net", "io")},
            "scan_paths:\n- src\nlanguages:\n- .kt\n",
            {
                "src/main/kotlin/app/Main.kt": (
                    "package org.tides.app\n\nimport org.tides.net.Socket\n\nfun main() {}\n"
                ),
                "src/main/kotlin/net/Socket.kt": "package org.tides.net\n\nclass Socket\n",
                "src/main/kotlin/io/Stream.kt": "package org.tides.io\n\nclass Stream\n",
            },
        )
        reindex(root)
        assert _target(root, "src/main/kotlin/app/Main.kt", "org.tides.net.Socket") == "net"

        moved = root / "src/main/kotlin/io/Socket.kt"
        (root / "src/main/kotlin/net/Socket.kt").rename(moved)
        incremental_reindex(root)

        assert _target(root, "src/main/kotlin/app/Main.kt", "org.tides.net.Socket") == "io"
        _assert_same_as_fresh(root, tmp_path)


class TestAProjectWhoseImportsReadNoManifest:
    def test_reads_no_manifest_on_a_run_where_nothing_changed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The manifests are found by walking the project, which is not free on a large tree."""
        root = _project(
            tmp_path / "project",
            {"app": "src/app"},
            "scan_paths:\n- src\n",
            {"src/app/main.py": "import os\n"},
        )
        reindex(root)

        def _walked(*_args: object) -> None:
            raise AssertionError("a project with no Go or Swift import read its manifests")

        monkeypatch.setattr("beadloom.graph.import_manifests.GoModules", _walked)
        monkeypatch.setattr("beadloom.graph.import_manifests.SwiftPackages", _walked)

        assert incremental_reindex(root).nothing_changed is True
