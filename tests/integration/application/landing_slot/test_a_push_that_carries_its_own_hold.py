"""BDL-083 S2g (``beadloom-89gm``; BDL-UX #354, RFC D12): a push that carries its own hold.

The first outside adopter's second clone followed the composed landing instruction
literally — acquire before the commit, release after — and pushed between the two. The
export inside the pushed commit still held the slot for the bead it landed, the merge
request merged that commit, and the trunk exported the slot as held by a closed bead. The
check below reads what a push would land: the export at the pushed commit, and the
``Bead:`` trailers of the commits the push carries, both through git.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from beadloom.application.landing_slot import (
    LANDING_SEQUENCE,
    VERDICT_CLEAN,
    VERDICT_NOT_CHECKED,
    VERDICT_REFUSED,
    check_push,
    pushed_refs,
)
from tests.support.committed_project import git

if TYPE_CHECKING:
    from pathlib import Path

_ZERO = "0" * 40
_IDENTITY = ("-c", "user.name=Test Committer", "-c", "user.email=committer@example.invalid")


def _export(*, holder: str | None, beads: dict[str, str]) -> str:
    slot: dict[str, object] = {
        "_type": "issue",
        "id": "rig-merge-slot",
        "title": "Merge Slot",
        "status": "in_progress" if holder else "open",
        "labels": ["gt:slot"],
    }
    if holder:
        slot["metadata"] = {"holder": holder}
    rows = [{"_type": "issue", "id": b, "status": s} for b, s in beads.items()] + [slot]
    return "".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows)


def _commit(root: Path, message: str, export: str | None) -> str:
    (root / "work.txt").write_text(message, encoding="utf-8")
    git(root, "add", "work.txt")
    if export is not None:
        (root / ".beads").mkdir(exist_ok=True)
        (root / ".beads" / "issues.jsonl").write_text(export, encoding="utf-8")
        git(root, "add", ".beads/issues.jsonl")
    git(root, *_IDENTITY, "commit", "-q", "-m", message)
    return git(root, "rev-parse", "HEAD")


def _repository(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q")
    _commit(root, "the start", None)
    return root


def _new_branch(tip: str) -> str:
    return f"refs/heads/f {tip} refs/heads/f {_ZERO}\n"


def test_a_push_whose_export_holds_the_slot_for_a_bead_it_carries_is_refused(
    tmp_path: Path,
) -> None:
    root = _repository(tmp_path)
    tip = _commit(
        root,
        "feat: the work\n\nBead: rig-1",
        _export(holder="rig-1", beads={"rig-1": "in_progress"}),
    )
    verdict = check_push(root, pushed_refs(_new_branch(tip)))
    assert verdict.status == VERDICT_REFUSED
    said = "\n".join(verdict.lines)
    assert "rig-1" in said
    assert LANDING_SEQUENCE in said
    assert "bd merge-slot release --holder rig-1" in said
    assert "bd export -o .beads/issues.jsonl" in said


def test_the_same_push_after_the_release_is_exported_and_landed_is_clean(
    tmp_path: Path,
) -> None:
    root = _repository(tmp_path)
    _commit(root, "feat: the work\n\nBead: rig-1", _export(holder="rig-1", beads={"rig-1": "x"}))
    tip = _commit(
        root, "chore: the export\n\nBead: rig-1", _export(holder=None, beads={"rig-1": "x"})
    )
    verdict = check_push(root, pushed_refs(_new_branch(tip)))
    assert verdict.status == VERDICT_CLEAN, verdict.lines


def test_a_hold_by_a_bead_this_push_does_not_carry_is_named_and_not_refused(
    tmp_path: Path,
) -> None:
    root = _repository(tmp_path)
    tip = _commit(
        root, "feat: mine\n\nBead: rig-1", _export(holder="rig-2", beads={"rig-2": "in_progress"})
    )
    verdict = check_push(root, pushed_refs(_new_branch(tip)))
    assert verdict.status == VERDICT_CLEAN
    assert "rig-2" in "\n".join(verdict.lines)


def test_only_the_commits_the_remote_lacks_are_carried(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    landed = _commit(
        root, "feat: earlier\n\nBead: rig-1", _export(holder="rig-1", beads={"rig-1": "x"})
    )
    tip = _commit(root, "feat: later\n\nBead: rig-2", None)
    line = f"refs/heads/f {tip} refs/heads/f {landed}\n"
    assert check_push(root, pushed_refs(line)).status == VERDICT_CLEAN
    assert check_push(root, pushed_refs(_new_branch(tip))).status == VERDICT_REFUSED


def test_a_mention_of_the_bead_outside_the_trailer_carries_nothing(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    tip = _commit(
        root, "feat: notes on rig-1\n\nBead: rig-9", _export(holder="rig-1", beads={"rig-1": "x"})
    )
    assert check_push(root, pushed_refs(_new_branch(tip))).status == VERDICT_CLEAN


def test_a_push_with_no_export_at_its_tip_is_clean_and_says_why(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    tip = _commit(root, "feat: the work\n\nBead: rig-1", None)
    verdict = check_push(root, pushed_refs(_new_branch(tip)))
    assert verdict.status == VERDICT_CLEAN
    assert ".beads/issues.jsonl" in "\n".join(verdict.lines)


def test_a_deletion_and_an_empty_push_land_no_export(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    deletion = f"(delete) {_ZERO} refs/heads/old {'b' * 40}\n"
    assert check_push(root, pushed_refs(deletion)).status == VERDICT_CLEAN
    assert check_push(root, ()).status == VERDICT_CLEAN


def test_a_commit_git_cannot_find_is_not_checked_rather_than_clean(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    verdict = check_push(root, pushed_refs(_new_branch("c" * 40)))
    assert verdict.status == VERDICT_NOT_CHECKED
