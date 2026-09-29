"""The index answers how many test files each placement holds, and nothing for an older index.

Split out of ``tests/test_ctx_and_debt_report_read_the_test_binding.py`` (BDL-074
``beadloom-2mj3.7``): ``count_test_files_by_placement`` lives in
``infrastructure/repository.py``, and ``ctx`` and the debt report both read it.
"""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

import pytest

from beadloom.context_oracle.test_binding import PLACEMENT_MIRROR, PLACEMENT_UNPLACED
from beadloom.infrastructure.repository import count_test_files_by_placement
from tests.support.bound_tests_ledger import open_index, write_ledger

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture()
def conn(tmp_path: Path) -> sqlite3.Connection:
    return open_index(tmp_path / "index.db")


class TestCountTestFilesByPlacement:
    def test_counts_each_placement(self, conn: sqlite3.Connection) -> None:
        write_ledger(conn, unplaced=True)
        assert count_test_files_by_placement(conn) == {
            PLACEMENT_MIRROR: 1,
            PLACEMENT_UNPLACED: 1,
        }

    def test_an_index_older_than_the_test_tables_holds_no_count(self, tmp_path: Path) -> None:
        old = sqlite3.connect(tmp_path / "old.db")
        old.row_factory = sqlite3.Row
        assert count_test_files_by_placement(old) == {}
