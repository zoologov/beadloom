"""The index answers how many test files each kind holds among those no mirror binds.

BDL-074 F1. An acceptance step file and a self-check both bind to no node by their
path, for different reasons, and a surface that counted them together could state
neither. The count is read from the ``kind`` the reindex recorded, never inferred
from a folder name.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.infrastructure.db import open_db
from beadloom.infrastructure.repository import (
    KIND_ACCEPTANCE,
    KIND_SELF_CHECK,
    count_other_kind_test_files,
    label_test_kind,
)
from tests.support.suite_index import SuiteFile, SuiteIndex

if TYPE_CHECKING:
    from pathlib import Path


class TestCountOtherKindTestFiles:
    def test_each_recorded_kind_is_counted_apart(self, tmp_path: Path) -> None:
        # Arrange
        index = SuiteIndex(
            files=[
                SuiteFile("tests/unit/a/test_a.py", ref_id="a"),
                SuiteFile("tests/test_flat.py", placement="unplaced", kind=None),
                SuiteFile("tests/acceptance/steps/test_a_steps.py", placement="other_kind",
                          kind="acceptance"),
                SuiteFile("tests/self_check/docs/test_b.py", placement="other_kind",
                          kind="self_check"),
                SuiteFile("tests/self_check/docs/test_c.py", placement="other_kind",
                          kind="self_check"),
            ]
        )
        conn = index.build(tmp_path)

        # Act
        try:
            counts = count_other_kind_test_files(conn)
        finally:
            conn.close()

        # Assert
        assert counts == {KIND_ACCEPTANCE: 1, KIND_SELF_CHECK: 2}

    def test_the_kind_is_the_recorded_one_not_the_folder(self, tmp_path: Path) -> None:
        index = SuiteIndex(
            files=[
                SuiteFile("tests/self_check/docs/test_b.py", placement="other_kind",
                          kind="acceptance"),
            ]
        )
        conn = index.build(tmp_path)
        try:
            counts = count_other_kind_test_files(conn)
        finally:
            conn.close()

        assert counts == {KIND_ACCEPTANCE: 1}

    def test_a_row_that_recorded_no_kind_is_counted_as_unrecorded(self, tmp_path: Path) -> None:
        index = SuiteIndex(
            files=[SuiteFile("tests/odd/test_b.py", placement="other_kind", kind=None)]
        )
        conn = index.build(tmp_path)
        try:
            counts = count_other_kind_test_files(conn)
        finally:
            conn.close()

        assert counts == {"unrecorded": 1}

    def test_an_index_without_the_test_tables_counts_nothing(self, tmp_path: Path) -> None:
        conn = open_db(tmp_path / "old.db")
        try:
            counts = count_other_kind_test_files(conn)
        finally:
            conn.close()

        assert counts == {}


class TestLabelTestKind:
    def test_the_two_kinds_are_named_in_words(self) -> None:
        assert label_test_kind(KIND_ACCEPTANCE) == "acceptance step"
        assert label_test_kind(KIND_SELF_CHECK) == "self-check"

    def test_a_kind_without_a_label_is_named_as_recorded(self) -> None:
        assert label_test_kind("smoke") == "smoke"
