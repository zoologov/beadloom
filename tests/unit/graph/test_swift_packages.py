"""The targets a ``Package.swift`` declares, read without running Swift (BDL-076 B7).

Measured by B3 (``beadloom-hmqn``) on a Swift Package Manager project: ``init``
knew no ``Package.swift``, so no target was a node, and a Swift ``import`` names a
module — a target — which no folder path spells. These tests hold the reading of
the manifest on its own: which calls are targets (and which look like one and are
not: a product, a dependency on a target, a commented-out line), the folder each
kind of target keeps its code in, a declared ``path:``, a test target's local
dependencies, and the module an import names, across one package or several.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.graph.swift_packages import SwiftPackages, declared_targets

if TYPE_CHECKING:
    from pathlib import Path


def _package(targets: str, *, name: str = "Kit", extra: str = "") -> str:
    return (
        "// swift-tools-version:5.9\nimport PackageDescription\n\n"
        f'let package = Package(\n    name: "{name}",\n{extra}'
        f"    targets: [\n{targets}\n    ]\n)\n"
    )


def _tree(root: Path, files: dict[str, str]) -> SwiftPackages:
    for rel_path, text in files.items():
        path = root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return SwiftPackages(root)


def _names(text: str) -> list[tuple[str, str]]:
    return [(target.name, target.kind) for target in declared_targets(text)]


class TestTheManifestsTargets:
    def test_a_single_library_target(self) -> None:
        assert _names(_package('        .target(name: "Core"),')) == [("Core", "target")]

    def test_a_library_and_an_executable(self) -> None:
        targets = '        .target(name: "Core"),\n        .executableTarget(name: "App"),'
        assert _names(_package(targets)) == [("Core", "target"), ("App", "executableTarget")]

    def test_every_kind_is_named_as_declared(self) -> None:
        targets = (
            '        .target(name: "Core"),\n'
            '        .macro(name: "CoreMacros"),\n'
            '        .plugin(name: "Lint", capability: .buildTool()),\n'
            '        .binaryTarget(name: "Crypto", path: "Crypto.xcframework"),\n'
            '        .systemLibrary(name: "CSqlite", pkgConfig: "sqlite3"),\n'
            '        .testTarget(name: "CoreTests", dependencies: ["Core"]),'
        )
        assert _names(_package(targets)) == [
            ("Core", "target"),
            ("CoreMacros", "macro"),
            ("Lint", "plugin"),
            ("Crypto", "binaryTarget"),
            ("CSqlite", "systemLibrary"),
            ("CoreTests", "testTarget"),
        ]

    def test_a_dependency_on_a_target_is_no_target_of_its_own(self) -> None:
        targets = (
            '        .target(name: "Core"),\n'
            '        .target(name: "Net", dependencies: [.target(name: "Core")]),'
        )
        assert _names(_package(targets)) == [("Core", "target"), ("Net", "target")]

    def test_a_plugin_product_is_no_target(self) -> None:
        products = '    products: [.plugin(name: "LintPlugin", targets: ["Lint"])],\n'
        targets = '        .plugin(name: "Lint", capability: .buildTool()),'
        assert _names(_package(targets, extra=products)) == [("Lint", "plugin")]

    def test_a_commented_out_target_is_not_read(self) -> None:
        targets = (
            '        .target(name: "Core"),\n'
            '        // .target(name: "Old"),\n'
            '        /* .target(name: "Older"), */'
        )
        assert _names(_package(targets)) == [("Core", "target")]

    def test_a_comment_marker_inside_a_string_is_text(self) -> None:
        targets = '        .target(name: "Core", path: "Sources//Core"),'
        assert [t.path for t in declared_targets(_package(targets))] == ["Sources//Core"]

    def test_a_name_that_is_not_a_plain_string_is_not_read(self) -> None:
        targets = '        .target(name: coreName),\n        .target(name: "\\(prefix)Net"),'
        assert _names(_package(targets)) == []

    def test_a_declared_path_is_kept(self) -> None:
        targets = (
            '        .target(\n            name: "Engine",\n            path: "Engine"\n        ),'
        )
        assert [(t.name, t.path) for t in declared_targets(_package(targets))] == [
            ("Engine", "Engine")
        ]

    def test_the_local_dependencies_of_a_target(self) -> None:
        targets = (
            '        .testTarget(name: "Checks", dependencies: [\n'
            '            "Core",\n'
            '            .target(name: "Net"),\n'
            '            .byName(name: "Store"),\n'
            '            .product(name: "Logging", package: "swift-log"),\n'
            "        ]),"
        )
        [checks] = declared_targets(_package(targets))
        assert checks.dependencies == ("Core", "Net", "Store")


class TestTheFolderOfATarget:
    def test_a_library_lives_under_sources(self, tmp_path: Path) -> None:
        packages = _tree(
            tmp_path,
            {
                "Package.swift": _package('        .target(name: "Core"),'),
                "Sources/Core/A.swift": "",
            },
        )
        [package] = packages.packages
        assert [(t.name, t.directory) for t in package.targets] == [("Core", "Sources/Core")]

    def test_the_first_predefined_source_folder_holding_the_target(self, tmp_path: Path) -> None:
        packages = _tree(
            tmp_path,
            {"Package.swift": _package('        .target(name: "Core"),'), "src/Core/A.swift": ""},
        )
        assert [t.directory for t in packages.packages[0].targets] == ["src/Core"]

    def test_tests_and_plugins_have_their_own_folders(self, tmp_path: Path) -> None:
        targets = (
            '        .testTarget(name: "CoreTests"),\n'
            '        .plugin(name: "Lint", capability: .buildTool()),'
        )
        packages = _tree(tmp_path, {"Package.swift": _package(targets)})
        assert [t.directory for t in packages.packages[0].targets] == [
            "Tests/CoreTests",
            "Plugins/Lint",
        ]

    def test_a_declared_path_is_read_from_the_package_folder(self, tmp_path: Path) -> None:
        packages = _tree(
            tmp_path,
            {
                "Packages/Kit/Package.swift": _package(
                    '        .target(name: "Engine", path: "Engine/"),'
                ),
            },
        )
        [package] = packages.packages
        assert package.directory == "Packages/Kit"
        assert [t.directory for t in package.targets] == ["Packages/Kit/Engine"]

    def test_a_path_outside_the_project_or_a_binary_has_no_folder(self, tmp_path: Path) -> None:
        targets = (
            '        .target(name: "Far", path: "../../elsewhere"),\n'
            '        .binaryTarget(name: "Crypto", path: "Crypto.xcframework"),'
        )
        packages = _tree(tmp_path, {"Package.swift": _package(targets)})
        assert [t.directory for t in packages.packages[0].targets] == [None, None]


class TestWhichManifestsAreRead:
    def test_no_manifest_no_package(self, tmp_path: Path) -> None:
        assert _tree(tmp_path, {"Sources/Core/A.swift": ""}).packages == ()

    def test_build_output_and_hidden_folders_are_not_searched(self, tmp_path: Path) -> None:
        manifest = _package('        .target(name: "Dep"),')
        packages = _tree(
            tmp_path,
            {
                ".build/checkouts/dep/Package.swift": manifest,
                ".swiftpm/x/Package.swift": manifest,
                "node_modules/x/Package.swift": manifest,
                "Package.swift": _package('        .target(name: "Core"),'),
            },
        )
        assert [p.directory for p in packages.packages] == [""]

    def test_several_packages_in_folder_order(self, tmp_path: Path) -> None:
        packages = _tree(
            tmp_path,
            {
                "Package.swift": _package('        .executableTarget(name: "App"),'),
                "Packages/Store/Package.swift": _package('        .target(name: "Store"),'),
                "Packages/Kit/Package.swift": _package('        .target(name: "Kit"),'),
            },
        )
        assert [p.directory for p in packages.packages] == ["", "Packages/Kit", "Packages/Store"]


class TestTheModuleAnImportNames:
    @pytest.fixture
    def packages(self, tmp_path: Path) -> SwiftPackages:
        root_targets = (
            '        .target(name: "Core"),\n'
            '        .executableTarget(name: "App", dependencies: ["Core", "Kit"]),\n'
            '        .binaryTarget(name: "Crypto", path: "Crypto.xcframework"),\n'
            '        .testTarget(name: "CoreTests", dependencies: ["Core"]),'
        )
        return _tree(
            tmp_path,
            {
                "Package.swift": _package(root_targets),
                "Sources/Core/A.swift": "",
                "Sources/App/main.swift": "",
                "Packages/Kit/Package.swift": _package(
                    '        .target(name: "Kit"),\n        .target(name: "Core"),'
                ),
                "Packages/Kit/Sources/Kit/K.swift": "",
                "Packages/Kit/Sources/Core/C.swift": "",
            },
        )

    def test_a_target_of_the_importers_package(self, packages: SwiftPackages) -> None:
        assert packages.module_directory("Core", "Sources/App/main.swift") == "Sources/Core"

    def test_the_importers_own_package_wins_over_another(self, packages: SwiftPackages) -> None:
        directory = packages.module_directory("Core", "Packages/Kit/Sources/Kit/K.swift")
        assert directory == "Packages/Kit/Sources/Core"

    def test_a_target_of_another_package_in_the_project(self, packages: SwiftPackages) -> None:
        assert (
            packages.module_directory("Kit", "Sources/App/main.swift")
            == "Packages/Kit/Sources/Kit"
        )

    def test_a_name_two_other_packages_declare_names_nothing(self, tmp_path: Path) -> None:
        packages = _tree(
            tmp_path,
            {
                "A/Package.swift": _package('        .target(name: "Shared"),'),
                "B/Package.swift": _package('        .target(name: "Shared"),'),
                "C/Package.swift": _package('        .target(name: "Main"),'),
            },
        )
        assert packages.module_directory("Shared", "C/Sources/Main/m.swift") is None

    @pytest.mark.parametrize("module", ["Foundation", "Logging", "Crypto", "CoreTests"])
    def test_what_is_no_source_module_of_the_project_names_nothing(
        self, packages: SwiftPackages, module: str
    ) -> None:
        assert packages.module_directory(module, "Sources/App/main.swift") is None

    def test_a_submodule_import_names_its_module(self, packages: SwiftPackages) -> None:
        assert packages.module_directory("Core.Route", "Sources/App/main.swift") == "Sources/Core"

    def test_declares_says_whether_any_manifest_names_the_module(
        self, packages: SwiftPackages
    ) -> None:
        assert packages.declares("Kit")
        assert not packages.declares("Logging")
