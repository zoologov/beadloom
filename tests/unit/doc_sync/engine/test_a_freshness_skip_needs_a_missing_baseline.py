"""Only a ``sync-check`` population compared against no baseline licenses a freshness skip.

A self-check that the new SPEC/DOC pairs are fresh cannot run in a clean room,
which holds no baseline to compare them against (BDL-UX #258), so it skips there.
A skip is the cheapest way to make a check quiet, so the decision behind this one
is a function with its own cases: which shapes of ``sync-check --json`` output
license it. Every case is synthetic and needs no tree.

Split out of ``tests/test_bead15_s3b_coverage.py`` by node (BDL-074 E1): what is
read is ``sync-check``'s baseline vocabulary (``BASELINE_NONE``).
"""

from __future__ import annotations

from beadloom.doc_sync.engine import BASELINE_NONE
from tests.support.freshness_baseline import (
    no_baseline_skip_reason,
    pairs_have_no_freshness_baseline,
)


class TestTheFreshnessSkipIsDecidedByTheBaseline:
    """The skip above must fire in a room and in no other checkout.

    A skip is the cheapest way to make a check quiet, so the decision behind
    this one is a function with its own cases rather than a condition nobody
    exercises. Every case here is synthetic: the point is which shapes of
    ``sync-check`` output license a skip, and that question needs no tree.
    """

    @staticmethod
    def _pair(
        baseline: str, *, status: str = "unverified", ref_id: str = "sync-check"
    ) -> dict[str, object]:
        """One pair in the shape ``sync-check --json`` emits."""
        return {
            "ref_id": ref_id,
            "status": status,
            "baseline": baseline,
            "doc_path": "domains/doc-sync/features/sync-check/SPEC.md",
            "code_path": "src/beadloom/doc_sync/engine.py",
            "reason": "no_baseline" if baseline == BASELINE_NONE else "ok",
        }

    def test_a_population_compared_against_nothing_has_no_baseline(self) -> None:
        """The room's own shape: every pair unverified against nothing."""
        pairs = [self._pair(BASELINE_NONE) for _ in range(3)]

        assert pairs_have_no_freshness_baseline(pairs) is True

    def test_an_unverified_pair_with_an_index_baseline_is_not_a_missing_baseline(
        self,
    ) -> None:
        """``sibling_symbols_changed`` is a finding about the tree, not a room.

        The tree carried 34 pairs in exactly this shape when this was written. A
        decision that read ``status`` instead of ``baseline`` would skip on them
        and take the whole check down with a verdict about the environment.
        """
        pairs = [self._pair("index", status="unverified")]

        assert pairs_have_no_freshness_baseline(pairs) is False

    def test_a_stale_pair_with_a_git_baseline_is_not_a_missing_baseline(self) -> None:
        """The verdict this test exists to report still reaches the assertion."""
        pairs = [self._pair("git:HEAD", status="stale")]

        assert pairs_have_no_freshness_baseline(pairs) is False

    def test_one_baselined_pair_among_unbaselined_ones_still_answers(self) -> None:
        """A checkout that compared anything is a checkout that can be judged."""
        pairs = [
            self._pair(BASELINE_NONE),
            self._pair(BASELINE_NONE),
            self._pair("index", status="ok"),
        ]

        assert pairs_have_no_freshness_baseline(pairs) is False

    def test_an_empty_population_is_not_a_missing_baseline(self) -> None:
        """No pairs is a broken sample, and the caller must fail rather than skip."""
        assert pairs_have_no_freshness_baseline([]) is False

    def test_a_pair_that_reports_no_baseline_field_does_not_buy_a_skip(self) -> None:
        """A renamed or dropped field fails the check; it never quiets it.

        The decision reads one key. If that key ever stops being emitted, the
        wrong direction to fail in is silence.
        """
        pairs: list[dict[str, object]] = [{"ref_id": "sync-check", "status": "unverified"}]

        assert pairs_have_no_freshness_baseline(pairs) is False

    def test_the_skip_reason_names_what_would_make_the_test_run(self) -> None:
        """The constraint the suite already enforces, applied to this skip.

        ``test_no_platform_xfail_waits_for_a_runner_that_will_not_come`` forbids
        a prediction nothing can adjudicate. The same rule in this shape: a skip
        that says only "it does not run here" is the ignored red with a quieter
        colour, so the reason names the count it saw, the baselines it wants and
        the two places that supply them.
        """
        reason = no_baseline_skip_reason([self._pair(BASELINE_NONE) for _ in range(4)])

        assert "4 sampled" in reason
        assert BASELINE_NONE in reason
        assert ".git" in reason
        assert "beadloom clean-room" in reason
