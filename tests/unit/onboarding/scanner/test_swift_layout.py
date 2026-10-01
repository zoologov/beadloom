"""The Swift Package Manager layout ``init`` reads, and the target clusters it yields.

BDL-076 B7 (``beadloom-ujzb.16``). Measured by B3 (``beadloom-hmqn``): on a Swift
package ``init`` wrote 0 nodes, ``languages: [python]`` and ``scan_paths: [src]``.
These tests hold what ``init`` takes from the manifest on its own, over packages
written for each form: a single library, a library and an executable, a target with
a declared ``path:``, test targets (named after their target or not), a target with
no Swift file, plugin, macro and binary targets, a package below the root, and the
trees that must not be read as a Swift package at all.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.onboarding.scanner.swift_layout import cluster_targets, read_swift_layout

if TYPE_CHECKING:
    from pathlib import Path

    from beadloom.onboarding.scanner.swift_layout import SwiftLayout


def _manifest(*targets: str) -> str:
    body = ",\n".join(f"        {target}" for target in targets)
    return (
        "// swift-tools-version:5.9\nimport PackageDescription\n\n"
        f'let package = Package(\n    name: "Kit",\n    targets: [\n{body}\n    ]\n)\n'
    )


def _tree(root: Path, files: dict[str, str]) -> SwiftLayout:
    for rel_path, text in files.items():
        path = root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return read_swift_layout(root)


def _directories(layout: SwiftLayout) -> dict[str, str]:
    return {name: entry["directory"] for name, entry in cluster_targets(layout).items()}


class TestASinglePackageAtTheRoot:
    def test_a_single_library(self, tmp_path: Path) -> None:
        layout = _tree(
            tmp_path,
            {
                "Package.swift": _manifest('.target(name: "Core")'),
                "Sources/Core/Route.swift": "",
                "Sources/Core/Model/Stop.swift": "",
            },
        )

        assert layout.production_roots == ("Sources/Core",)
        assert layout.languages == (".swift",)
        assert layout.mirrors == {}
        clusters = cluster_targets(layout)
        assert list(clusters) == ["Core"]
        assert clusters["Core"]["files"] == [
            "Sources/Core/Model/Stop.swift",
            "Sources/Core/Route.swift",
        ]
        assert clusters["Core"]["children"] == {}

    def test_a_library_and_an_executable(self, tmp_path: Path) -> None:
        layout = _tree(
            tmp_path,
            {
                "Package.swift": _manifest(
                    '.target(name: "Core")',
                    '.executableTarget(name: "App", dependencies: ["Core"])',
                ),
                "Sources/Core/Route.swift": "",
                "Sources/App/main.swift": "",
            },
        )

        assert layout.production_roots == ("Sources/App", "Sources/Core")
        assert _directories(layout) == {"App": "Sources/App", "Core": "Sources/Core"}

    def test_a_declared_path(self, tmp_path: Path) -> None:
        layout = _tree(
            tmp_path,
            {
                "Package.swift": _manifest('.target(name: "Engine", path: "Engine")'),
                "Engine/Ignition.swift": "",
            },
        )

        assert layout.production_roots == ("Engine",)
        assert _directories(layout) == {"Engine": "Engine"}
        assert layout.territory == frozenset({"Engine"})

    def test_plugins_and_macros_are_targets_and_binaries_are_not(self, tmp_path: Path) -> None:
        layout = _tree(
            tmp_path,
            {
                "Package.swift": _manifest(
                    '.macro(name: "KitMacros")',
                    '.plugin(name: "Lint", capability: .buildTool())',
                    '.binaryTarget(name: "Crypto", path: "Crypto.xcframework")',
                    '.systemLibrary(name: "CSqlite")',
                ),
                "Sources/KitMacros/Macros.swift": "",
                "Plugins/Lint/Plugin.swift": "",
                "Crypto.xcframework/Info.plist": "",
                "Sources/CSqlite/module.modulemap": "",
            },
        )

        assert _directories(layout) == {"KitMacros": "Sources/KitMacros", "Lint": "Plugins/Lint"}

    def test_a_system_library_is_no_cluster_whatever_its_folder_holds(
        self, tmp_path: Path
    ) -> None:
        layout = _tree(
            tmp_path,
            {
                "Package.swift": _manifest('.systemLibrary(name: "CSqlite")'),
                "Sources/CSqlite/module.modulemap": "",
                "Sources/CSqlite/Shim.swift": "",
            },
        )

        assert cluster_targets(layout) == {}
        assert layout.production_roots == ()

    def test_a_target_with_no_swift_file_is_no_cluster(self, tmp_path: Path) -> None:
        layout = _tree(
            tmp_path,
            {
                "Package.swift": _manifest('.target(name: "CZip")', '.target(name: "Core")'),
                "Sources/CZip/zip.c": "",
                "Sources/Core/Route.swift": "",
            },
        )

        assert layout.production_roots == ("Sources/Core",)
        assert list(cluster_targets(layout)) == ["Core"]

    def test_the_territory_is_every_top_folder_a_target_holds(self, tmp_path: Path) -> None:
        layout = _tree(
            tmp_path,
            {
                "Package.swift": _manifest(
                    '.target(name: "Core")', '.testTarget(name: "CoreTests")'
                ),
                "Sources/Core/Route.swift": "",
                "Tests/CoreTests/RouteTests.swift": "",
            },
        )

        assert layout.territory == frozenset({"Sources", "Tests"})

    def test_a_cluster_name_already_taken_is_qualified(self, tmp_path: Path) -> None:
        layout = _tree(
            tmp_path,
            {"Package.swift": _manifest('.target(name: "api")'), "Sources/api/A.swift": ""},
        )

        assert list(cluster_targets(layout, taken={"api"})) == ["api-target"]


class TestTestTargets:
    def test_a_test_target_named_after_its_target_mirrors_it(self, tmp_path: Path) -> None:
        layout = _tree(
            tmp_path,
            {
                "Package.swift": _manifest(
                    '.target(name: "Core")',
                    '.target(name: "Net", dependencies: ["Core"])',
                    '.testTarget(name: "NetTests", dependencies: ["Net", "Core"])',
                ),
                "Sources/Core/Route.swift": "",
                "Sources/Net/Client.swift": "",
                "Tests/NetTests/ClientTests.swift": "",
            },
        )

        assert layout.mirrors == {"Tests/NetTests": "Sources/Net"}
        assert "NetTests" not in cluster_targets(layout)
        assert layout.production_roots == ("Sources/Core", "Sources/Net")

    def test_a_test_target_of_one_local_dependency_mirrors_it(self, tmp_path: Path) -> None:
        layout = _tree(
            tmp_path,
            {
                "Package.swift": _manifest(
                    '.target(name: "Engine", path: "Engine")',
                    '.testTarget(name: "SmokeChecks", dependencies: ["Engine"])',
                ),
                "Engine/Ignition.swift": "",
                "Tests/SmokeChecks/IgnitionSmoke.swift": "",
            },
        )

        assert layout.mirrors == {"Tests/SmokeChecks": "Engine"}

    def test_a_test_target_of_several_targets_mirrors_none(self, tmp_path: Path) -> None:
        layout = _tree(
            tmp_path,
            {
                "Package.swift": _manifest(
                    '.target(name: "Core")',
                    '.target(name: "Net")',
                    '.testTarget(name: "EndToEnd", dependencies: ["Core", "Net"])',
                ),
                "Sources/Core/Route.swift": "",
                "Sources/Net/Client.swift": "",
                "Tests/EndToEnd/FlowTests.swift": "",
            },
        )

        assert layout.mirrors == {}


class TestPackagesBelowTheRoot:
    def test_a_package_below_the_root_is_one_cluster_with_its_targets_as_children(
        self, tmp_path: Path
    ) -> None:
        layout = _tree(
            tmp_path,
            {
                "Package.swift": _manifest('.executableTarget(name: "App")'),
                "Sources/App/main.swift": "",
                "Packages/Kit/Package.swift": _manifest(
                    '.target(name: "Core")', '.target(name: "Net")'
                ),
                "Packages/Kit/Sources/Core/Route.swift": "",
                "Packages/Kit/Sources/Net/Client.swift": "",
            },
        )

        clusters = cluster_targets(layout)
        assert _directories(layout) == {"App": "Sources/App", "Packages-Kit": "Packages/Kit"}
        assert clusters["Packages-Kit"]["child_directories"] == {
            "Core": "Packages/Kit/Sources/Core",
            "Net": "Packages/Kit/Sources/Net",
        }
        assert layout.production_roots == (
            "Packages/Kit/Sources/Core",
            "Packages/Kit/Sources/Net",
            "Sources/App",
        )
        assert layout.territory == frozenset({"Sources", "Packages"})

    def test_packages_under_tests_docs_or_fixtures_are_not_the_projects(
        self, tmp_path: Path
    ) -> None:
        manifest = _manifest('.target(name: "Probe")')
        layout = _tree(
            tmp_path,
            {
                "tests/fixtures/swift/Package.swift": manifest,
                "tests/fixtures/swift/Sources/Probe/P.swift": "",
                "docs/sample/Package.swift": manifest,
                "docs/sample/Sources/Probe/P.swift": "",
                "examples/fixtures/Package.swift": manifest,
                "examples/fixtures/Sources/Probe/P.swift": "",
            },
        )

        assert cluster_targets(layout) == {}
        assert layout.territory == frozenset()


class TestNoSwiftPackage:
    def test_a_tree_without_a_manifest_is_no_layout(self, tmp_path: Path) -> None:
        layout = _tree(tmp_path, {"Sources/Core/Route.swift": "", "src/app.py": ""})

        assert layout.production_roots == ()
        assert layout.languages == ()
        assert layout.mirrors == {}
        assert layout.territory == frozenset()
        assert cluster_targets(layout) == {}
