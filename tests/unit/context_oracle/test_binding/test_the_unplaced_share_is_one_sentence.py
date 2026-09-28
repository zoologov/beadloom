"""The binding states the unplaced share of every test file in one sentence, or says nothing.

``describe_unplaced`` is the sentence ``ctx`` and the debt report both print. Split
out of ``tests/test_ctx_and_debt_report_read_the_test_binding.py`` (BDL-074
``beadloom-2mj3.7``); counts in, a sentence out, so unit.
"""

from __future__ import annotations

from beadloom.context_oracle.test_binding import (
    PLACEMENT_MIRROR,
    PLACEMENT_OTHER_KIND,
    PLACEMENT_UNPLACED,
    describe_unplaced,
)
from tests.support.bound_tests_ledger import UNPLACED_SENTENCE


class TestDescribeUnplaced:
    def test_no_test_file_at_all_has_nothing_to_say(self) -> None:
        assert describe_unplaced({}) is None

    def test_every_file_placed_has_nothing_to_say(self) -> None:
        assert describe_unplaced({PLACEMENT_MIRROR: 3, PLACEMENT_OTHER_KIND: 1}) is None

    def test_names_the_unplaced_share_of_every_test_file(self) -> None:
        counts = {PLACEMENT_UNPLACED: 2, PLACEMENT_MIRROR: 1, PLACEMENT_OTHER_KIND: 1}
        assert describe_unplaced(counts) == UNPLACED_SENTENCE
