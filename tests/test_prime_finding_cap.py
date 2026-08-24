"""`prime` states its findings without becoming them (BDL-061 S4).

`beadloom prime` promises a compact context — "<2K tokens" in its own
documentation — and then printed **every** lint violation and **every** stale
doc, one line each, with no bound. On a clean repository that promise held by
luck: the lists were empty.

Measured here: opting this repository into `scenario-coverage` took the health
section from 0 findings to 68, and `prime` grew from ~2.6 KB to 13.1 KB — five
times its budget, in the artifact whose entire job is to fit in one.

The fix is the shape the rest of this epic uses: **bound the list, state the
count, name the command that shows the rest.** A truncated list that says how
much it truncated is honest; an unbounded one that blows the budget is not, and
neither is a silent cut.
"""

from __future__ import annotations

from typing import Any

from beadloom.onboarding.scanner.prime import MAX_LISTED_FINDINGS, _format_prime_markdown


def _dynamic(violations: int = 0, stale: int = 0) -> dict[str, Any]:
    return {
        "kind_counts": {"domain": 7, "feature": 37},
        "symbols": 1453,
        "domains": [],
        "stale_docs": [
            {"doc_path": f"docs/d{i}.md", "ref_id": f"ref-{i}"} for i in range(stale)
        ],
        "violations": [
            {"rule": "scenario-coverage", "node": f"node-{i}", "message": "no scenario binds"}
            for i in range(violations)
        ],
        "stale_count": stale,
        "violations_count": violations,
        "last_reindex": "2026-08-24T00:00:00+00:00",
    }


def _render(**kwargs: int) -> str:
    return _format_prime_markdown("proj", [], _dynamic(**kwargs))


class TestTheListIsBounded:
    def test_a_long_violation_list_is_truncated_and_says_by_how_much(self) -> None:
        text = _render(violations=68)
        listed = [line for line in text.splitlines() if line.startswith("- [scenario-coverage]")]
        assert len(listed) == MAX_LISTED_FINDINGS
        assert f"{68 - MAX_LISTED_FINDINGS} more" in text
        assert "beadloom lint" in text

    def test_a_long_stale_list_is_truncated_and_says_by_how_much(self) -> None:
        text = _render(stale=40)
        listed = [line for line in text.splitlines() if line.startswith("- docs/d")]
        assert len(listed) == MAX_LISTED_FINDINGS
        assert f"{40 - MAX_LISTED_FINDINGS} more" in text
        assert "beadloom sync-check" in text

    def test_a_short_list_is_printed_whole_with_no_note(self) -> None:
        text = _render(violations=3)
        listed = [line for line in text.splitlines() if line.startswith("- [scenario-coverage]")]
        assert len(listed) == 3
        assert "more" not in text

    def test_the_total_is_still_stated_in_full(self) -> None:
        """Truncating the list must not truncate the COUNT — that is the finding."""
        assert "68 lint violations" in _render(violations=68)

    def test_the_budget_survives_a_repository_with_many_findings(self) -> None:
        assert len(_render(violations=68, stale=40).encode("utf-8")) < 8000
