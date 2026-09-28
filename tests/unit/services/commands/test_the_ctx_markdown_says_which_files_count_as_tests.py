"""``ctx``'s markdown says which files count as tests, every time (``beadloom-2mj3.15``).

Review ``beadloom-b9ll`` M-new-1: a Jest ``__tests__/`` file was read by main and not
by the binding, and nothing on ``ctx`` said so — the recognition clause was stated
only when a project had no test file at all. The bundle carries the clause as
``test_recognition``, stated by the builder against the recorded layout, and the
markdown prints it under the tests line whether or not any file is unplaced.
"""

from __future__ import annotations

from beadloom.services.cli import _format_markdown
from tests.support.bound_tests_ledger import summary_of_tests

_READ_BY = (
    "a test file is read when its path matches a pattern of pytest (test_*.py) "
    "under the root tests"
)


def _bundle(**extra: object) -> dict[str, object]:
    return {
        "version": 2,
        "focus": {"ref_id": "billing", "kind": "domain", "summary": "Billing"},
        "graph": {"nodes": [], "edges": []},
        "text_chunks": [],
        "code_symbols": [],
        "sync_status": {"stale_docs": [], "last_reindex": None},
        "constraints": [],
        "warning": None,
        "tests": summary_of_tests([]),
        "test_placements": {"mirror": 2},
        "test_unplaced": None,
        **extra,
    }


def _lines_after_tests(bundle: dict[str, object]) -> list[str]:
    lines = _format_markdown(bundle).splitlines()
    tests_at = next(i for i, line in enumerate(lines) if line.startswith("Tests: "))
    return lines[tests_at + 1 :]


class TestTheClauseIsPrinted:
    def test_under_the_tests_line_when_every_file_is_placed(self) -> None:
        assert _lines_after_tests(_bundle(test_recognition=_READ_BY))[0] == (
            "  A test file is read when its path matches a pattern of pytest (test_*.py) "
            "under the root tests"
        )

    def test_after_the_unplaced_sentence_when_there_is_one(self) -> None:
        after = _lines_after_tests(
            _bundle(test_recognition=_READ_BY, test_unplaced="1 of 3 test file(s) are unplaced")
        )
        assert after[0].startswith("  1 of 3 test file(s) are unplaced")
        assert after[1].startswith("  A test file is read when")


class TestABundleWithoutTheClause:
    def test_states_nothing_it_does_not_know(self) -> None:
        assert "is read when" not in _format_markdown(_bundle(test_recognition=None))
        assert "is read when" not in _format_markdown(_bundle())
