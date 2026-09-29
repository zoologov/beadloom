"""``ctx``'s markdown states a node's tests in one line, and the unplaced share under it.

Split out of ``tests/test_reindex_tests.py`` and
``tests/test_ctx_and_debt_report_read_the_test_binding.py`` (BDL-074
``beadloom-2mj3.7``): the renderer lives in ``services/commands/query.py`` and is
reached through the CLI hub; a bundle written as data in, text out, so unit.
"""

from __future__ import annotations

from types import MappingProxyType

from beadloom.context_oracle.test_binding import (
    PLACEMENT_MIRROR,
    PLACEMENT_OTHER_KIND,
    PLACEMENT_UNPLACED,
)
from beadloom.services.cli import _format_markdown
from tests.support.bound_tests_ledger import UNPLACED_SENTENCE, summary_of_tests

# ---------------------------------------------------------------------------
# Markdown rendering of tests line
# ---------------------------------------------------------------------------


class TestMarkdownTestsLine:
    """Test that _format_markdown renders the Tests: line correctly."""

    def test_format_markdown_includes_tests_line(self) -> None:
        """Markdown output should contain a Tests: line when tests are present."""
        from beadloom.services.cli import _format_markdown

        bundle: dict[str, object] = {
            "version": 2,
            "focus": {"ref_id": "auth", "kind": "domain", "summary": "Auth module"},
            "graph": {"nodes": [], "edges": []},
            "text_chunks": [],
            "code_symbols": [],
            "sync_status": {"stale_docs": [], "last_reindex": None},
            "constraints": [],
            "warning": None,
            "tests": {
                "framework": "pytest",
                "test_files": [
                    "tests/test_auth.py",
                    "tests/test_auth_service.py",
                    "tests/test_auth_utils.py",
                ],
                "test_count": 15,
                "coverage_estimate": "high",
            },
        }
        md = _format_markdown(bundle)
        assert "Tests:" in md
        assert "pytest" in md
        assert "15 tests" in md
        assert "3 files" in md
        assert "high coverage" in md

    def test_format_markdown_no_tests(self) -> None:
        """Markdown output should not have Tests: line when tests is None."""
        from beadloom.services.cli import _format_markdown

        bundle: dict[str, object] = {
            "version": 2,
            "focus": {"ref_id": "auth", "kind": "domain", "summary": "Auth module"},
            "graph": {"nodes": [], "edges": []},
            "text_chunks": [],
            "code_symbols": [],
            "sync_status": {"stale_docs": [], "last_reindex": None},
            "constraints": [],
            "warning": None,
            "tests": None,
        }
        md = _format_markdown(bundle)
        assert "Tests:" not in md


def _bundle(tests: dict[str, object] | None, placements: dict[str, int]) -> dict[str, object]:
    return {
        "version": 2,
        "focus": {"ref_id": "posting", "kind": "feature", "summary": "Posting"},
        "graph": {"nodes": [], "edges": []},
        "text_chunks": [],
        "code_symbols": [],
        "sync_status": {"stale_docs": [], "last_reindex": None},
        "constraints": [],
        "warning": None,
        "tests": tests,
        "test_placements": placements,
    }


_PLACEMENTS = MappingProxyType(
    {PLACEMENT_UNPLACED: 2, PLACEMENT_MIRROR: 1, PLACEMENT_OTHER_KIND: 1}
)


_PLACEMENTS = MappingProxyType(
    {PLACEMENT_UNPLACED: 2, PLACEMENT_MIRROR: 1, PLACEMENT_OTHER_KIND: 1}
)


class TestTheContextMarkdown:
    def test_the_tests_line_is_unchanged(self) -> None:
        md = _format_markdown(_bundle(summary_of_tests([]), dict(_PLACEMENTS)))
        assert "Tests: pytest, 0 tests in 0 files (low coverage)" in md.splitlines()

    def test_states_the_unplaced_share_under_the_tests_line(self) -> None:
        lines = _format_markdown(_bundle(summary_of_tests([]), dict(_PLACEMENTS))).splitlines()
        tests_at = lines.index("Tests: pytest, 0 tests in 0 files (low coverage)")
        assert lines[tests_at + 1] == f"  {UNPLACED_SENTENCE}, so the count above can be short"

    def test_says_nothing_when_every_file_is_placed(self) -> None:
        md = _format_markdown(_bundle(summary_of_tests([]), {PLACEMENT_MIRROR: 4}))
        assert "unplaced" not in md

    def test_says_nothing_for_a_node_the_binding_does_not_cover(self) -> None:
        md = _format_markdown(_bundle(None, dict(_PLACEMENTS)))
        assert "unplaced" not in md
        assert "Tests:" not in md

    def test_a_bundle_without_placements_still_renders(self) -> None:
        bundle = _bundle(summary_of_tests([]), {})
        del bundle["test_placements"]
        assert "unplaced" not in _format_markdown(bundle)
