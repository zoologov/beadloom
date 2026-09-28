"""``ctx``'s markdown prints the unplaced sentence the bundle carries (BDL-074 G2).

The sentence names the folders of the test layout the index recorded, so it is
stated by the context builder, where the index is open, and carried in the bundle
as ``test_unplaced``. A bundle without the key — one the context cache kept from
before it existed — still gets the default layout's sentence.
"""

from __future__ import annotations

from beadloom.services.cli import _format_markdown
from tests.support.bound_tests_ledger import UNPLACED_SENTENCE, summary_of_tests

_DECLARED = (
    "1 of 1 test file(s) are unplaced (not under test/integration/ or test/unit/) "
    "and bind to no node"
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
        "test_placements": {"unplaced": 2, "mirror": 2},
        **extra,
    }


class TestTheSentenceTheBundleCarries:
    def test_the_bundles_sentence_is_printed_under_the_tests_line(self) -> None:
        lines = _format_markdown(_bundle(test_unplaced=_DECLARED)).splitlines()
        tests_at = next(i for i, line in enumerate(lines) if line.startswith("Tests: "))
        assert lines[tests_at + 1] == f"  {_DECLARED}, so the count above can be short"

    def test_a_bundle_that_states_none_prints_none(self) -> None:
        assert "unplaced" not in _format_markdown(_bundle(test_unplaced=None))

    def test_a_cached_bundle_without_the_key_states_the_default_layouts(self) -> None:
        assert f"  {UNPLACED_SENTENCE}, so" in _format_markdown(_bundle())
