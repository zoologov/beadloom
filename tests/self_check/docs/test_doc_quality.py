"""Self-checks of this repository's documents and published site (BDL-074 A3).

Moved out of ``tests/test_doc_quality.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

import pytest

from beadloom.doc_sync.doc_quality import (
    CHECK_NAMES,
    PENDING_IN_APPROVED,
    UNFILLED_PLACEHOLDER,
    check_documents,
)


class TestOnThisRepositorysOwnDocuments:
    @staticmethod
    @pytest.fixture(scope="class")
    def _report() -> object:
        from pathlib import Path

        from beadloom.application.doc_shape import (
            planning_documents,
            shipped_placeholders,
        )

        root = Path(__file__).resolve().parents[3]
        return check_documents(
            planning_documents(root),
            project_root=root,
            placeholders=shipped_placeholders(root),
        )

    def test_the_checks_read_this_repositorys_documents(self, _report: object) -> None:
        assert _report.documents > 100  # type: ignore[attr-defined]

    def test_every_document_falls_in_exactly_one_kind(self, _report: object) -> None:
        """The INVARIANT, not the instance (the lesson of the rewritten RFC pin).

        Pinning "BRIEF reads nothing on this repo" would redden the day the
        template gains a Goal — which is the outcome the per-kind report exists
        to produce. What must hold whatever the documents say is that the
        per-kind denominators account for the corpus: a kind that silently
        dropped documents would understate exactly the hole this is for.
        """
        report = _report  # type: ignore[attr-defined]
        assert len({c.kind for c in report.by_kind}) > 1, "one kind is not a population"
        assert sum(c.documents for c in report.by_kind) == report.documents

    def test_the_per_kind_counts_sum_to_the_global_ones(self, _report: object) -> None:
        """Two counters over one corpus must not be free to disagree (#171)."""
        report = _report  # type: ignore[attr-defined]
        for name in CHECK_NAMES:
            per_kind = sum(c.applicable.get(name, 0) for c in report.by_kind)
            assert per_kind == report.applicable[name], name

    def test_a_pending_row_in_an_approved_document_is_reported(
        self, _report: object
    ) -> None:
        """The MECHANISM, not the instance.

        This test used to assert that BDL-061's own RFC still carried four
        `Pending` rows — Q1, Q2, Q3 and Q5, each decided in CONTEXT and never
        written back. That was true when the check shipped, and the check
        reporting it is what caused the debt to be paid (commit ``2ddbcf9``),
        which then reddened this test.

        A test that pins an instance dies the moment the instance is fixed, and
        takes the coverage with it. So it now asserts that the check reads a
        real population and reports the rows it finds, whatever they are — the
        two surviving ones live in BDL-021 and BDL-034, and when those are paid
        too, the assertion still holds on an empty result because the
        population, not the finding count, is what proves the check ran.
        """
        report = _report  # type: ignore[attr-defined]
        pending = [f for f in report.findings if f.check == PENDING_IN_APPROVED]
        assert PENDING_IN_APPROVED not in report.checks_that_read_nothing, (
            "the check read no rows at all — it is unproven on this repo, "
            "which is a different fact from finding nothing"
        )
        for finding in pending:
            assert finding.path, "a finding must name the document it came from"

    def test_no_check_reads_nothing_at_all(self, _report: object) -> None:
        """A check with no applicable document here would be unproven, and the
        bead requires that to be stated rather than discovered later."""
        assert _report.checks_that_read_nothing == ()  # type: ignore[attr-defined]

    def test_an_enumerated_stub_inside_a_real_heading_is_not_a_placeholder(
        self, _report: object
    ) -> None:
        """Measured: substring matching reported "Step 1 (12.12.1): Detection"
        and two more real headings of BDL-030's RFC as unfilled placeholders."""
        unfilled = [
            f
            for f in _report.findings  # type: ignore[attr-defined]
            if f.check == UNFILLED_PLACEHOLDER
        ]
        assert unfilled == []
