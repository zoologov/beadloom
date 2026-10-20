"""BDL-083 S2g (``beadloom-89gm``; BDL-UX #354, RFC D12): ``beadloom landing-check``.

The command the pre-push hook runs before the Gate. Its exit code is its contract: 0 when
the push lands no hold of its own, 1 when the export it lands holds the slot for a bead it
carries, 2 when git could not answer — never 0 for a push nobody could judge.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from click.testing import CliRunner

from beadloom.application.landing_slot import VERDICT_LEAD
from beadloom.services.cli import main
from tests.support.committed_project import git

if TYPE_CHECKING:
    from pathlib import Path

_ZERO = "0" * 40
_IDENTITY = ("-c", "user.name=Test Committer", "-c", "user.email=committer@example.invalid")


def _held_by(holder: str | None) -> str:
    slot: dict[str, object] = {"id": "rig-merge-slot", "status": "open", "labels": ["gt:slot"]}
    if holder:
        slot.update(status="in_progress", metadata={"holder": holder})
    return json.dumps(slot) + "\n"


def _project(tmp_path: Path, holder: str | None) -> tuple[Path, str]:
    root = tmp_path / "repo"
    (root / ".beads").mkdir(parents=True)
    (root / ".beads" / "issues.jsonl").write_text(_held_by(holder), encoding="utf-8")
    git(root, "init", "-q")
    git(root, "add", "-A")
    git(root, *_IDENTITY, "commit", "-q", "-m", "feat: the work\n\nBead: rig-1")
    return root, git(root, "rev-parse", "HEAD")


def _run(root: Path, *args: str, stdin: str = "") -> tuple[int, str]:
    arguments = ["landing-check", "--project", str(root), *args]
    result = CliRunner().invoke(main, arguments, input=stdin)
    return result.exit_code, result.output


def test_a_push_carrying_its_own_hold_exits_1_and_leads_with_the_verdict(tmp_path: Path) -> None:
    root, tip = _project(tmp_path, "rig-1")
    code, out = _run(root, "--stdin", stdin=f"refs/heads/f {tip} refs/heads/f {_ZERO}\n")
    assert code == 1, out
    assert out.startswith(f"{VERDICT_LEAD}REFUSED"), out


def test_a_push_after_the_release_landed_exits_0(tmp_path: Path) -> None:
    root, tip = _project(tmp_path, None)
    code, out = _run(root, "--stdin", stdin=f"refs/heads/f {tip} refs/heads/f {_ZERO}\n")
    assert code == 0, out
    assert out.startswith(f"{VERDICT_LEAD}clean"), out


def test_without_stdin_the_head_is_judged_as_a_new_branch(tmp_path: Path) -> None:
    root, _ = _project(tmp_path, "rig-1")
    code, out = _run(root)
    assert code == 1, out


def test_input_git_would_not_write_exits_2_and_is_not_checked(tmp_path: Path) -> None:
    root, _ = _project(tmp_path, "rig-1")
    code, out = _run(root, "--stdin", stdin="garbage\n")
    assert code == 2, out
    assert out.startswith(f"{VERDICT_LEAD}NOT CHECKED"), out


def test_outside_a_repository_exits_2(tmp_path: Path) -> None:
    code, out = _run(tmp_path)
    assert code == 2, out
    assert out.startswith(f"{VERDICT_LEAD}NOT CHECKED"), out
