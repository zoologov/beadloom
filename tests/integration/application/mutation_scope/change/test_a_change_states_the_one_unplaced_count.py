"""A change's population states the unplaced count every other surface states.

BDL-074 F1. `beadloom mutation --changed-since` said "350 of 578 test file(s) are
placed under no node" on the tree where `ctx` and `status --debt-report` said 176
were unplaced: the change counted every file bound to no node — unplaced, and the
acceptance and self-check kinds — under the word the other two use for one of them.
One definition, one number: the change states the sentence `ctx` states, and names
each other kind beside it by its count.

The runner's fallback selection was narrowed afterwards to the unplaced files alone
(`unplaced_tests`, BDL-074 G1): the kinds that bind to no node by design never
become bound, so a fallback that held them could never empty.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.application.mutation_scope import change_payload, describe_change, plan_change
from beadloom.context_oracle.test_binding import describe_unplaced
from beadloom.infrastructure.repository import count_test_files_by_placement
from tests.support.suite_index import SuiteFile, SuiteIndex, SuiteNode

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path


def _suite() -> SuiteIndex:
    """One bound, two unplaced, one unowned, one acceptance and two self-check files."""
    return SuiteIndex(
        nodes=[SuiteNode("ledger", kind="domain")],
        files=[
            SuiteFile("tests/unit/ledger/test_posting.py", ref_id="ledger"),
            SuiteFile("tests/test_flat.py", placement="unplaced", kind=None),
            SuiteFile("tests/test_other_flat.py", placement="unplaced", kind=None),
            SuiteFile("tests/unit/vault/test_vault.py", placement="unowned"),
            SuiteFile(
                "tests/acceptance/steps/test_posting_steps.py",
                placement="other_kind",
                kind="acceptance",
            ),
            *(
                SuiteFile(
                    f"tests/self_check/docs/test_{name}.py",
                    placement="other_kind",
                    kind="self_check",
                )
                for name in ("readme", "spec")
            ),
        ],
    )


def _binding_line(conn: sqlite3.Connection, project: Path) -> str:
    lines = describe_change(plan_change(project, conn, "", base="main"))
    (line,) = [line for line in lines if line.startswith("Binding:")]
    return line


class TestTheChangeStatesOneUnplacedCount:
    def test_the_unplaced_count_is_the_sentence_ctx_states(self, tmp_path: Path) -> None:
        # Arrange
        conn = _suite().build(tmp_path)
        try:
            # Act
            line = _binding_line(conn, tmp_path)
            ctx_sentence = describe_unplaced(count_test_files_by_placement(conn))
        finally:
            conn.close()

        # Assert
        assert ctx_sentence is not None
        assert ctx_sentence in line
        assert "2 of 7 test file(s) are unplaced" in line

    def test_no_file_of_another_kind_is_counted_as_placed_under_no_node(
        self, tmp_path: Path
    ) -> None:
        conn = _suite().build(tmp_path)
        try:
            line = _binding_line(conn, tmp_path)
        finally:
            conn.close()

        assert "placed under no node" not in line
        assert "6 of 7" not in line

    def test_each_other_kind_is_named_beside_it_by_its_count(self, tmp_path: Path) -> None:
        conn = _suite().build(tmp_path)
        try:
            line = _binding_line(conn, tmp_path)
        finally:
            conn.close()

        assert "1 unowned (under a mirrored folder whose code no node owns)" in line
        assert "1 acceptance step and 2 self-check file(s) bind to no node by their kind" in line

    def test_the_payload_carries_the_counts_it_states(self, tmp_path: Path) -> None:
        conn = _suite().build(tmp_path)
        try:
            payload = change_payload(plan_change(tmp_path, conn, "", base="main"))
        finally:
            conn.close()

        assert payload["test_placements"] == {
            "mirror": 1,
            "unplaced": 2,
            "unowned": 1,
            "other_kind": 3,
        }
        assert payload["other_kinds"] == {"acceptance": 1, "self_check": 2}

    def test_the_runners_fallback_is_the_unplaced_count_it_states(
        self, tmp_path: Path
    ) -> None:
        conn = _suite().build(tmp_path)
        try:
            plan = plan_change(tmp_path, conn, "", base="main")
        finally:
            conn.close()

        assert plan.unplaced_tests == ("tests/test_flat.py", "tests/test_other_flat.py")
        assert "tests/self_check/docs/test_readme.py" not in plan.unplaced_tests

    def test_a_suite_with_every_file_bound_states_no_binding_line(
        self, tmp_path: Path
    ) -> None:
        index = SuiteIndex(
            nodes=[SuiteNode("ledger", kind="domain")],
            files=[SuiteFile("tests/unit/ledger/test_posting.py", ref_id="ledger")],
        )
        conn = index.build(tmp_path)
        try:
            lines = describe_change(plan_change(tmp_path, conn, "", base="main"))
        finally:
            conn.close()

        assert not [line for line in lines if line.startswith("Binding:")]
