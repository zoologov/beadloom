"""The unplaced sentence names the folders the project declared (BDL-074 G2).

``describe_unplaced`` is the one sentence ``ctx`` and the debt report print about
test files that bind to nothing. It said ``not under tests/integration/ or
tests/unit/`` for every project; with the test roots configurable that is false
for a project whose root is ``test/``, and with tests beside the code an unplaced
file is also one no node's source holds. With no recorded layout the sentence is
the one this repository has always printed.
"""

from __future__ import annotations

from dataclasses import replace

from beadloom.context_oracle.test_binding import (
    PLACEMENT_BESIDE_CODE,
    PLACEMENT_UNPLACED,
    describe_test_file_recognition,
    describe_unbound,
    describe_unplaced,
)
from beadloom.context_oracle.test_layout import layout_from_config
from tests.support.bound_tests_ledger import UNPLACED_SENTENCE


class TestTheFoldersNamed:
    def test_without_a_recorded_layout_the_sentence_is_unchanged(self) -> None:
        assert describe_unplaced({PLACEMENT_UNPLACED: 2, "mirror": 2}) == UNPLACED_SENTENCE

    def test_a_declared_root_is_named_with_its_mirrored_folders(self) -> None:
        layout, _ = layout_from_config({"tests": {"roots": ["test"], "beside_code": False}})
        assert describe_unplaced({PLACEMENT_UNPLACED: 1}, layout.recorded()) == (
            "1 of 1 test file(s) are unplaced (not under test/integration/ or test/unit/) "
            "and bind to no node"
        )

    def test_tests_beside_the_code_add_that_no_node_source_holds_them(self) -> None:
        layout, _ = layout_from_config({})
        counts = {PLACEMENT_UNPLACED: 1, PLACEMENT_BESIDE_CODE: 2}
        assert describe_unplaced(counts, layout.recorded()) == (
            "1 of 3 test file(s) are unplaced (not under __tests__/integration/, "
            "__tests__/unit/, spec/integration/, spec/unit/, test/integration/, test/unit/, "
            "tests/integration/ or tests/unit/, "
            "nor inside a node's source) and bind to no node"
        )


#: Beadloom's default patterns, as the recognition clause states them.
DEFAULT_PATTERNS_STATED = (
    "go_test (*_test.go), "
    "jest (*.test.*, *.spec.*, __tests__/**/*.[jt]s, __tests__/**/*.[jt]sx), "
    "junit (*Test.java, *Tests.java, *TestCase.java, *IT.java, *ITCase.java, *Test.kt, "
    "*Tests.kt, src/test/**/*.java, src/test/**/*.kt), "
    "pytest (test_*.py, *_test.py) or "
    "xctest (*Tests.swift, *Tests/**/*.swift)"
)


class TestWhatATestFileIsReadBy:
    """``beadloom-2mj3.15``: the clause names the patterns in force, not only their groups."""

    def test_names_every_pattern_and_where_it_is_looked_for(self) -> None:
        layout, _ = layout_from_config({})
        assert describe_test_file_recognition(layout.recorded()) == (
            f"a test file is read when its path matches a pattern of {DEFAULT_PATTERNS_STATED} "
            "under the roots tests, test, spec, __tests__ or beside a node's code"
        )

    def test_several_roots_and_no_tests_beside_the_code(self) -> None:
        layout, _ = layout_from_config(
            {"tests": {"roots": ["test", "spec"], "beside_code": False}}
        )
        assert describe_test_file_recognition(layout.recorded()) == (
            f"a test file is read when its path matches a pattern of {DEFAULT_PATTERNS_STATED} "
            "under the roots test, spec"
        )

    def test_declared_patterns_are_the_ones_named(self) -> None:
        layout, _ = layout_from_config(
            {"tests": {"patterns": {"pytest": ["test_*.py"]}, "beside_code": False}}
        )
        assert describe_test_file_recognition(layout.recorded()) == (
            "a test file is read when its path matches a pattern of pytest (test_*.py) "
            "under the roots tests, test, spec, __tests__"
        )

    def test_a_record_written_before_the_patterns_were_recorded_names_the_groups(
        self,
    ) -> None:
        layout, _ = layout_from_config({"tests": {"beside_code": False}})
        recorded = replace(layout.recorded(), patterns=())
        assert describe_test_file_recognition(recorded) == (
            "a test file is read when its path matches a pattern of go_test, jest, junit, "
            "pytest or xctest under the roots tests, test, spec, __tests__"
        )


class TestATestTreeTheProjectHas:
    def test_a_present_mirror_root_is_named_among_the_folders(self) -> None:
        layout, _ = layout_from_config({"tests": {"beside_code": False}})
        recorded = layout.recorded(present_mirror_roots=("src/test/java",))
        assert describe_unplaced({PLACEMENT_UNPLACED: 1}, recorded) == (
            "1 of 1 test file(s) are unplaced (not under __tests__/integration/, "
            "__tests__/unit/, spec/integration/, spec/unit/, src/test/java/, "
            "test/integration/, test/unit/, tests/integration/ "
            "or tests/unit/) and bind to no node"
        )
        assert describe_test_file_recognition(recorded).endswith(
            "under the roots tests, test, spec, __tests__, src/test/java"
        )


class TestTheUnboundLineOfAChange:
    """Review ``beadloom-b9ll`` m-new-2: ``mutation --changed-since`` named the default folders."""

    def test_names_the_recorded_roots_as_ctx_and_the_debt_report_do(self) -> None:
        layout, _ = layout_from_config({"tests": {"roots": ["test"]}})
        counts = {PLACEMENT_UNPLACED: 1, PLACEMENT_BESIDE_CODE: 1}
        assert describe_unbound(counts, {}, layout.recorded()) == describe_unplaced(
            counts, layout.recorded()
        )
        assert "test/unit/" in (describe_unbound(counts, {}, layout.recorded()) or "")
        assert "nor inside a node's source" in (
            describe_unbound(counts, {}, layout.recorded()) or ""
        )

    def test_without_a_recorded_layout_names_the_default_folders(self) -> None:
        assert describe_unbound({PLACEMENT_UNPLACED: 2, "mirror": 2}, {}) == UNPLACED_SENTENCE


class TestOnlyTheRootsThatExistAreNamed:
    """Third review of ``beadloom-b9ll``, nit: the sentences named every default root,
    including ones the project does not have. The record names the roots read, as it
    names the build tools' test trees; with none, it says which were looked for."""

    def test_a_project_with_only_test_is_told_about_test(self) -> None:
        layout, _ = layout_from_config({})
        recorded = layout.recorded(present_roots=("test",))
        assert describe_unplaced({PLACEMENT_UNPLACED: 1}, recorded) == (
            "1 of 1 test file(s) are unplaced (not under test/integration/ or test/unit/, "
            "nor inside a node's source) and bind to no node"
        )
        assert describe_test_file_recognition(recorded).endswith(
            "under the root test or beside a node's code"
        )

    def test_a_project_with_no_root_is_told_which_were_looked_for(self) -> None:
        layout, _ = layout_from_config({})
        recorded = layout.recorded(present_roots=())
        assert describe_test_file_recognition(recorded).endswith(
            "under no root, since none of tests, test, spec, __tests__ exists, "
            "or beside a node's code"
        )
        assert describe_unplaced({PLACEMENT_UNPLACED: 1}, recorded) == (
            "1 of 1 test file(s) are unplaced (inside no node's source) and bind to no node"
        )

    def test_a_present_test_tree_alone_is_named_as_the_root(self) -> None:
        layout, _ = layout_from_config({"tests": {"beside_code": False}})
        recorded = layout.recorded(present_mirror_roots=("src/test/java",), present_roots=())
        assert describe_test_file_recognition(recorded).endswith("under the root src/test/java")
