"""The JVM source-set layout read from a project tree, and the package clusters it yields.

BDL-076 B6 (``beadloom-ujzb.15``). Measured by B3 (``beadloom-hmqn``): on a Maven or
Gradle project ``init`` made nodes of the source sets (``src/main``,
``src/main/java``, ``src/test``) and wrote ``scan_paths: [src]``, so no package was
a node and no dotted import resolved. These tests hold the layout reading on its
own, over trees written for each form: Maven and Gradle single-module builds, a
build of several modules declared in ``settings.gradle.kts`` or a parent
``pom.xml``, test-only source sets, a module mixing Java and Kotlin, a base package
that holds code, a single-package project and a deep package tree — and the trees
that must not be read as a JVM layout at all.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.onboarding.scanner.jvm_layout import (
    cluster_packages,
    jvm_package_directory,
    read_jvm_layout,
)

if TYPE_CHECKING:
    from pathlib import Path

    from beadloom.onboarding.scanner.jvm_layout import JvmLayout
    from beadloom.onboarding.scanner.types import ClusterEntry


def _tree(root: Path, paths: list[str]) -> JvmLayout:
    """Write a Java or Kotlin file at each of *paths* and read the project's layout."""
    for rel_path in paths:
        path = root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("// code\n", encoding="utf-8")
    return read_jvm_layout(root)


def _directories(clusters: dict[str, ClusterEntry]) -> dict[str, str]:
    return {name: entry["directory"] for name, entry in clusters.items()}


def _children(clusters: dict[str, ClusterEntry]) -> dict[str, dict[str, str]]:
    return {
        name: dict(entry["child_directories"])
        for name, entry in clusters.items()
        if entry["child_directories"]
    }


_SHOP = "src/main/java/org/acme/shop"

#: Maven's standard layout: the build file, three packages and a test.
_MAVEN = [
    "pom.xml",
    f"{_SHOP}/web/Controller.java",
    f"{_SHOP}/service/Orders.java",
    f"{_SHOP}/model/Item.java",
    "src/test/java/org/acme/shop/service/OrdersTest.java",
]


class TestAMavenProject:
    def test_its_source_root_is_the_production_set(self, tmp_path: Path) -> None:
        layout = _tree(tmp_path, _MAVEN)

        assert layout.production_roots == ("src/main/java",)
        assert layout.test_roots == ("src/test/java",)

    def test_its_test_tree_mirrors_the_code_tree(self, tmp_path: Path) -> None:
        layout = _tree(tmp_path, _MAVEN)

        assert layout.mirrors == {"src/test/java": "src/main/java"}

    def test_it_claims_the_top_level_src_directory(self, tmp_path: Path) -> None:
        layout = _tree(tmp_path, _MAVEN)

        assert layout.territory == frozenset({"src"})

    def test_each_package_below_the_shared_prefix_is_a_cluster(self, tmp_path: Path) -> None:
        clusters = cluster_packages(_tree(tmp_path, _MAVEN))

        assert _directories(clusters) == {
            "model": f"{_SHOP}/model",
            "service": f"{_SHOP}/service",
            "web": f"{_SHOP}/web",
        }

    def test_no_source_set_and_no_test_is_a_cluster(self, tmp_path: Path) -> None:
        clusters = cluster_packages(_tree(tmp_path, _MAVEN))

        files = [path for entry in clusters.values() for path in entry["files"]]
        assert not {"main", "test", "java", "main-java", "test-java"} & set(clusters)
        assert [path for path in files if "/src/test/" in f"/{path}"] == []

    def test_a_cluster_lists_the_files_of_its_package(self, tmp_path: Path) -> None:
        clusters = cluster_packages(_tree(tmp_path, _MAVEN))

        assert clusters["web"]["files"] == [f"{_SHOP}/web/Controller.java"]


class TestAGradleKotlinProject:
    def test_the_kotlin_set_is_the_source_root(self, tmp_path: Path) -> None:
        layout = _tree(
            tmp_path,
            [
                "build.gradle.kts",
                "settings.gradle.kts",
                "src/main/kotlin/org/acme/orchard/geo/Distance.kt",
                "src/main/kotlin/org/acme/orchard/planner/Planner.kt",
                "src/test/kotlin/org/acme/orchard/planner/PlannerTest.kt",
            ],
        )

        assert layout.production_roots == ("src/main/kotlin",)
        assert layout.mirrors == {"src/test/kotlin": "src/main/kotlin"}
        assert _directories(cluster_packages(layout)) == {
            "geo": "src/main/kotlin/org/acme/orchard/geo",
            "planner": "src/main/kotlin/org/acme/orchard/planner",
        }


class TestThePackageTree:
    def test_a_subpackage_is_a_child_of_its_top_level_package(self, tmp_path: Path) -> None:
        clusters = cluster_packages(
            _tree(
                tmp_path,
                [
                    f"{_SHOP}/web/Controller.java",
                    f"{_SHOP}/web/dto/OrderDto.java",
                    f"{_SHOP}/model/Item.java",
                ],
            ),
        )

        assert _children(clusters) == {"web": {"dto": f"{_SHOP}/web/dto"}}
        assert clusters["web"]["files"] == [
            f"{_SHOP}/web/Controller.java",
            f"{_SHOP}/web/dto/OrderDto.java",
        ]

    def test_a_base_package_holding_code_parents_the_packages_below_it(
        self, tmp_path: Path
    ) -> None:
        base = "src/main/java/com/acme/demo"
        clusters = cluster_packages(
            _tree(
                tmp_path,
                [
                    f"{base}/DemoApplication.java",
                    f"{base}/web/Controller.java",
                    f"{base}/service/Orders.java",
                ],
            ),
        )

        assert _directories(clusters) == {"demo": base}
        assert _children(clusters) == {
            "demo": {"service": f"{base}/service", "web": f"{base}/web"}
        }

    def test_a_single_package_project_is_one_cluster(self, tmp_path: Path) -> None:
        base = "src/main/java/org/acme/tool"
        clusters = cluster_packages(_tree(tmp_path, [f"{base}/Main.java", f"{base}/Options.java"]))

        assert _directories(clusters) == {"tool": base}
        assert _children(clusters) == {}

    def test_a_deep_tree_keeps_two_levels_below_the_shared_prefix(self, tmp_path: Path) -> None:
        core = "src/main/java/com/acme/billing/core"
        clusters = cluster_packages(
            _tree(
                tmp_path,
                [
                    f"{core}/domain/model/Invoice.java",
                    f"{core}/domain/model/value/Money.java",
                    f"{core}/domain/events/Issued.java",
                    f"{core}/app/web/Api.java",
                ],
            ),
        )

        assert _directories(clusters) == {"app": f"{core}/app", "domain": f"{core}/domain"}
        assert _children(clusters) == {
            "app": {"web": f"{core}/app/web"},
            "domain": {"events": f"{core}/domain/events", "model": f"{core}/domain/model"},
        }
        assert f"{core}/domain/model/value/Money.java" in clusters["domain"]["children"]["model"]


class TestABuildOfSeveralModules:
    def test_gradle_modules_each_hold_their_packages(self, tmp_path: Path) -> None:
        layout = _tree(
            tmp_path,
            [
                "settings.gradle.kts",
                "core/src/main/java/org/acme/core/model/Tree.java",
                "core/src/main/java/org/acme/core/geo/Point.java",
                "app/src/main/kotlin/org/acme/app/routing/Main.kt",
                "app/src/test/kotlin/org/acme/app/routing/MainTest.kt",
            ],
        )
        clusters = cluster_packages(layout)

        assert layout.production_roots == ("app/src/main/kotlin", "core/src/main/java")
        assert layout.mirrors == {"app/src/test/kotlin": "app/src/main/kotlin"}
        assert layout.territory == frozenset({"app", "core"})
        assert _directories(clusters) == {"app": "app", "core": "core"}
        assert _children(clusters) == {
            "app": {"routing": "app/src/main/kotlin/org/acme/app/routing"},
            "core": {
                "geo": "core/src/main/java/org/acme/core/geo",
                "model": "core/src/main/java/org/acme/core/model",
            },
        }

    def test_maven_modules_nested_in_a_folder_are_named_by_their_path(
        self, tmp_path: Path
    ) -> None:
        layout = _tree(
            tmp_path,
            [
                "pom.xml",
                "services/billing/pom.xml",
                "services/billing/src/main/java/org/acme/billing/api/Invoices.java",
                "ledger/pom.xml",
                "ledger/src/main/java/org/acme/ledger/Ledger.java",
            ],
        )
        clusters = cluster_packages(layout)

        assert layout.territory == frozenset({"ledger", "services"})
        assert _directories(clusters) == {
            "ledger": "ledger",
            "services-billing": "services/billing",
        }
        assert _children(clusters) == {
            "ledger": {"ledger": "ledger/src/main/java/org/acme/ledger"},
            "services-billing": {
                "api": "services/billing/src/main/java/org/acme/billing/api",
            },
        }

    def test_the_root_module_keeps_its_packages_at_the_top(self, tmp_path: Path) -> None:
        clusters = cluster_packages(
            _tree(
                tmp_path,
                [
                    f"{_SHOP}/web/Controller.java",
                    f"{_SHOP}/model/Item.java",
                    "plugins/audit/src/main/java/org/acme/audit/Trail.java",
                ],
            ),
        )

        assert _directories(clusters) == {
            "model": f"{_SHOP}/model",
            "plugins-audit": "plugins/audit",
            "web": f"{_SHOP}/web",
        }


class TestTestSourceSets:
    def test_test_sets_are_not_source_roots_and_mirror_the_main_set(self, tmp_path: Path) -> None:
        layout = _tree(
            tmp_path,
            [
                f"{_SHOP}/model/Item.java",
                "src/integrationTest/java/org/acme/shop/model/ItemIT.java",
                "src/testFixtures/java/org/acme/shop/model/Items.java",
                "src/it/java/org/acme/shop/model/ItemITCase.java",
            ],
        )

        assert layout.production_roots == ("src/main/java",)
        assert layout.mirrors == {
            "src/integrationTest/java": "src/main/java",
            "src/it/java": "src/main/java",
            "src/testFixtures/java": "src/main/java",
        }
        assert _directories(cluster_packages(layout)) == {"model": f"{_SHOP}/model"}

    def test_a_module_with_test_sources_only_is_claimed_but_yields_nothing(
        self, tmp_path: Path
    ) -> None:
        layout = _tree(
            tmp_path,
            [
                f"{_SHOP}/model/Item.java",
                "e2e/src/test/java/org/acme/shop/CheckoutTest.java",
            ],
        )

        assert layout.production_roots == ("src/main/java",)
        assert layout.territory == frozenset({"e2e", "src"})
        assert layout.mirrors == {}
        assert set(cluster_packages(layout)) == {"model"}


class TestAModuleMixingJavaAndKotlin:
    def test_both_language_roots_are_source_roots_with_one_shared_prefix(
        self, tmp_path: Path
    ) -> None:
        layout = _tree(
            tmp_path,
            [
                "src/main/java/org/acme/mill/legacy/Grinder.java",
                "src/main/kotlin/org/acme/mill/fresh/Sifter.kt",
                "src/test/kotlin/org/acme/mill/fresh/SifterTest.kt",
            ],
        )

        assert layout.production_roots == ("src/main/java", "src/main/kotlin")
        assert layout.mirrors == {"src/test/kotlin": "src/main/kotlin"}
        assert _directories(cluster_packages(layout)) == {
            "fresh": "src/main/kotlin/org/acme/mill/fresh",
            "legacy": "src/main/java/org/acme/mill/legacy",
        }

    def test_a_package_split_across_the_two_roots_is_two_clusters(self, tmp_path: Path) -> None:
        clusters = cluster_packages(
            _tree(
                tmp_path,
                [
                    "src/main/java/org/acme/mill/shared/Grain.java",
                    "src/main/kotlin/org/acme/mill/shared/Flour.kt",
                    "src/main/kotlin/org/acme/mill/fresh/Sifter.kt",
                ],
            ),
        )

        assert _directories(clusters) == {
            "fresh": "src/main/kotlin/org/acme/mill/fresh",
            "shared": "src/main/java/org/acme/mill/shared",
            "shared-main-kotlin": "src/main/kotlin/org/acme/mill/shared",
        }

    def test_a_test_tree_without_its_language_mirrors_the_main_set_it_has(
        self, tmp_path: Path
    ) -> None:
        layout = _tree(
            tmp_path,
            [
                "src/main/java/org/acme/mill/legacy/Grinder.java",
                "src/test/kotlin/org/acme/mill/legacy/GrinderTest.kt",
            ],
        )

        assert layout.mirrors == {"src/test/kotlin": "src/main/java"}


class TestWhatIsNotAJvmLayout:
    def test_a_python_project_has_none(self, tmp_path: Path) -> None:
        layout = _tree(tmp_path, ["pyproject.toml", "src/parcel/api/routes.py"])

        assert layout.production_roots == ()
        assert layout.territory == frozenset()
        assert cluster_packages(layout) == {}

    def test_a_fixture_under_tests_or_a_build_output_is_not_a_module(self, tmp_path: Path) -> None:
        layout = _tree(
            tmp_path,
            [
                "tests/fixtures/site/java/src/main/java/org/acme/x/X.java",
                "tests/e2e/shop/src/main/java/org/acme/w/W.java",
                "docs/sample/src/main/kotlin/org/acme/v/V.kt",
                "lib/build/generated/src/main/java/org/acme/y/Y.java",
                "lib/.gradle/src/main/java/org/acme/z/Z.java",
            ],
        )

        assert layout.production_roots == ()

    def test_a_project_inside_a_source_folder_is_not_a_module(self, tmp_path: Path) -> None:
        layout = _tree(
            tmp_path,
            [
                f"{_SHOP}/model/Item.java",
                "src/main/resources/sample/src/main/java/org/acme/s/S.java",
            ],
        )

        assert layout.production_roots == ("src/main/java",)
        assert layout.modules == ("",)

    def test_a_language_the_indexer_does_not_read_is_no_source_root(self, tmp_path: Path) -> None:
        layout = _tree(
            tmp_path,
            ["src/main/scala/org/acme/Main.scala", "src/main/groovy/org/acme/Tool.groovy"],
        )

        assert layout.production_roots == ()


class TestAnImportNamesAPackageDirectory:
    def _layout(self, tmp_path: Path) -> JvmLayout:
        return _tree(
            tmp_path,
            [
                f"{_SHOP}/model/Item.java",
                f"{_SHOP}/web/Controller.java",
                "core/src/main/kotlin/org/acme/core/geo/Point.kt",
            ],
        )

    def test_a_class_import(self, tmp_path: Path) -> None:
        layout = self._layout(tmp_path)

        assert jvm_package_directory("org.acme.shop.model.Item", layout) == f"{_SHOP}/model"

    def test_a_wildcard_and_a_static_import(self, tmp_path: Path) -> None:
        layout = self._layout(tmp_path)

        assert jvm_package_directory("org.acme.shop.model.*", layout) == (f"{_SHOP}/model")
        assert jvm_package_directory("org.acme.shop.model.Item.of", layout) == (f"{_SHOP}/model")

    def test_a_package_of_another_module(self, tmp_path: Path) -> None:
        layout = self._layout(tmp_path)

        assert jvm_package_directory("org.acme.core.geo.Point", layout) == (
            "core/src/main/kotlin/org/acme/core/geo"
        )

    def test_a_third_party_import_sharing_a_segment_names_nothing(self, tmp_path: Path) -> None:
        layout = self._layout(tmp_path)

        assert jvm_package_directory("org.springframework.web.Foo", layout) is None
        assert jvm_package_directory("org.acme.Missing", layout) is None
