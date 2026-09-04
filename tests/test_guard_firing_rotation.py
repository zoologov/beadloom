"""BDL-061 bead `.56` — the firing record is bounded and loses no count.

The record was append-only with no cap and ``--liveness`` parsed it whole, so the
report's cost grew with every guarded edit. `.35` added the ``.gitignore`` entry,
which made the growth invisible rather than absent. These tests pin what rotation
may and may not cost: the parse is bounded, every count survives, and the detail
that leaves the active file is kept for one more generation rather than deleted.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from click.testing import CliRunner

from beadloom.application.guards.firing import (
    ACTIVE_FIRINGS_CAP,
    ARCHIVE_RELPATH,
    CARRIED_KIND,
    FIRINGS_RELPATH,
    read_carried,
    read_firings,
    record_firing,
)
from beadloom.application.guards.liveness import build_liveness
from beadloom.application.guards.models import GuardOutcome, GuardVerdict
from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

_START = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _record(
    root: Path, guard: str, *, index: int, outcome: GuardOutcome = GuardOutcome.PASS
) -> None:
    record_firing(
        root,
        GuardVerdict(
            guard=guard,
            outcome=outcome,
            why="a recorded evaluation",
            not_covered=("nothing beyond this guard's own question",),
        ),
        at=_START + timedelta(seconds=index),
    )


def _fill(root: Path, guard: str, count: int, *, start: int = 0) -> None:
    for index in range(start, start + count):
        _record(root, guard, index=index)


class TestTheParseIsBounded:
    """The measured problem was the cost of the report, so bound that."""

    def test_below_the_cap_nothing_rotates(self, tmp_path: Path) -> None:
        _fill(tmp_path, "working-branch", 5)
        assert len(read_firings(tmp_path)) == 5
        assert not (tmp_path / ARCHIVE_RELPATH).exists()
        assert read_carried(tmp_path).rotated == 0

    def test_three_caps_of_firings_still_parse_as_less_than_one(
        self, tmp_path: Path
    ) -> None:
        _fill(tmp_path, "working-branch", ACTIVE_FIRINGS_CAP * 3)
        assert len(read_firings(tmp_path)) < ACTIVE_FIRINGS_CAP

    def test_the_summary_line_is_not_a_firing(self, tmp_path: Path) -> None:
        """``read_firings`` needed no change to stay right: the summary names no
        guard of its own, so the existing parser already skips it."""
        _fill(tmp_path, "working-branch", ACTIVE_FIRINGS_CAP)
        text = (tmp_path / FIRINGS_RELPATH).read_text(encoding="utf-8")
        assert CARRIED_KIND in text
        assert all(record.guard == "working-branch" for record in read_firings(tmp_path))


class TestNoCountIsLost:
    """A rotation that lost a firing would turn a live guard into a false never-fired."""

    def test_the_total_survives_one_rotation(self, tmp_path: Path) -> None:
        _fill(tmp_path, "working-branch", ACTIVE_FIRINGS_CAP + 10)
        [row] = [r for r in build_liveness(tmp_path) if r.guard == "working-branch"]
        assert row.fired_count == ACTIVE_FIRINGS_CAP + 10

    def test_the_total_survives_repeated_rotation(self, tmp_path: Path) -> None:
        """The fold reads the OUTGOING summary too, so a twice-rotated firing is
        still counted once instead of resetting the total every cap."""
        total = ACTIVE_FIRINGS_CAP * 2 + 7
        _fill(tmp_path, "working-branch", total)
        [row] = [r for r in build_liveness(tmp_path) if r.guard == "working-branch"]
        assert row.fired_count == total
        assert row.carried_count == total - len(read_firings(tmp_path))

    def test_an_error_only_guard_stays_never_fired_across_rotation(
        self, tmp_path: Path
    ) -> None:
        """An ``error`` is evidence the guard ran and did NOT answer. Rotation must
        not promote it into a firing by forgetting which outcome it was."""
        for index in range(ACTIVE_FIRINGS_CAP + 1):
            _record(tmp_path, "working-branch", index=index, outcome=GuardOutcome.ERROR)
        [row] = [r for r in build_liveness(tmp_path) if r.guard == "working-branch"]
        assert row.fired_count == ACTIVE_FIRINGS_CAP + 1
        assert row.never_fired

    def test_each_guard_keeps_its_own_carried_count(self, tmp_path: Path) -> None:
        _fill(tmp_path, "working-branch", ACTIVE_FIRINGS_CAP - 100)
        _fill(tmp_path, "bead-claimed", 150, start=ACTIVE_FIRINGS_CAP)
        rows = {row.guard: row for row in build_liveness(tmp_path)}
        assert rows["working-branch"].fired_count == ACTIVE_FIRINGS_CAP - 100
        assert rows["bead-claimed"].fired_count == 150


class TestWhatRotationCosts:
    """Stated, because a cost nobody names is a cost nobody weighs."""

    def test_the_detail_is_kept_for_one_generation_then_replaced(
        self, tmp_path: Path
    ) -> None:
        _fill(tmp_path, "working-branch", ACTIVE_FIRINGS_CAP)
        first = (tmp_path / ARCHIVE_RELPATH).read_text(encoding="utf-8")
        _fill(tmp_path, "working-branch", ACTIVE_FIRINGS_CAP, start=ACTIVE_FIRINGS_CAP)
        second = (tmp_path / ARCHIVE_RELPATH).read_text(encoding="utf-8")
        assert first != second
        assert "a recorded evaluation" in second

    def test_the_carried_summary_keeps_the_first_moment_it_ever_saw(
        self, tmp_path: Path
    ) -> None:
        """"Did it ever fire" is answered exactly; only the per-firing text goes."""
        _fill(tmp_path, "working-branch", ACTIVE_FIRINGS_CAP + 1)
        summary = read_carried(tmp_path).for_guard("working-branch")
        assert summary is not None
        assert summary.first_at == _START.isoformat()

    def test_a_corrupt_summary_line_does_not_break_the_report(
        self, tmp_path: Path
    ) -> None:
        _fill(tmp_path, "working-branch", ACTIVE_FIRINGS_CAP)
        path = tmp_path / FIRINGS_RELPATH
        lines = path.read_text(encoding="utf-8").splitlines()
        lines = [
            json.dumps({"kind": CARRIED_KIND, "guards": "not a mapping"})
            if CARRIED_KIND in line
            else line
            for line in lines
        ]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        rows = {row.guard: row for row in build_liveness(tmp_path)}
        assert rows["working-branch"].fired_count == 0


class TestTheReportSaysWhereTheCountCameFrom:
    """The number is the same after rotation; the evidence behind it is not."""

    def test_the_human_report_names_the_carried_firings(self, tmp_path: Path) -> None:
        _fill(tmp_path, "working-branch", ACTIVE_FIRINGS_CAP + 1)
        result = CliRunner().invoke(
            main, ["guard", "--liveness", "--project", str(tmp_path)]
        )
        assert result.exit_code == 0, result.output
        assert "carried" in result.output, result.output

    def test_the_json_report_carries_the_count(self, tmp_path: Path) -> None:
        _fill(tmp_path, "working-branch", ACTIVE_FIRINGS_CAP + 1)
        result = CliRunner().invoke(
            main, ["guard", "--liveness", "--json", "--project", str(tmp_path)]
        )
        assert result.exit_code == 0, result.output
        rows = {row["guard"]: row for row in json.loads(result.stdout)["guards"]}
        assert rows["working-branch"]["carried_count"] == ACTIVE_FIRINGS_CAP
