"""Self-checks of this repository's graph, rules and code structure (BDL-074 A3).

Moved out of ``tests/test_graph_summary_facts.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.graph.rules.summary_facts import summary_facts_inert_reason

if TYPE_CHECKING:
    from pathlib import Path



class TestThisRepositoryIsChecked:
    """The rule is live on Beadloom's own graph, whatever it currently reports."""

    def test_this_repository_s_summaries_state_checkable_facts(
        self, self_check_snapshot: Path
    ) -> None:
        """A rule that stood down here would prove nothing about the corrections.

        This asserts liveness, not cleanliness: the four findings this repository
        currently carries are BDL-062 `.4`'s to correct, and pinning their number
        here would make this test fail on the commit that fixes them.

        The root is the self-check snapshot (BDL-074 A1, A2): read from the
        working directory, the index was absent under the empty directory the
        suite now runs in, and the test SKIPPED instead of asserting.
        """
        from beadloom.infrastructure.db import open_db as open_index

        conn = open_index(self_check_snapshot / ".beadloom" / "beadloom.db")
        try:
            assert summary_facts_inert_reason(conn, self_check_snapshot) is None
        finally:
            conn.close()
