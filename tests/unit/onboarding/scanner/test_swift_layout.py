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

from beadloom.onboarding.scanner.swift_layout import (
    cluster_targets,
    read_swift_layout,
    unread_swift,
)

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
        assert layout.claimed == frozenset({"Engine"})

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

    def test_the_claimed_folders_are_the_targets_own(self, tmp_path: Path) -> None:
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

        assert layout.claimed == frozenset({"Sources/Core", "Tests/CoreTests"})
        assert layout.read_folders == layout.claimed

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
        assert layout.claimed == frozenset({"Sources/App", "Packages/Kit"})
        # What the layout itself reads is each target's folder: the rest of the
        # package's folder is scanned as any other folder (the re-review's m3).
        assert layout.read_folders == frozenset(
            {"Sources/App", "Packages/Kit/Sources/Core", "Packages/Kit/Sources/Net"}
        )

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
        assert layout.claimed == frozenset()


class TestNoSwiftPackage:
    def test_a_tree_without_a_manifest_is_no_layout(self, tmp_path: Path) -> None:
        layout = _tree(tmp_path, {"Sources/Core/Route.swift": "", "src/app.py": ""})

        assert layout.production_roots == ()
        assert layout.languages == ()
        assert layout.mirrors == {}
        assert layout.claimed == frozenset()
        assert cluster_targets(layout) == {}


class TestTheSwiftInitDoesNotRead:
    """R2 finding 7: Swift outside every read ``Package.swift`` target is named, not lost."""

    def test_an_xcode_project_without_a_manifest(self, tmp_path: Path) -> None:
        layout = _tree(
            tmp_path,
            {
                "Beacon.xcodeproj/project.pbxproj": "// !$*UTF8*$!\n",
                "Beacon/Views/HomeView.swift": "",
                "Beacon/Models/Reading.swift": "",
                "src/app.py": "",
            },
        )

        unread = unread_swift(tmp_path, layout)

        assert unread.files == ("Beacon/Models/Reading.swift", "Beacon/Views/HomeView.swift")
        assert unread.xcode_projects == ("Beacon.xcodeproj",)

    def test_a_targets_files_and_the_manifests_are_read(self, tmp_path: Path) -> None:
        layout = _tree(
            tmp_path,
            {
                "Package.swift": _manifest(
                    '.target(name: "Core")', '.testTarget(name: "CoreTests")'
                ),
                "Package@swift-5.9.swift": "",
                "Sources/Core/Route.swift": "",
                "Tests/CoreTests/RouteTests.swift": "",
            },
        )

        assert unread_swift(tmp_path, layout).files == ()

    def test_an_app_beside_a_local_package_is_the_part_named(self, tmp_path: Path) -> None:
        layout = _tree(
            tmp_path,
            {
                "App.xcworkspace/contents.xcworkspacedata": "",
                "App/AppMain.swift": "",
                "Packages/Kit/Package.swift": _manifest('.target(name: "Kit")'),
                "Packages/Kit/Sources/Kit/Kit.swift": "",
            },
        )

        unread = unread_swift(tmp_path, layout)

        assert unread.files == ("App/AppMain.swift",)
        assert unread.xcode_projects == ("App.xcworkspace",)

    def test_other_peoples_code_build_output_and_skipped_folders_are_not_named(
        self, tmp_path: Path
    ) -> None:
        layout = _tree(
            tmp_path,
            {
                "Pods/Alamofire/Session.swift": "",
                "Carthage/Checkouts/X/X.swift": "",
                ".build/checkouts/Y/Y.swift": "",
                "build/Z.swift": "",
                "docs/Example.swift": "",
                "tests/fixtures/F.swift": "",
                "App/fixtures/G.swift": "",
            },
        )

        assert unread_swift(tmp_path, layout).files == ()

    def test_a_project_without_swift_has_nothing_to_name(self, tmp_path: Path) -> None:
        layout = _tree(tmp_path, {"src/app.py": "", "web/index.ts": ""})

        unread = unread_swift(tmp_path, layout)

        assert (unread.files, unread.xcode_projects) == ((), ())

    def test_the_sentence_init_says(self) -> None:
        from beadloom.onboarding.scanner.swift_layout import UnreadSwift

        assert UnreadSwift().sentence() == ""
        one = UnreadSwift(("A/B.swift",)).sentence()
        assert one.startswith("Not read: 1 .swift file outside any Package.swift target - init")
        both = UnreadSwift(("A/B.swift", "A/C.swift"), ("A.xcodeproj",)).sentence()
        assert both.startswith("Not read: 2 .swift files outside any Package.swift target")
        assert "(Xcode: A.xcodeproj)" in both
