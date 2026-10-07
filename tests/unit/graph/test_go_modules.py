"""A Go import path mapped to the project directory of the package it names (BDL-076 B5).

Measured by B3 (``beadloom-hmqn``) on a standard Go layout: an import is written
as ``<module path>/<package directory>``, and nothing stripped the module path the
project's ``go.mod`` declares, so no Go import reached the package it names. These
tests hold the mapping on its own, over project trees written for each form: the
module prefix, ``internal/``, nested packages, a workspace of several modules, a
``replace`` to a local directory, a nested module, and the imports that must stay
unmapped because the project does not hold them (the standard library, a module
from elsewhere, a path that merely shares a segment with one of ours).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.graph.go_modules import GoModules

if TYPE_CHECKING:
    from pathlib import Path


def _tree(root: Path, files: dict[str, str]) -> GoModules:
    """Write *files* under *root* and read the project's Go modules from it."""
    for rel_path, text in files.items():
        path = root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return GoModules(root)


_PACKAGE = "package x\n"

#: The standard Go service layout: the entry point is named after the module.
_SERVICE = {
    "go.mod": "module example.org/tidewater\n\ngo 1.22\n",
    "cmd/tidewater/main.go": "package main\n",
    "internal/api/handler.go": _PACKAGE,
    "internal/catalog/catalog.go": _PACKAGE,
    "internal/catalog/search/index.go": _PACKAGE,
    "tidewater.go": "package tidewater\n",
}


class TestTheModulePrefixIsStripped:
    @pytest.fixture
    def modules(self, tmp_path: Path) -> GoModules:
        return _tree(tmp_path, _SERVICE)

    def test_an_internal_package(self, modules: GoModules) -> None:
        directory = modules.package_directory(
            "example.org/tidewater/internal/catalog", "internal/api/handler.go"
        )
        assert directory == "internal/catalog"

    def test_the_entry_point_named_after_the_module_attracts_nothing(
        self, modules: GoModules
    ) -> None:
        directory = modules.package_directory(
            "example.org/tidewater/internal/api", "cmd/tidewater/main.go"
        )
        assert directory == "internal/api"

    def test_a_nested_package(self, modules: GoModules) -> None:
        directory = modules.package_directory(
            "example.org/tidewater/internal/catalog/search", "internal/api/handler.go"
        )
        assert directory == "internal/catalog/search"

    def test_the_modules_own_root_package(self, modules: GoModules) -> None:
        assert modules.package_directory("example.org/tidewater", "cmd/tidewater/main.go") == ""


class TestAnImportTheProjectDoesNotHoldStaysUnmapped:
    @pytest.fixture
    def modules(self, tmp_path: Path) -> GoModules:
        return _tree(tmp_path, _SERVICE)

    @pytest.mark.parametrize("import_path", ["fmt", "net/http", "encoding/json"])
    def test_the_standard_library(self, modules: GoModules, import_path: str) -> None:
        assert modules.package_directory(import_path, "internal/api/handler.go") is None

    def test_a_third_party_module(self, modules: GoModules) -> None:
        directory = modules.package_directory("github.com/google/uuid", "internal/api/handler.go")
        assert directory is None

    def test_a_module_whose_path_shares_a_segment_with_a_directory(
        self, modules: GoModules
    ) -> None:
        directory = modules.package_directory(
            "github.com/acme/tidewater/internal/catalog", "internal/api/handler.go"
        )
        assert directory is None

    def test_a_module_path_that_only_begins_with_ours(self, modules: GoModules) -> None:
        directory = modules.package_directory(
            "example.org/tidewaterx/internal/catalog", "internal/api/handler.go"
        )
        assert directory is None


class TestTheGoverningModule:
    def test_is_the_nearest_go_mod_at_or_above_the_file(self, tmp_path: Path) -> None:
        modules = _tree(
            tmp_path,
            {
                "go.mod": "module example.org/app\n",
                "tools/go.mod": "module example.org/app/tools\n",
                "tools/lint/lint.go": _PACKAGE,
                "server/server.go": _PACKAGE,
            },
        )
        tools = modules.governing("tools/lint/lint.go")
        server = modules.governing("server/server.go")
        assert tools is not None
        assert (tools.path, tools.directory) == ("example.org/app/tools", "tools")
        assert server is not None
        assert (server.path, server.directory) == ("example.org/app", "")

    def test_a_file_under_no_go_mod_has_no_module_and_maps_nothing(self, tmp_path: Path) -> None:
        modules = _tree(tmp_path, {"lib/go.mod": "module example.org/lib\n", "cmd/main.go": ""})
        assert modules.governing("cmd/main.go") is None
        assert modules.package_directory("example.org/lib", "cmd/main.go") is None

    @pytest.mark.parametrize("ignored", ["testdata", "vendor", ".cache", "_old", "node_modules"])
    def test_a_go_mod_the_go_tool_ignores_is_not_a_module(
        self, tmp_path: Path, ignored: str
    ) -> None:
        modules = _tree(
            tmp_path,
            {
                "go.mod": "module example.org/app\n",
                f"{ignored}/go.mod": "module example.org/app/ignored\n",
            },
        )
        governing = modules.governing(f"{ignored}/x.go")
        assert governing is not None
        assert governing.directory == ""


    def test_a_symbolic_link_is_not_followed(self, tmp_path: Path) -> None:
        modules = _tree(
            tmp_path,
            {"go.mod": "module example.org/app\n", "tools/go.mod": "module example.org/tools\n"},
        )
        (tmp_path / "linked").symlink_to(tmp_path / "tools", target_is_directory=True)
        governing = modules.governing("linked/lint.go")
        assert governing is not None
        assert governing.directory == ""


class TestANestedModule:
    def test_owns_the_packages_below_it(self, tmp_path: Path) -> None:
        modules = _tree(
            tmp_path,
            {
                "go.mod": "module example.org/app\n",
                "tools/go.mod": "module example.org/app/tools\n",
            },
        )
        assert modules.package_directory("example.org/app/tools/lint", "main.go") == "tools/lint"

    def test_under_another_path_takes_its_directory_out_of_the_outer_module(
        self, tmp_path: Path
    ) -> None:
        """Go never looks for ``example.org/app/tools/lint`` under another module."""
        modules = _tree(
            tmp_path,
            {
                "go.mod": "module example.org/app\n",
                "tools/go.mod": "module example.org/devtools\n",
            },
        )
        assert modules.package_directory("example.org/app/tools/lint", "main.go") is None
        assert modules.package_directory("example.org/devtools/lint", "main.go") == "tools/lint"


class TestAWorkspaceOfSeveralModules:
    def test_a_module_reaches_a_package_of_another_module_it_uses(self, tmp_path: Path) -> None:
        modules = _tree(
            tmp_path,
            {
                "go.work": "go 1.22\n\nuse (\n\t./services/orders\n\t./libs/money\n)\n",
                "services/orders/go.mod": "module example.org/orders\n",
                "libs/money/go.mod": "module example.org/money\n",
            },
        )
        directory = modules.package_directory(
            "example.org/money/currency", "services/orders/api/api.go"
        )
        assert directory == "libs/money/currency"

    def test_a_module_the_workspace_uses_counts_where_the_search_does_not_look(
        self, tmp_path: Path
    ) -> None:
        modules = _tree(
            tmp_path,
            {
                "go.work": "use (\n\t./app\n\t./_labs/money // experimental\n)\n",
                "app/go.mod": "module example.org/app\n",
                "_labs/money/go.mod": "module example.org/money\n",
            },
        )
        assert modules.package_directory("example.org/money/fx", "app/main.go") == "_labs/money/fx"

    def test_a_workspace_replace_to_a_local_directory(self, tmp_path: Path) -> None:
        modules = _tree(
            tmp_path,
            {
                "go.work": "go 1.22\nuse ./app\nreplace github.com/acme/money => ./_forks/money\n",
                "app/go.mod": "module example.org/app\n",
                "_forks/money/go.mod": "module github.com/acme/money\n",
            },
        )
        directory = modules.package_directory("github.com/acme/money/fx", "app/main.go")
        assert directory == "_forks/money/fx"


class TestAReplaceDirective:
    """Each target sits in a folder the module search skips, so only the directive reaches it."""

    def test_to_a_local_path_maps_the_module_to_that_directory(self, tmp_path: Path) -> None:
        modules = _tree(
            tmp_path,
            {
                "app/go.mod": (
                    "module example.org/app\n\n"
                    "require github.com/acme/money v1.4.0\n\n"
                    "replace github.com/acme/money v1.4.0 => ../_forks/money // local fork\n"
                ),
                "_forks/money/go.mod": "module github.com/acme/money\n",
            },
        )
        directory = modules.package_directory("github.com/acme/money/fx", "app/main.go")
        assert directory == "_forks/money/fx"

    def test_in_a_block(self, tmp_path: Path) -> None:
        modules = _tree(
            tmp_path,
            {
                "app/go.mod": (
                    "module example.org/app\n\n"
                    "replace (\n"
                    "\tgithub.com/acme/money => ../_forks/money\n"
                    "\tgithub.com/acme/clock => github.com/other/clock v0.2.0\n"
                    ")\n"
                ),
                "_forks/money/go.mod": "module github.com/acme/money\n",
            },
        )
        assert modules.package_directory("github.com/acme/money", "app/main.go") == "_forks/money"

    def test_to_another_module_maps_nothing(self, tmp_path: Path) -> None:
        modules = _tree(
            tmp_path,
            {
                "go.mod": (
                    "module example.org/app\n"
                    "replace github.com/acme/clock => github.com/other/clock v0.2.0\n"
                ),
            },
        )
        assert modules.package_directory("github.com/acme/clock", "main.go") is None

    def test_to_a_directory_outside_the_project_maps_nothing(self, tmp_path: Path) -> None:
        modules = _tree(
            tmp_path / "project",
            {"go.mod": "module example.org/app\nreplace github.com/acme/money => ../../money\n"},
        )
        assert modules.package_directory("github.com/acme/money", "main.go") is None

    def test_applies_to_the_module_that_declares_it_only(self, tmp_path: Path) -> None:
        modules = _tree(
            tmp_path,
            {
                "a/go.mod": "module example.org/a\nreplace github.com/acme/money => ../_money\n",
                "b/go.mod": "module example.org/b\n",
                "_money/go.mod": "module github.com/acme/money\n",
            },
        )
        assert modules.package_directory("github.com/acme/money", "a/main.go") == "_money"
        assert modules.package_directory("github.com/acme/money", "b/main.go") is None


class TestTheGoModFileIsReadAsGoWritesIt:
    def test_a_quoted_module_path_and_comments(self, tmp_path: Path) -> None:
        modules = _tree(
            tmp_path,
            {"go.mod": '// The service.\nmodule "example.org/quay" // quoted\n\ngo 1.22\n'},
        )
        assert modules.package_directory("example.org/quay/berths", "main.go") == "berths"

    def test_a_go_mod_with_no_module_line_maps_nothing(self, tmp_path: Path) -> None:
        modules = _tree(tmp_path, {"go.mod": "go 1.22\n"})
        assert modules.package_directory("example.org/quay/berths", "main.go") is None


class TestTheManifestsTheReadingRestsOn:
    """``beadloom-jcng``: every file whose text decides an answer, so a change to one is seen."""

    def test_every_go_mod_and_go_work_with_its_text_in_path_order(self, tmp_path: Path) -> None:
        work = "go 1.22\n\nuse ./services/orders\n"
        orders = "module example.org/orders\n"
        modules = _tree(
            tmp_path,
            {
                "go.work": work,
                "services/orders/go.mod": orders,
                "services/orders/orders.go": _PACKAGE,
            },
        )

        assert modules.manifests == (("go.work", work), ("services/orders/go.mod", orders))

    def test_a_module_a_workspace_uses_where_the_search_does_not_look(
        self, tmp_path: Path
    ) -> None:
        work = "go 1.22\n\nuse ./_shared/money\n"
        money = "module example.org/money\n"
        modules = _tree(tmp_path, {"go.work": work, "_shared/money/go.mod": money})

        assert modules.manifests == (("_shared/money/go.mod", money), ("go.work", work))

    def test_a_project_with_no_go_module_rests_on_nothing(self, tmp_path: Path) -> None:
        assert _tree(tmp_path, {"main.py": "print(1)\n"}).manifests == ()
