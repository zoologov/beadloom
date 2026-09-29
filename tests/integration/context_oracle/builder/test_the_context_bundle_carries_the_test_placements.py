"""The context bundle carries the repository's test placements beside a node's four-key tests.

Split out of ``tests/test_ctx_and_debt_report_read_the_test_binding.py`` (BDL-074
``beadloom-2mj3.7``); ``ctx``'s rendering of the placements is under
``tests/unit/services/commands/``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.context_oracle.builder import build_context
from beadloom.context_oracle.test_binding import PLACEMENT_MIRROR, PLACEMENT_UNPLACED
from tests.support.bound_tests_ledger import open_index, write_ledger

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path

_FOUR_KEYS = {"framework", "test_files", "test_count", "coverage_estimate"}


@pytest.fixture()
def conn(tmp_path: Path) -> sqlite3.Connection:
    return open_index(tmp_path / "index.db")


class TestTheContextBundle:
    def test_carries_the_placements_beside_the_four_key_tests(
        self, conn: sqlite3.Connection
    ) -> None:
        write_ledger(conn, unplaced=True)
        bundle = build_context(conn, ["ledger"], depth=0, max_nodes=5, max_chunks=5)
        assert set(bundle["tests"]) == _FOUR_KEYS
        assert bundle["tests"]["test_files"] == ["tests/unit/ledger/test_a.py"]
        assert bundle["test_placements"] == {PLACEMENT_MIRROR: 1, PLACEMENT_UNPLACED: 1}
