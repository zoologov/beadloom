"""The unplaced sentence names the folders the project declared (BDL-074 G2).

``describe_unplaced`` is the one sentence ``ctx`` and the debt report print about
test files that bind to nothing. It said ``not under tests/integration/ or
tests/unit/`` for every project; with the test roots configurable that is false
for a project whose root is ``test/``, and with tests beside the code an unplaced
file is also one no node's source holds. With no recorded layout the sentence is
the one this repository has always printed.
"""

from __future__ import annotations

from beadloom.context_oracle.test_binding import (
    PLACEMENT_BESIDE_CODE,
    PLACEMENT_UNPLACED,
    describe_test_file_recognition,
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
            "1 of 3 test file(s) are unplaced (not under tests/integration/ or tests/unit/, "
            "nor inside a node's source) and bind to no node"
        )


class TestWhatATestFileIsReadBy:
    def test_names_every_framework_and_where_it_is_looked_for(self) -> None:
        layout, _ = layout_from_config({})
        assert describe_test_file_recognition(layout.recorded()) == (
            "a test file is read when its name matches a pattern of go_test, jest or pytest "
            "under the root tests or beside a node's code"
        )

    def test_several_roots_and_no_tests_beside_the_code(self) -> None:
        layout, _ = layout_from_config(
            {"tests": {"roots": ["test", "spec"], "beside_code": False}}
        )
        assert describe_test_file_recognition(layout.recorded()) == (
            "a test file is read when its name matches a pattern of go_test, jest or pytest "
            "under the roots test, spec"
        )
