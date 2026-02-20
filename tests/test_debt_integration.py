"""Tests for meta_doc_staleness integration in debt report.

Verifies that the debt report includes the new ``meta_doc_staleness`` category
when ``DebtData.meta_doc_stale_count > 0``, with correct weight application
and total score contribution.
"""

from __future__ import annotations

from beadloom.infrastructure.debt_report import (
    DebtData,
    DebtWeights,
    compute_debt_score,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _zero_data(**overrides: object) -> DebtData:
    """Build a DebtData with all counts at zero, applying overrides."""
    defaults: dict[str, object] = {
        "error_count": 0,
        "warning_count": 0,
        "undocumented_count": 0,
        "stale_count": 0,
        "untracked_count": 0,
        "oversized_count": 0,
        "high_fan_out_count": 0,
        "dormant_count": 0,
        "untested_count": 0,
        "meta_doc_stale_count": 0,
        "node_issues": {},
    }
    defaults.update(overrides)
    return DebtData(**defaults)  # type: ignore[arg-type]


# ===========================================================================
# 1. DebtData field existence
# ===========================================================================


class TestDebtDataMetaDocStaleCount:
    def test_field_exists_and_defaults_to_zero(self) -> None:
        """meta_doc_stale_count should exist on DebtData and default to 0."""
        data = _zero_data()
        assert data.meta_doc_stale_count == 0

    def test_field_accepts_positive_value(self) -> None:
        """meta_doc_stale_count can be set to a positive integer."""
        data = _zero_data(meta_doc_stale_count=7)
        assert data.meta_doc_stale_count == 7


# ===========================================================================
# 2. DebtWeights field existence
# ===========================================================================


class TestDebtWeightsMetaDocStale:
    def test_weight_exists_and_defaults_to_1_5(self) -> None:
        """meta_doc_stale weight should exist and default to 1.5."""
        weights = DebtWeights()
        assert weights.meta_doc_stale == 1.5

    def test_weight_customizable(self) -> None:
        """meta_doc_stale weight should be overridable."""
        weights = DebtWeights(meta_doc_stale=3.0)
        assert weights.meta_doc_stale == 3.0


# ===========================================================================
# 3. compute_debt_score includes meta_doc_staleness category
# ===========================================================================


class TestComputeDebtScoreMetaDocStaleness:
    def test_stale_count_produces_category(self) -> None:
        """When meta_doc_stale_count > 0, a meta_doc_staleness category appears."""
        data = _zero_data(meta_doc_stale_count=5)
        report = compute_debt_score(data)
        cat_names = {c.name for c in report.categories}
        assert "meta_doc_staleness" in cat_names

    def test_zero_stale_count_no_category(self) -> None:
        """When meta_doc_stale_count == 0, no meta_doc_staleness category."""
        data = _zero_data(meta_doc_stale_count=0)
        report = compute_debt_score(data)
        cat_names = {c.name for c in report.categories}
        assert "meta_doc_staleness" not in cat_names

    def test_weight_applied_correctly(self) -> None:
        """Score for meta_doc_staleness = count * weight."""
        data = _zero_data(meta_doc_stale_count=4)
        weights = DebtWeights(meta_doc_stale=2.0)
        report = compute_debt_score(data, weights)
        meta_cat = next(
            c for c in report.categories if c.name == "meta_doc_staleness"
        )
        assert meta_cat.score == 4 * 2.0

    def test_details_populated(self) -> None:
        """The category details should contain the stale count."""
        data = _zero_data(meta_doc_stale_count=3)
        report = compute_debt_score(data)
        meta_cat = next(
            c for c in report.categories if c.name == "meta_doc_staleness"
        )
        assert meta_cat.details["meta_doc_stale"] == 3

    def test_total_score_includes_meta_doc(self) -> None:
        """Overall debt_score should include the meta_doc_staleness contribution."""
        # Only meta_doc_staleness contributes
        data = _zero_data(meta_doc_stale_count=4)
        weights = DebtWeights(meta_doc_stale=1.5)
        report = compute_debt_score(data, weights)
        assert report.debt_score == 4 * 1.5

    def test_total_score_additive_with_other_categories(self) -> None:
        """meta_doc_staleness adds to existing category scores."""
        data = _zero_data(error_count=1, meta_doc_stale_count=2)
        weights = DebtWeights()  # rule_error=3.0, meta_doc_stale=1.5
        report = compute_debt_score(data, weights)
        expected = 1 * 3.0 + 2 * 1.5  # rule_violations + meta_doc_staleness
        assert report.debt_score == expected
