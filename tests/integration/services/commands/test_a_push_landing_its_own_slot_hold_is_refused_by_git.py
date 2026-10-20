"""A real ``git push`` of a commit whose export still holds the landing slot (BDL-UX #354).

The adopter's second clone landed a bead in the order the 9.0.0 flow gave: acquire, commit
with the export, push, release. The export inside the pushed commit held the slot for the
bead it landed, the trunk merged that commit, and the next clone's ``bd merge-slot acquire``
was refused naming a bead that was closed. Measured on the monorepo fixture with bd 1.0.4:
on 9.0.0 that push exits 0; with ``beadloom landing-check`` in the installed pre-push hook it
exits 1 and the remote receives nothing.

These tests push through git itself, so the hook's exit code is judged by git and not by the
test. The Gate is a shim that passes, because the push is refused before it would run and
the clean case should not depend on what the Gate reads in a one-file repository; the
landing check is the real ``beadloom`` under test. Nothing here imports the module that
implements the check, so the file collects against 9.0.0 and fails there on its assertions.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tests.support.committed_project import commit_project, git
from tests.support.hook_runner import install_hooks, tools

#: The ``beadloom`` the suite runs under, which the shim hands every landing check to.
_BEADLOOM = Path(sys.executable).parent / "beadloom"

#: A ``beadloom`` that runs the real landing check and passes the Gate: the Gate's verdict
#: line goes to the ``--tee`` copy the hook reads it back from.
_SHIM = f"""\
if [ "$1" = landing-check ]; then exec "{_BEADLOOM}" "$@"; fi
if [ "$1" = ci ]; then
  while [ $# -gt 0 ]; do
    if [ "$1" = --tee ]; then shift; echo "PASS - gate clean" > "$1"; fi
    shift
  done
  echo "PASS - gate clean"
fi
exit 0"""

_IDENTITY = ("-c", "user.name=Test Committer", "-c", "user.email=committer@example.invalid")

#: The bead the pushed commit lands, named by its ``Bead:`` trailer.
_BEAD = "rig-1"


def _export(holder: str | None) -> str:
    """``.beads/issues.jsonl`` in the shape bd 1.0.4 writes: the bead and the slot record."""
    slot: dict[str, object] = {
        "_type": "issue",
        "id": "rig-merge-slot",
        "title": "Merge Slot",
        "status": "open",
        "labels": ["gt:slot"],
    }
    if holder is not None:
        slot.update(status="in_progress", metadata={"holder": holder})
    rows = [{"_type": "issue", "id": _BEAD, "status": "closed"}, slot]
    return "".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows)


def _clone_landing(tmp_path: Path, holder: str | None) -> tuple[Path, Path]:
    """A clone whose last commit lands ``rig-1`` with an export naming *holder*, and its remote."""
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)  # noqa: S603, S607
    root = tmp_path / "clone"
    (root / ".beadloom").mkdir(parents=True)
    (root / "README.md").write_text("a repository\n", encoding="utf-8")
    commit_project(root, origin=str(remote))
    install_hooks(root)
    (root / ".beads").mkdir()
    (root / ".beads" / "issues.jsonl").write_text(_export(holder), encoding="utf-8")
    git(root, "add", ".beads/issues.jsonl")
    message = f"feat: the work\n\nBead: {_BEAD}"
    git(root, *_IDENTITY, "commit", "-q", "--no-verify", "-m", message)
    return root, remote


def _push(root: Path, tmp_path: Path) -> subprocess.CompletedProcess[str]:
    """``git push`` of HEAD to the remote's ``main``, under a PATH holding git and the shim."""
    return subprocess.run(
        ["git", "push", "origin", "HEAD:refs/heads/main"],  # noqa: S607 - git on the PATH below
        cwd=root,
        env={"PATH": tools(tmp_path, shims={"beadloom": _SHIM}), "HOME": str(tmp_path)},
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def _remote_main(remote: Path) -> str:
    """The commit the remote's ``main`` names, or an empty string when it names none."""
    return git(remote, "for-each-ref", "--format=%(objectname)", "refs/heads/main")


def test_a_push_whose_export_holds_the_slot_for_its_own_bead_does_not_reach_the_remote(
    tmp_path: Path,
) -> None:
    root, remote = _clone_landing(tmp_path, holder=_BEAD)

    pushed = _push(root, tmp_path)

    assert pushed.returncode != 0, pushed.stdout + pushed.stderr
    assert _remote_main(remote) == ""


def test_the_refused_push_names_the_release_that_frees_the_slot(tmp_path: Path) -> None:
    root, _ = _clone_landing(tmp_path, holder=_BEAD)

    pushed = _push(root, tmp_path)

    assert f"bd merge-slot release --holder {_BEAD}" in pushed.stdout + pushed.stderr


def test_a_push_whose_export_shows_the_slot_free_reaches_the_remote(tmp_path: Path) -> None:
    root, remote = _clone_landing(tmp_path, holder=None)

    pushed = _push(root, tmp_path)

    assert pushed.returncode == 0, pushed.stdout + pushed.stderr
    assert _remote_main(remote) == git(root, "rev-parse", "HEAD")
