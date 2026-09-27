"""A test file binds to the node that owns the code its path mirrors (BDL-074 C1).

The binding is pure: it reads a test file's path, the code files the index holds,
the scan paths and the nodes' sources, and answers which node the test belongs to
and how it was placed. Nothing here touches a disk or an index, so every case is
stated as data.
"""

from __future__ import annotations

import pytest

from beadloom.context_oracle.test_binding import (
    PLACEMENT_MIRROR,
    PLACEMENT_OTHER_KIND,
    PLACEMENT_OVERRIDE,
    PLACEMENT_UNOWNED,
    PLACEMENT_UNPLACED,
    bind_test_file,
    is_test_file,
    summarize_tests,
    union_over_descendants,
)
from beadloom.context_oracle.test_file_reader import count_test_functions, read_test_file
from beadloom.infrastructure.repository import most_specific_owner

#: A src-layout project: one package, a domain directory, a feature package and
#: a single-file component.
CODE_FILES = frozenset(
    {
        "src/app/__init__.py",
        "src/app/graph/__init__.py",
        "src/app/graph/loader.py",
        "src/app/graph/diff.py",
        "src/app/graph/rules/__init__.py",
        "src/app/graph/rules/engine.py",
        "src/app/cli.py",
    }
)
SCAN_PATHS = ("src",)
NODE_SOURCES = (
    ("graph", "src/app/graph/"),
    ("rule-engine", "src/app/graph/rules/"),
    ("loader", "src/app/graph/loader.py"),
    ("cli", "src/app/cli.py"),
)


def _bind(path: str, overrides: tuple[tuple[str, str], ...] = ()) -> tuple[object, ...]:
    bound = bind_test_file(
        path,
        code_files=CODE_FILES,
        scan_paths=SCAN_PATHS,
        node_sources=NODE_SOURCES,
        overrides=overrides,
    )
    return bound.kind, bound.ref_id, bound.placement


class TestTheMirror:
    """`tests/<kind>/<path>/test_<name>.py` names `<package>/<path>/<name>.py`."""

    def test_a_directory_mirror_binds_to_the_node_owning_that_directory(self) -> None:
        assert _bind("tests/unit/graph/rules/test_layers.py") == (
            "unit",
            "rule-engine",
            PLACEMENT_MIRROR,
        )

    def test_the_most_specific_owner_wins_over_the_enclosing_directory(self) -> None:
        # `loader.py` has a node of its own; the `graph` directory node does not get it.
        assert _bind("tests/unit/graph/test_loader.py") == ("unit", "loader", PLACEMENT_MIRROR)

    def test_a_module_no_child_node_owns_binds_to_the_enclosing_directory_node(self) -> None:
        assert _bind("tests/integration/graph/test_diff.py") == (
            "integration",
            "graph",
            PLACEMENT_MIRROR,
        )

    def test_a_folder_named_after_a_module_mirrors_that_module(self) -> None:
        # Several test files for one module live in a folder named after it.
        assert _bind("tests/unit/graph/loader/test_edges.py") == (
            "unit",
            "loader",
            PLACEMENT_MIRROR,
        )

    def test_a_test_at_the_top_of_a_kind_folder_mirrors_the_package_root(self) -> None:
        assert _bind("tests/unit/test_cli.py") == ("unit", "cli", PLACEMENT_MIRROR)

    def test_the_package_may_be_named_in_the_mirror(self) -> None:
        assert _bind("tests/unit/app/graph/rules/test_x.py") == (
            "unit",
            "rule-engine",
            PLACEMENT_MIRROR,
        )

    def test_a_mirror_naming_no_code_path_is_unowned(self) -> None:
        assert _bind("tests/unit/nowhere/test_x.py") == ("unit", None, PLACEMENT_UNOWNED)

    def test_a_mirror_whose_code_no_node_owns_is_unowned(self) -> None:
        # `src/app/__init__.py` exists; no node's source covers the package root.
        assert _bind("tests/unit/test_something.py") == ("unit", None, PLACEMENT_UNOWNED)

    def test_a_scan_path_of_the_project_root_mirrors_its_packages(self) -> None:
        bound = bind_test_file(
            "tests/unit/pkg/test_core.py",
            code_files=frozenset({"pkg/__init__.py", "pkg/core.py"}),
            scan_paths=(".",),
            node_sources=(("core", "pkg/core.py"),),
            overrides=(),
        )
        assert (bound.ref_id, bound.placement) == ("core", PLACEMENT_MIRROR)


class TestTheLayoutNotYetReached:
    """A file outside `tests/unit/` and `tests/integration/` is not guessed at."""

    def test_a_flat_test_file_is_unplaced_and_bound_to_nothing(self) -> None:
        # The heuristic would have bound this to `loader` by its name.
        assert _bind("tests/test_loader.py") == (None, None, PLACEMENT_UNPLACED)

    def test_a_folder_that_is_not_a_kind_is_unplaced(self) -> None:
        assert _bind("tests/graph/test_loader.py") == (None, None, PLACEMENT_UNPLACED)

    @pytest.mark.parametrize("kind", ["acceptance", "self_check"])
    def test_the_kinds_bound_by_other_means_are_recorded_and_not_mirrored(self, kind: str) -> None:
        assert _bind(f"tests/{kind}/graph/test_loader.py") == (kind, None, PLACEMENT_OTHER_KIND)


class TestTheOverride:
    """A node's `tests:` prefixes, resolved by the ownership rule, and they win."""

    def test_a_declared_file_binds_a_flat_test(self) -> None:
        overrides = (("rule-engine", "tests/test_rule_engine_story.py"),)
        assert _bind("tests/test_rule_engine_story.py", overrides) == (
            None,
            "rule-engine",
            PLACEMENT_OVERRIDE,
        )

    def test_a_declared_directory_covers_the_files_beneath_it(self) -> None:
        overrides = (("cli", "tests/stories/"),)
        assert _bind("tests/stories/deep/test_a.py", overrides)[1:] == ("cli", PLACEMENT_OVERRIDE)

    def test_a_prefix_without_a_slash_is_one_file_as_a_source_is(self) -> None:
        overrides = (("cli", "tests/stories"),)
        assert _bind("tests/stories/test_a.py", overrides) == (None, None, PLACEMENT_UNPLACED)

    def test_the_override_wins_over_the_mirror(self) -> None:
        overrides = (("cli", "tests/unit/graph/test_loader.py"),)
        assert _bind("tests/unit/graph/test_loader.py", overrides) == (
            "unit",
            "cli",
            PLACEMENT_OVERRIDE,
        )

    def test_the_most_specific_declared_prefix_wins(self) -> None:
        overrides = (("graph", "tests/stories/"), ("cli", "tests/stories/cli/"))
        assert _bind("tests/stories/cli/test_a.py", overrides)[1] == "cli"


class TestOwnership:
    """The one ownership rule, as a pure function over (ref_id, source) pairs."""

    def test_the_longest_covering_prefix_owns_the_file(self) -> None:
        assert most_specific_owner(NODE_SOURCES, "src/app/graph/rules/engine.py") == "rule-engine"

    def test_a_file_source_owns_only_itself(self) -> None:
        assert most_specific_owner(NODE_SOURCES, "src/app/graph/loader_edges.py") == "graph"

    def test_a_blank_source_owns_nothing(self) -> None:
        assert most_specific_owner((("root", ""),), "src/app/cli.py") is None


class TestWhatCountsAsATest:
    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("test_loader.py", True),
            ("loader_test.py", True),
            ("conftest.py", False),
            ("helpers.py", False),
            ("test_loader.pyc", False),
        ],
    )
    def test_the_pytest_file_names(self, name: str, expected: bool) -> None:
        assert is_test_file(name) is expected

    def test_the_test_functions_pytest_collects_are_counted(self) -> None:
        text = (
            "def test_a():\n    pass\n\n"
            "async def test_b():\n    pass\n\n"
            "def helper():\n    pass\n\n"
            "class TestThing:\n"
            "    def test_c(self):\n        pass\n"
            "    def not_a_test(self):\n        pass\n\n"
            "class Helper:\n"
            "    def test_d(self):\n        pass\n"
        )
        assert count_test_functions(text) == 3

    def test_a_file_that_does_not_parse_counts_zero(self) -> None:
        assert count_test_functions("def test_a(:\n") == 0

    def test_imports_are_read_in_the_code_index_form(self) -> None:
        text = (
            "import os\n"
            "import beadloom.graph.loader as loader\n"
            "from beadloom.graph import diff\n"
            "from . import sibling\n"
            "from .helpers import build\n"
            "def test_a():\n"
            "    from beadloom.infrastructure.db import open_db\n"
            "class TestB:\n"
            "    def test_b(self):\n"
            "        try:\n"
            "            pass\n"
            "        except ImportError:\n"
            "            import yaml\n"
        )
        assert read_test_file(text).imports == (
            (1, "os"),
            (2, "beadloom.graph.loader"),
            (3, "beadloom.graph"),
            (7, "beadloom.infrastructure.db"),
            (13, "yaml"),
        )


class TestTheParentUnion:
    """A parent's files are the union of its own and its descendants', counted once."""

    def test_a_parent_holds_its_descendants_files_once(self) -> None:
        direct = {"leaf": {"t/a.py"}, "mid": {"t/b.py"}}
        parent_children = {"root": ["mid", "other"], "mid": ["leaf"]}
        union = union_over_descendants(direct, parent_children)
        assert union["root"] == frozenset({"t/a.py", "t/b.py"})
        assert union["mid"] == frozenset({"t/a.py", "t/b.py"})
        assert union["leaf"] == frozenset({"t/a.py"})

    def test_a_part_of_cycle_terminates(self) -> None:
        union = union_over_descendants({"a": {"x.py"}}, {"a": ["b"], "b": ["a"]})
        assert union["a"] == union["b"] == frozenset({"x.py"})

    def test_a_file_reached_through_two_children_is_counted_once(self) -> None:
        summary = summarize_tests(
            frozenset({"t/a.py", "t/b.py"}), {"t/a.py": 2, "t/b.py": 3}, framework="pytest"
        )
        assert summary == {
            "framework": "pytest",
            "test_files": ["t/a.py", "t/b.py"],
            "test_count": 5,
            "coverage_estimate": "medium",
        }

    def test_a_node_with_no_bound_file_in_a_project_with_tests_is_low(self) -> None:
        assert summarize_tests(frozenset(), {}, framework="pytest")["coverage_estimate"] == "low"

    def test_a_project_with_no_test_files_says_none(self) -> None:
        assert summarize_tests(frozenset(), {}, framework="none") == {
            "framework": "none",
            "test_files": [],
            "test_count": 0,
            "coverage_estimate": "none",
        }
