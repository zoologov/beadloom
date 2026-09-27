"""Self-checks of this repository's documents and published site (BDL-074 A3).

Moved out of ``tests/test_bead18_s5_relation.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

import pytest

from beadloom.infrastructure.db import open_db
from beadloom.infrastructure.doc_roots import (
    DEFAULT_KINDS,
    DEFAULT_ROOTS,
    SPACE_AS_IS,
    SPACE_TO_BE,
    SPACE_WORKING,
    resolve_doc_spaces,
)
from tests.test_bead18_s5_relation import (
    _EPICS,
    _HANDED_OUT,
    _repo_beads,
    _repo_known_refs,
    _repo_report,
)

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


def _independent_population(root: Path) -> dict[str, int]:
    """Recount the three spaces without calling anything under test.

    Kind first, then root, spelled out here rather than imported so a defect in
    the classifier cannot agree with itself.
    """
    kinds = {kind.upper(): space for space, ks in DEFAULT_KINDS.items() for kind in ks}
    found: dict[str, set[Path]] = {}
    for declared, patterns in DEFAULT_ROOTS.items():
        found[declared] = {p for pat in patterns for p in root.glob(pat) if p.is_file()}
    counts = dict.fromkeys(DEFAULT_ROOTS, 0)
    everything = {p for paths in found.values() for p in paths}
    for path in everything:
        stem = path.name.rpartition(".")[0].upper()
        space: str | None = kinds.get(stem)
        if space is None:
            space = next((s for s, paths in found.items() if path in paths), None)
        if space is not None:
            counts[space] += 1
    return counts


def _declared_in_section(text: str, known: set[str]) -> list[str]:
    """Backticked known refs under a related-files heading — recounted here."""
    import re

    refs: list[str] = []
    inside = False
    for line in text.splitlines():
        heading = re.match(r"^#{1,6}\s+(.*?)\s*$", line)
        if heading is not None:
            title = heading.group(1).lower()
            inside = any(w in title for w in ("related file", "related code", "primary ref"))
            continue
        if not inside:
            continue
        for match in re.finditer(r"`([A-Za-z0-9][A-Za-z0-9._-]*)`", line):
            if match.group(1) in known and match.group(1) not in refs:
                refs.append(match.group(1))
    return refs


@pytest.fixture(autouse=True)
def _remove_handed_out_roots() -> Iterator[None]:
    """Keep the tests independent of each other and of the machine's temp dir."""
    yield
    while _HANDED_OUT:
        shutil.rmtree(_HANDED_OUT.pop(), ignore_errors=True)


class TestTheDenominatorsAreRecomputable:
    """Every number the report prints, recounted by code that is not the code.

    A relation check reports a clean result about the work it looked at; the
    number that matters is how much work that was. `.17` reported these figures
    and this class is the independent half of A GREEN COUNT IS NOT A CHECKED
    COUNT — the count is not disputed, the denominator behind it is.
    """

    def test_the_three_populations_match_an_independent_count(
        self, self_check_snapshot: Path
    ) -> None:
        report = _repo_report(self_check_snapshot)

        assert dict(report.populations) == _independent_population(self_check_snapshot)

    def test_the_populations_are_not_trivially_zero(self, self_check_snapshot: Path) -> None:
        """The recount above is worthless if both sides are empty."""
        counts = _independent_population(self_check_snapshot)

        assert counts[SPACE_TO_BE] > 100
        assert counts[SPACE_AS_IS] > 50
        assert counts[SPACE_WORKING] > 10

    def test_the_declaring_and_unresolved_buckets_partition_the_epics(
        self, self_check_snapshot: Path
    ) -> None:
        """No epic may be in neither bucket — that is where a denominator hides."""
        report = _repo_report(self_check_snapshot)

        assert report.epics_declaring_nodes + report.epics_declaring_nothing == report.epics

    def test_the_declarations_checked_are_recountable_from_the_documents(
        self, self_check_snapshot: Path
    ) -> None:
        """``refs_checked`` recounted from the CONTEXT sections and the export."""
        beads = _repo_beads(self_check_snapshot)
        known = _repo_known_refs(self_check_snapshot)
        expected = 0
        for directory in sorted((self_check_snapshot / _EPICS).iterdir()):
            document = directory / "CONTEXT.md"
            if not document.is_file():
                document = directory / "BRIEF.md"
            if not document.is_file():
                continue
            if not any(s == "closed" for s in beads.get(directory.name, ())):
                continue
            expected += len(_declared_in_section(document.read_text(encoding="utf-8"), known))

        assert _repo_report(self_check_snapshot).refs_checked == expected

    def test_the_epics_with_closed_beads_are_recountable_from_the_export(
        self, self_check_snapshot: Path
    ) -> None:
        beads = _repo_beads(self_check_snapshot)
        report = _repo_report(self_check_snapshot)
        closed = [key for key, statuses in beads.items() if "closed" in statuses]

        assert report.epics_with_closed_beads == sum(
            1 for key in closed if (self_check_snapshot / _EPICS / key).is_dir()
        )

    def test_the_relation_reports_that_it_related_something(
        self, self_check_snapshot: Path
    ) -> None:
        """The premise of every count above: it is not a vacuous run."""
        assert _repo_report(self_check_snapshot).relation_checked is True


class TestAnExcusedPairSaysSo:
    """`_sync_summary`'s docstring is the specification the new verdict broke.

    It promises a line that says how many pairs were checked and found fresh and
    how many could not be checked at all, because a bare ``N pair(s) fresh`` was
    true of a run in which six pairs had just been deleted (BDL-UX #174). The
    `exempt` verdict is in neither half of that arithmetic.
    """


    def test_the_shipped_layout_excuses_no_pair_at_all(self, self_check_snapshot: Path) -> None:
        """Measured, and it is why the omission has been invisible.

        ``index_docs`` walks the docs directory alone, so a document outside it
        never enters ``sync_state``. The shipped ``ACTIVE.md`` lives under the
        planning tree, so the shipped exemption excuses nothing here: freshness
        never looked at those files. The report nonetheless prints "55 WORKING
        document(s) exempt", which counts documents rather than excused pairs —
        a true sentence about a population that was never in the check.
        """
        report = _repo_report(self_check_snapshot)
        # The snapshot's index (BDL-074 A1, A2): read as found on disk, the answer
        # depended on the last reindex, and without one the leg skipped.
        conn = open_db(self_check_snapshot / ".beadloom" / "beadloom.db")
        pairs = conn.execute("SELECT doc_path FROM sync_state").fetchall()
        spaces = resolve_doc_spaces(self_check_snapshot)
        excused = [p for (p,) in pairs if spaces.space_of(str(p)) == SPACE_WORKING]
        conn.close()

        assert report.working_documents > 0
        assert excused == []
