"""The surface ledger records which pairs it counted, and names the ones a run dropped.

BDL-083 S2f (``beadloom-27br``), RFC D11, BDL-UX #353. The first outside adopter's Windows
checkout counted 167 declared pairs where the macOS checkout of the same commit counted 347,
and ``.beadloom/sync-surface.json`` held two integers, so the drop was a smaller number with
no names. The ledger now carries the ``(doc, file)`` pair list beside the counts, one pair per
line so a dropped pair is one removed line in a diff, and ``compare_surface`` names the
recorded pairs the current run no longer declares.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from beadloom.doc_sync.surface_ledger import (
    compare_surface,
    ledger_path,
    read_ledger,
    write_ledger,
)

if TYPE_CHECKING:
    from pathlib import Path

_PAIRS = (
    ("backend/digest.md", "backend/src/digest/sections.py"),
    ("backend/digest.md", "backend/src/digest/__init__.py"),
    ("frontend/shared-lib.md", "frontend/src/shared/lib/percent.ts"),
)


class TestTheLedgerCarriesItsPairs:
    def test_the_written_pairs_are_read_back_sorted_and_distinct(self, tmp_path: Path) -> None:
        write_ledger(tmp_path, declared_pairs=3, declared_docs=2, pairs=[*_PAIRS, _PAIRS[0]])

        ledger = read_ledger(tmp_path)

        assert ledger is not None
        assert ledger.pairs == tuple(sorted(_PAIRS))

    def test_each_pair_is_one_line_of_the_file(self, tmp_path: Path) -> None:
        write_ledger(tmp_path, declared_pairs=3, declared_docs=2, pairs=_PAIRS)

        lines = ledger_path(tmp_path).read_text(encoding="utf-8").splitlines()

        for doc, file in _PAIRS:
            assert sum(1 for line in lines if doc in line and file in line) == 1

    def test_the_file_is_json_holding_the_counts_and_the_pairs(self, tmp_path: Path) -> None:
        write_ledger(tmp_path, declared_pairs=3, declared_docs=2, pairs=_PAIRS, recorded_at="t")

        raw = json.loads(ledger_path(tmp_path).read_text(encoding="utf-8"))

        assert raw == {
            "declared_docs": 2,
            "declared_pairs": 3,
            "pairs": [list(pair) for pair in sorted(_PAIRS)],
            "recorded_at": "t",
        }

    def test_a_ledger_recorded_before_the_pair_list_reads_with_none(self, tmp_path: Path) -> None:
        ledger_path(tmp_path).parent.mkdir(parents=True)
        ledger_path(tmp_path).write_text(
            '{"declared_docs": 2, "declared_pairs": 3, "recorded_at": ""}\n', encoding="utf-8"
        )

        ledger = read_ledger(tmp_path)

        assert ledger is not None
        assert ledger.pairs == ()


class TestADroppedPairIsNamed:
    def test_a_shrunken_surface_names_the_pair_it_dropped(self, tmp_path: Path) -> None:
        write_ledger(tmp_path, declared_pairs=3, declared_docs=2, pairs=_PAIRS)

        verdict = compare_surface(
            read_ledger(tmp_path), declared_pairs=2, declared_docs=2, pairs=_PAIRS[1:]
        )

        assert verdict.shrank is True
        assert verdict.dropped == (_PAIRS[0],)
        assert "3 → 2 pair(s)" in verdict.message
        assert f"{_PAIRS[0][0]} ↔ {_PAIRS[0][1]}" in verdict.message

    def test_an_unchanged_surface_drops_nothing(self, tmp_path: Path) -> None:
        write_ledger(tmp_path, declared_pairs=3, declared_docs=2, pairs=_PAIRS)

        verdict = compare_surface(
            read_ledger(tmp_path), declared_pairs=3, declared_docs=2, pairs=_PAIRS
        )

        assert verdict.dropped == ()
        assert verdict.message == ""

    def test_a_long_drop_names_some_pairs_and_counts_the_rest(self, tmp_path: Path) -> None:
        recorded = [(f"doc{i:02}.md", f"src/m{i:02}.py") for i in range(25)]
        write_ledger(tmp_path, declared_pairs=25, declared_docs=25, pairs=recorded)

        verdict = compare_surface(
            read_ledger(tmp_path), declared_pairs=0, declared_docs=25, pairs=()
        )

        assert len(verdict.dropped) == 25
        named = [pair for pair in recorded if f"{pair[0]} ↔ {pair[1]}" in verdict.message]
        assert 0 < len(named) < 25
        assert f"and {25 - len(named)} more" in verdict.message

    def test_a_ledger_without_a_pair_list_says_it_cannot_name_them(self, tmp_path: Path) -> None:
        write_ledger(tmp_path, declared_pairs=3, declared_docs=2)

        verdict = compare_surface(
            read_ledger(tmp_path), declared_pairs=2, declared_docs=2, pairs=_PAIRS[1:]
        )

        assert verdict.shrank is True
        assert verdict.dropped == ()
        assert "--record-surface" in verdict.message
