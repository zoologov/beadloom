"""What the working tree holds beyond HEAD, read before a clean room is built from HEAD.

BDL-083 S2d (RFC D6, BDL-UX #335). Measured on the first outside adopter's monorepo, anonymised
as ``tests/fixtures/monorepo``: a room for a 51-file ``git mv`` change had to be finished by
hand, twice. The room is built from HEAD, so the old side of a rename stayed in it — the old
package importable, the old tests collected as a second set — and naming an old path in
``--carry`` refused the room, because the tree no longer held it. And a file shared with a
neighbour bead was copied whole with the neighbour's edits in it, which the room did not say.

This module answers the two questions the room asks git before it is built, and nothing else:

* **Does HEAD hold a carried path, and as what?** A path HEAD holds as a file and the tree does
  not is the bead's deletion, and the room deletes it too. A path neither holds is a typing
  error and is still refused, so a list never shrinks without the caller being told.
* **Where does the tree differ from HEAD?** Every modified, deleted, added and untracked file,
  ignored files excepted. The room names the ones it does not carry: those are the differences
  its verdict leaves out, a neighbour's work or a file of the bead's own nobody named. Which of
  the two each one is, git cannot say, so the room names them rather than guessing.

Paths are read relative to the project root, with ``-z`` so a name git would quote is read
whole. A git that cannot answer gives ``None`` (or an empty mapping), never an exception: the
room is still buildable, and the caller says the difference was not read.
"""

# beadloom:feature=wave-plan

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

#: The kinds of difference a room reports. Words rather than git's letters, because a reader
#: of ``clean-room --json`` is not assumed to know ``git diff``'s status codes.
CHANGE_MODIFIED = "modified"
CHANGE_DELETED = "deleted"
CHANGE_ADDED = "added"
CHANGE_UNTRACKED = "untracked"
CHANGE_UNMERGED = "unmerged"

#: What HEAD holds a path as.
HELD_AS_FILE = "file"
HELD_AS_DIRECTORY = "directory"

#: ``git diff --name-status`` letters, without renames and copies (``--no-renames`` splits a
#: rename into its two sides, which is the shape a carry list has). ``T`` is a file whose type
#: changed, a modification as far as a room is concerned.
_STATUS_CHANGES = {
    "M": CHANGE_MODIFIED,
    "T": CHANGE_MODIFIED,
    "D": CHANGE_DELETED,
    "A": CHANGE_ADDED,
    "U": CHANGE_UNMERGED,
}

_TEXT_CODEC = "utf-8"


@dataclass(frozen=True)
class TreeDifference:
    """One file where the working tree differs from HEAD, and how."""

    path: str
    change: str


def held_at_head(root: Path, paths: Iterable[str]) -> dict[str, str]:
    """What HEAD holds each of *paths* as, for the ones it holds at all.

    *paths* are relative to *root* in POSIX form. A path HEAD does not hold is absent from the
    answer, and so is every path when git cannot answer — the caller then refuses a carried
    path the tree does not hold either, which is the answer it gave before deletions existed.
    """
    named = tuple(dict.fromkeys(paths))
    if not named:
        return {}
    # Recursive and by name: `ls-tree` without `-r` lists a named directory's CHILDREN rather
    # than the directory, so the one reading that does not depend on that rule is the list
    # of every file HEAD holds under the named paths.
    listing = _git(root, "ls-tree", "-r", "-z", "--name-only", "HEAD", "--", *named)
    if listing is None:
        return {}
    files = set(filter(None, listing.split("\0")))
    held: dict[str, str] = {}
    for path in named:
        if path in files:
            held[path] = HELD_AS_FILE
        elif any(file.startswith(f"{path}/") for file in files):
            held[path] = HELD_AS_DIRECTORY
    return held


def tree_differences(root: Path) -> tuple[TreeDifference, ...] | None:
    """Every file where the working tree under *root* differs from HEAD, or ``None``.

    Staged and unstaged changes are one answer, because a room is built from HEAD and both
    are absent from it. ``None`` means git could not answer, which is not "no difference".
    """
    tracked = _git(root, "diff", "HEAD", "--relative", "--name-status", "--no-renames", "-z")
    untracked = _git(root, "ls-files", "--others", "--exclude-standard", "-z")
    if tracked is None or untracked is None:
        return None
    differences = list(_tracked_differences(tracked))
    differences += [
        TreeDifference(path, CHANGE_UNTRACKED) for path in filter(None, untracked.split("\0"))
    ]
    return tuple(sorted(differences, key=lambda difference: difference.path))


def differences_not_carried(
    differences: Iterable[TreeDifference], carried: Iterable[str]
) -> tuple[TreeDifference, ...]:
    """The *differences* no carried path names — the ones a room's verdict leaves out."""
    named = set(carried)
    return tuple(difference for difference in differences if difference.path not in named)


def difference_records(
    differences: tuple[TreeDifference, ...] | None,
) -> list[dict[str, str]] | None:
    """*differences* as the records a room's marker and ``clean-room --json`` carry.

    ``None`` stays ``None``: a difference git could not read is not an empty one.
    """
    if differences is None:
        return None
    return [{"path": difference.path, "change": difference.change} for difference in differences]


def _tracked_differences(listing: str) -> Iterable[TreeDifference]:
    """Read ``--name-status -z`` output: a status field, then its path, each NUL-ended."""
    fields = listing.split("\0")
    # Not strict: the output ends with a NUL, so the split leaves one empty field over.
    for status, path in zip(fields[0::2], fields[1::2], strict=False):
        if status and path:
            yield TreeDifference(path, _STATUS_CHANGES.get(status[0], CHANGE_MODIFIED))


def _git(root: Path, *args: str) -> str | None:
    """Run one read-only git command in *root*; its output, or ``None`` if it did not answer."""
    try:
        result = subprocess.run(  # noqa: S603
            ["git", *args],  # noqa: S607
            cwd=root,
            capture_output=True,
            encoding=_TEXT_CODEC,
            errors="surrogateescape",
            check=False,
        )
    except OSError:
        return None
    return result.stdout if result.returncode == 0 else None
