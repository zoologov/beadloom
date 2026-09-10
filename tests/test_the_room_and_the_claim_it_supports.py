"""BDL-068 S6 — the clean room's own verdict, and the population it did not enter.

``beadloom-uzck``, the last dev bead of this slice, measured the epic's subject
inside the instrument the epic used to verify everything else. ``beadloom ci`` in
its room reported ``sync-check WARN: 0 pair(s) fresh, 450 NOT VERIFIED (no
baseline — index rebuilt)``, while the same gate on the tree found 3 stale pairs
that bead's own change had created. Roughly forty "green in a clean room" claims
were written in this epic, and every one of them carried a doc-freshness step
whose population was zero.

**The judgement this module records, because a test cannot hold all of it.**

*The instrument is honest and the claim is not.* ``sync-check`` states ``0 pair(s)
fresh, N NOT VERIFIED`` and the step's own status word is ``WARN``, never
``PASS``. What erases it is ``rc 0`` plus the phrase: a reader who takes "green in
a clean room" as a verdict has taken a word the run never used.

*The room should not carry a baseline.* Carrying ``.git`` or the tree's index
would import the tree's own freshness state into a room built to exclude it,
which is BDL-UX #243 in the other direction — a room measuring something that did
not come from ``HEAD`` plus the carried files. The freshness fact is a
relationship between a document and a commit, and a room that has no commits
cannot hold one truthfully.

*The claim must name the population, and the room should hand it over.* This
epic's own constraint is that the unresolved population is part of every answer,
and the room states its limit as a CAUSE — "no .git, so a freshness check inside
it has no baseline" — where the number is the form that survives being skimmed.
The command already knows the project root, so ``0 of 450`` is derivable where the
caveat is printed. That is ``FINDING BDL-068.S6-6``.

The ``xfail(strict=True)`` convention is ``.18``'s and ``.22``'s: a finding stated
only in prose is a finding nobody re-measures.
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import pytest

from beadloom.application.gate import GateStep, _sync_summary
from beadloom.application.waves.clean_room import build_room
from beadloom.doc_sync.engine import STATUS_OK, STATUS_UNVERIFIED
from beadloom.doc_sync.surface_ledger import SurfaceVerdict

if TYPE_CHECKING:
    from pathlib import Path

BEAD = "beadloom-s6.69"


def _repo(root: Path) -> Path:
    """A one-commit repository, the smallest thing a room can be built from."""
    root.mkdir(parents=True)
    (root / "src").mkdir()
    (root / "src" / "thing.py").write_text("VALUE = 1\n", encoding="utf-8")
    for args in (
        ["init", "-q", "-b", "main"],
        ["config", "user.email", "t@example.invalid"],
        ["config", "user.name", "T"],
    ):
        subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)  # noqa: S603, S607
    subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)  # noqa: S607
    subprocess.run(
        ["git", "commit", "-q", "-m", "base"],  # noqa: S607
        cwd=root,
        check=True,
        capture_output=True,
    )
    return root


def _pairs(fresh: int, unverified: int) -> list[dict[str, object]]:
    """A ``check_sync`` result set with the two populations this module weighs."""
    rows: list[dict[str, object]] = [
        {"status": STATUS_OK, "code_path": f"src/fresh{n}.py", "doc_path": f"d{n}.md"}
        for n in range(fresh)
    ]
    rows += [
        {
            "status": STATUS_UNVERIFIED,
            "code_path": f"src/unverified{n}.py",
            "doc_path": f"u{n}.md",
        }
        for n in range(unverified)
    ]
    return rows


_NO_SURFACE = SurfaceVerdict(recorded=True, shrank=False, message="", headline="")


class TestTheGateSaysWhatItCouldNotEnter:
    """The honest half, held where it already works.

    Boundary guards written after the behaviour. They exist because the erasure
    happened downstream of them, and a later simplification of either line would
    remove the only place the population is stated at all.
    """

    def test_a_run_with_no_baseline_reports_no_fresh_pair_and_names_the_rest(
        self,
    ) -> None:
        summary = _sync_summary(_pairs(fresh=0, unverified=450), _pairs(0, 450), _NO_SURFACE)
        assert summary.startswith("0 pair(s) fresh")
        assert "450 NOT VERIFIED (no baseline — index rebuilt)" in summary

    def test_the_step_that_verified_nothing_is_not_called_pass(self) -> None:
        """``unverifiable is not clean`` — the word the room's verdict never quotes."""
        step = GateStep("sync-check", passed=True, not_verified=True, summary="0 pair(s) fresh")
        assert step.status == "WARN"

    def test_a_run_with_a_baseline_states_the_population_it_did_enter(self) -> None:
        """The control: the same line on a tree that has one names the pairs."""
        summary = _sync_summary(_pairs(fresh=450, unverified=0), [], _NO_SURFACE)
        assert summary == "450 pair(s) fresh"

    def test_a_partial_baseline_states_both_populations_in_one_line(self) -> None:
        summary = _sync_summary(_pairs(fresh=3, unverified=447), _pairs(0, 447), _NO_SURFACE)
        assert "3 pair(s) fresh" in summary
        assert "447 NOT VERIFIED" in summary


class TestTheRoomsStatedLimitOnDocFreshness:
    """What the room hands a reader about the check it makes impossible."""

    def test_the_room_states_the_cause(self, tmp_path: Path) -> None:
        """The behaviour today, so the finding below is a gap and not a denial."""
        build = build_room(
            bead_id=BEAD,
            project_root=_repo(tmp_path / "project"),
            parent=tmp_path / "rooms",
            environment=False,
        )
        assert build.built is True
        assert "no .git, so a freshness check inside it has no baseline" in build.detail

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "FINDING BDL-068.S6-6 (BDL-UX #273): the room states the CAUSE of the missing "
            "freshness baseline and never the POPULATION. `0 of 450 pairs` is "
            "derivable where the caveat is printed — the project root is in hand — "
            "and it is the form that survives being read as `green in a clean room`"
        ),
    )
    def test_the_room_states_how_many_pairs_a_freshness_check_there_cannot_enter(
        self, tmp_path: Path
    ) -> None:
        build = build_room(
            bead_id=BEAD,
            project_root=_repo(tmp_path / "project"),
            parent=tmp_path / "rooms",
            environment=False,
        )
        assert any(character.isdigit() for character in build.detail.split("baseline")[0][-40:]), (
            "the freshness clause carries no number: " + build.detail
        )

    def test_the_gap_is_the_one_recorded(self, tmp_path: Path) -> None:
        """The clause as it reads today, so the finding names a measured string."""
        build = build_room(
            bead_id=BEAD,
            project_root=_repo(tmp_path / "project"),
            parent=tmp_path / "rooms",
            environment=False,
        )
        clause = build.detail.split("; ", 1)[-1]
        assert clause == "no .git, so a freshness check inside it has no baseline"

    def test_the_room_carries_no_git_directory(self, tmp_path: Path) -> None:
        """The isolation the caveat is about, asserted rather than assumed.

        It is also the reason this module recommends naming the population rather
        than supplying a baseline: a room that carried ``.git`` would measure
        freshness against a history the room was built to exclude.
        """
        build = build_room(
            bead_id=BEAD,
            project_root=_repo(tmp_path / "project"),
            parent=tmp_path / "rooms",
            environment=False,
        )
        assert not (build.path / ".git").exists()


class TestEveryFindingHereIsStrictAndNamesItself:
    """The meta-check `.18` introduced and `.22` carried."""

    def test_every_xfail_in_this_module_is_strict_and_cites_a_finding(self) -> None:
        import sys

        module = sys.modules[__name__]
        for klass_name, klass in vars(module).items():
            if not (isinstance(klass, type) and klass_name.startswith("Test")):
                continue
            for name, function in vars(klass).items():
                for mark in getattr(function, "pytestmark", []):
                    if mark.name != "xfail":
                        continue
                    where = f"{klass_name}.{name}"
                    assert mark.kwargs.get("strict") is True, f"{where}: not strict"
                    assert "FINDING BDL-068.S6-" in mark.kwargs.get("reason", ""), where
