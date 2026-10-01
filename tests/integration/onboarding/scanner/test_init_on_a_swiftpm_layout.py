"""``init`` then ``reindex`` on the Swift adopter fixture: every target and import.

BDL-076 B7 (``beadloom-ujzb.16``). Measured by B3 on ``tests/fixtures/site/swift``
(``Package.swift``; ``Sources/{BeaconApp,BeaconNetwork,BeaconCore}``;
``Tests/BeaconCoreTests``): ``init`` reported ``Graph: 0 nodes, 0 edges`` and wrote
``languages: [python]`` and ``scan_paths: [src]``. Each half is held here on its
own: what ``init`` writes into the graph YAML and the config, and what ``reindex``
derives from the code through the scan paths ``init`` wrote. Below the fixture, the
quick scan is held on the forms it must leave alone: a target with no import, and
one that imports Apple frameworks only.

The expected targets and imports are read from the fixture's code and written in
:mod:`tests.support.adopter_portals`, never taken from the product.
"""

from __future__ import annotations

import shutil
import sqlite3
from typing import TYPE_CHECKING, Any

import pytest
import yaml
from click.testing import CliRunner

from beadloom.services.cli import main
from tests.support.adopter_portals import SWIFT
from tests.support.committed_project import commit_project

if TYPE_CHECKING:
    from pathlib import Path

pytest.importorskip("tree_sitter_swift")

_TEST_FILE = "Tests/BeaconCoreTests/ReadingTests.swift"
_TESTED = "Sources/BeaconCore"


def _beadloom(root: Path, *args: str) -> None:
    result = CliRunner().invoke(main, [*args, "--project", str(root)])
    assert result.exit_code == 0, result.output


@pytest.fixture
def root(tmp_path: Path) -> Path:
    """The fixture, copied, committed and initialised as an adopter does it."""
    project = tmp_path / SWIFT.project
    shutil.copytree(SWIFT.source, project)
    commit_project(project, origin=SWIFT.origin)
    _beadloom(project, "init", "--yes")
    return project


def _graph(root: Path) -> list[dict[str, Any]]:
    return [
        yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for path in sorted((root / ".beadloom" / "_graph").glob("*.yml"))
    ]


def _config(root: Path) -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load(
        (root / ".beadloom" / "config.yml").read_text(encoding="utf-8")
    )
    return loaded


def _owner_by_source(root: Path) -> dict[str, str]:
    """Each node's ref_id, keyed by its source directory without the trailing slash."""
    return {
        str(node.get("source") or "").rstrip("/"): str(node["ref_id"])
        for data in _graph(root)
        for node in data.get("nodes") or []
    }


def _expected(root: Path) -> set[tuple[str, str]]:
    owners = _owner_by_source(root)
    return {(owners[importer], owners[imported]) for importer, imported in SWIFT.imports}


def _yaml_depends_on(root: Path) -> set[tuple[str, str]]:
    return {
        (str(edge["src"]), str(edge["dst"]))
        for data in _graph(root)
        for edge in data.get("edges") or []
        if edge.get("kind") == "depends_on"
    }


def _indexed(root: Path, sql: str, *params: str) -> list[tuple[Any, ...]]:
    with sqlite3.connect(root / ".beadloom" / "beadloom.db") as conn:
        return [tuple(row) for row in conn.execute(sql, params).fetchall()]


def _indexed_depends_on(root: Path) -> set[tuple[str, str]]:
    rows = _indexed(root, "SELECT src_ref_id, dst_ref_id FROM edges WHERE kind = 'depends_on'")
    return {(str(src), str(dst)) for src, dst in rows}


def _drop_yaml_depends_on(root: Path) -> None:
    """Take every ``depends_on`` edge ``init`` wrote out of the graph YAML."""
    for path in sorted((root / ".beadloom" / "_graph").glob("*.yml")):
        data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if "edges" in data:
            data["edges"] = [e for e in data["edges"] if e.get("kind") != "depends_on"]
            path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def test_every_target_is_a_node_and_the_test_target_is_not(root: Path) -> None:
    owners = _owner_by_source(root)

    assert [module for module in SWIFT.modules if module not in owners] == []
    assert set(owners) - {""} == set(SWIFT.modules)


def test_init_writes_the_targets_folders_as_scan_paths_and_swift_as_the_language(
    root: Path,
) -> None:
    config = _config(root)

    assert config["scan_paths"] == sorted(SWIFT.modules)
    assert config["languages"] == [".swift"]


def test_init_mirrors_the_test_target_to_the_target_it_tests(root: Path) -> None:
    assert _config(root)["tests"] == {"mirrors": {"Tests/BeaconCoreTests": _TESTED}}


def test_init_writes_exactly_the_imports_into_the_graph(root: Path) -> None:
    assert _yaml_depends_on(root) == _expected(root)


def test_the_graph_after_init_and_reindex_holds_exactly_the_imports(root: Path) -> None:
    _beadloom(root, "reindex")

    assert len(_expected(root)) == 3
    assert _indexed_depends_on(root) == _expected(root)


def test_reindex_alone_derives_the_imports_from_the_code(root: Path) -> None:
    _drop_yaml_depends_on(root)
    _beadloom(root, "reindex")

    assert _indexed_depends_on(root) == _expected(root)


def test_apple_frameworks_stay_unresolved(root: Path) -> None:
    _beadloom(root, "reindex")

    unresolved = _indexed(
        root,
        "SELECT DISTINCT import_path FROM code_imports WHERE resolved_ref_id IS NULL",
    )
    resolved = _indexed(
        root,
        "SELECT DISTINCT import_path FROM code_imports WHERE resolved_ref_id IS NOT NULL",
    )

    assert {path for (path,) in resolved} == {"BeaconCore", "BeaconNetwork"}
    assert {path for (path,) in unresolved} <= {"Foundation"}


def test_the_test_binds_to_the_target_it_tests(root: Path) -> None:
    _beadloom(root, "reindex")

    bound = _indexed(root, "SELECT ref_id, placement FROM test_files WHERE path = ?", _TEST_FILE)

    assert bound == [(_owner_by_source(root)[_TESTED], "mirror")]


class TestTheQuickScanReadsASwiftImportAsATarget:
    """A Swift import names a target of the project, through the manifest, or nothing.

    A target with no import and one importing Apple frameworks only draw no edge,
    and an import of a target in a package below the root reaches that package's
    cluster, whose name no segment of the import spells.
    """

    def _edges(self, tmp_path: Path, files: dict[str, str]) -> set[tuple[str, str]]:
        from beadloom.onboarding.scanner import _quick_import_scan
        from beadloom.onboarding.scanner.swift_layout import cluster_targets, read_swift_layout

        for rel_path, text in files.items():
            path = tmp_path / rel_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        layout = read_swift_layout(tmp_path)
        clusters = cluster_targets(layout)
        refs = {name: name for name in clusters}
        edges = _quick_import_scan(tmp_path, clusters, refs, swift=layout)
        return {(e["src"], e["dst"]) for e in edges}

    def test_no_imports_and_framework_imports_draw_nothing(self, tmp_path: Path) -> None:
        manifest = (
            "import PackageDescription\n"
            'let package = Package(name: "Kit", targets: [\n'
            '    .target(name: "Bare"),\n'
            '    .target(name: "Ui"),\n'
            '    .target(name: "Foundation2"),\n'
            "])\n"
        )
        edges = self._edges(
            tmp_path,
            {
                "Package.swift": manifest,
                "Sources/Bare/Bare.swift": "public struct Bare {}\n",
                "Sources/Ui/View.swift": (
                    "import Foundation\nimport SwiftUI\nimport Combine\n\nstruct V {}\n"
                ),
                "Sources/Foundation2/F.swift": "import Foundation\n",
            },
        )

        assert edges == set()

    def test_an_import_of_a_target_in_a_package_below_the_root_reaches_that_package(
        self, tmp_path: Path
    ) -> None:
        """The module ``Core`` is no cluster's name: its package's cluster is ``Packages-Kit``."""
        root_manifest = (
            "import PackageDescription\n"
            'let package = Package(name: "App", targets: [\n'
            '    .executableTarget(name: "App"),\n'
            "])\n"
        )
        kit_manifest = (
            "import PackageDescription\n"
            'let package = Package(name: "Kit", targets: [\n'
            '    .target(name: "Core"),\n'
            "])\n"
        )
        edges = self._edges(
            tmp_path,
            {
                "Package.swift": root_manifest,
                "Sources/App/main.swift": "import Core\nimport Logging\n",
                "Packages/Kit/Package.swift": kit_manifest,
                "Packages/Kit/Sources/Core/Core.swift": "public struct Core {}\n",
            },
        )

        assert edges == {("App", "Packages-Kit")}


def test_a_swift_packages_mirrors_are_written_beside_a_jvm_trees(tmp_path: Path) -> None:
    """A declared mapping replaces the default one, so the two layouts' are written together."""
    pytest.importorskip("tree_sitter_java")
    files = {
        "Package.swift": (
            "import PackageDescription\n"
            'let package = Package(name: "Kit", targets: [\n'
            '    .target(name: "Core"),\n'
            '    .testTarget(name: "CoreTests", dependencies: ["Core"]),\n'
            "])\n"
        ),
        "Sources/Core/Core.swift": "public struct Core {}\n",
        "Tests/CoreTests/CoreTests.swift": "import XCTest\n",
        "server/src/main/java/org/acme/kit/Api.java": "package org.acme.kit;\nclass Api {}\n",
        "server/src/test/java/org/acme/kit/ApiTest.java": (
            "package org.acme.kit;\nclass ApiTest {}\n"
        ),
    }
    for rel_path, text in files.items():
        path = tmp_path / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    _beadloom(tmp_path, "init", "--yes")

    assert _config(tmp_path)["tests"] == {
        "mirrors": {
            "Tests/CoreTests": "Sources/Core",
            "server/src/test/java": "server/src/main/java",
        }
    }


def test_a_targets_folder_holding_other_code_is_still_one_node(tmp_path: Path) -> None:
    """``Sources/`` holding a script the project scan counts is no second, folder-made node."""
    files = {
        "Package.swift": (
            "import PackageDescription\n"
            'let package = Package(name: "Kit", targets: [.target(name: "WebView")])\n'
        ),
        "Sources/WebView/View.swift": "public struct View {}\n",
        "Sources/WebView/Resources/bridge.js": "export const bridge = 1;\n",
    }
    for rel_path, text in files.items():
        path = tmp_path / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    _beadloom(tmp_path, "init", "--yes")

    assert set(_owner_by_source(tmp_path)) - {""} == {"Sources/WebView"}
