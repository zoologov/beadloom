# beadloom:domain=doc-sync
# beadloom:feature=sync-check
"""The git baseline: which paths differ from ``HEAD``.

**Why this module exists.** A doc-freshness check needs a baseline — a state of
the world from BEFORE the current edit — to compare against. Beadloom used to
keep that baseline only in ``.beadloom/beadloom.db``, which is a derived cache:
git-ignored, per-machine, and destroyed on every rebuild and every CI checkout.
A rebuild therefore recorded the *current* tree as its own baseline, and nothing
can be stale relative to a baseline created a second ago (BDL-UX #175).

Git is the baseline that cannot be lost: it is committed by construction, it
travels with the clone, and a rebuilt index cannot erase it. This module reads
it, and it answers exactly one KIND of question: *what does git say about this
working copy?* — which paths differ from ``HEAD``, which paths this commit
stages, which paths a branch changes against a ref, and which branch is checked
out. BDL-068 S1.6 widened it from the first two to the last two rather than
opening a second subprocess call to ``git`` elsewhere in the product: two
readers of one tool are two things that can disagree about what a path is
relative to, and ``_project_relative`` is the answer to that. BDL-083 S1c added
a fifth for the same reason: which commits a branch holds against a ref, with the
message and the paths of each, so the Gate can attribute a finding to the bead
whose commits changed its files. BDL-083 S1d added the sixth, for the scope
check's base: where this branch left the branch it was cut from — the merge-base
of two refs, whether one commit is an ancestor of another, the branches the
working copy knows, and what the reflog recorded when a branch was created.

What it deliberately does NOT do: judge freshness. That is
:func:`~beadloom.doc_sync.engine.check_sync`'s job, which pairs this answer with
the doc side. And ``None`` means *git could not answer* (no repository, no git
binary, no commit yet) — never "nothing changed": an absent answer that reads as
a clean one is the defect this module was written for.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

# Decoded exactly like every other side of a comparison in this domain: an
# ambient codec makes the answer a property of the image rather than the tree
# (see ``engine._TEXT_CODEC``).
_TEXT_CODEC = "utf-8"
_TEXT_ERRORS = "surrogateescape"

#: Rename / copy status letters — their record carries the OLD path as a second
#: NUL-separated field, and both endpoints count as changed.
_RENAME_STATUS = frozenset("RC")

#: Separators of one ``git log`` record: before each commit, and after its hash and
#: its message. Neither byte occurs in a hash, and a commit message that holds one
#: is not a message any tool writes.
_COMMIT_START = "\x1e"
_COMMIT_FIELD = "\x1f"
_COMMIT_FORMAT = f"--format={_COMMIT_START}%H{_COMMIT_FIELD}%B{_COMMIT_FIELD}"

#: The fields of one record: the hash, the message, and the NUL-separated paths.
_COMMIT_FIELDS = 3

#: The shortest possible porcelain record is ``XY p`` — two status letters, a
#: space, and a one-character path.
_MIN_RECORD_LEN = 4


def _run_git(project_root: Path, args: list[str]) -> str | None:
    """Run ``git *args`` in *project_root*; ``None`` when git cannot answer."""
    try:
        result = subprocess.run(  # noqa: S603
            ["git", *args],  # noqa: S607
            cwd=project_root,
            capture_output=True,
            encoding=_TEXT_CODEC,
            errors=_TEXT_ERRORS,
            check=False,
        )
    except OSError:
        # git missing / not executable / unusable cwd. `check=False` rules out
        # CalledProcessError and no timeout is passed, so OSError is the whole set.
        return None
    if result.returncode != 0:
        return None
    return result.stdout


def changed_paths(project_root: Path) -> frozenset[str] | None:
    """Project-relative paths that differ from ``HEAD``, or ``None`` if unknown.

    Includes modified, staged, deleted, renamed (both endpoints) and untracked
    files, because every one of them is a path whose content is not the content
    ``HEAD`` records. Ignored files are excluded: git does not track them, so
    git has no opinion about them and inventing one would be the same category
    error as inventing a baseline.

    ``None`` is returned when the project is not inside a git work tree, when
    ``git`` is unavailable, or when there is no ``HEAD`` yet. Callers must treat
    it as *not checked*, never as *no changes*.
    """
    prefix = _run_git(project_root, ["rev-parse", "--show-prefix"])
    if prefix is None:
        return None
    if _run_git(project_root, ["rev-parse", "--verify", "HEAD"]) is None:
        return None  # a repository with no commit has no baseline to offer
    raw = _run_git(project_root, ["status", "--porcelain", "-z", "-uall"])
    if raw is None:
        return None
    return frozenset(_project_relative(_parse_porcelain_z(raw), prefix.strip()))


def staged_paths(project_root: Path) -> frozenset[str] | None:
    """Project-relative paths this commit would record, or ``None`` if unknown.

    The same question as :func:`changed_paths`, asked of the index rather than of
    the working tree: *what is this commit about?* It exists because a commit
    gate that judges the whole tree fails one agent's commit on a neighbour's
    in-progress work (BDL-UX #118) — the tree is shared, the index is not.

    Added, copied, modified and renamed entries are included; a deletion is not,
    because there is no content left to compare a document against and the pair's
    own ``missing`` verdict already covers it.

    ``None`` means git could not answer — no work tree, no ``git``, no ``HEAD``
    yet — and callers must treat it as *not checked*, never as *nothing staged*.
    """
    prefix = _run_git(project_root, ["rev-parse", "--show-prefix"])
    if prefix is None:
        return None
    if _run_git(project_root, ["rev-parse", "--verify", "HEAD"]) is None:
        return None  # a repository with no commit stages against nothing
    raw = _run_git(
        project_root,
        ["diff", "--cached", "--name-only", "-z", "--diff-filter=ACMR"],
    )
    if raw is None:
        return None
    paths = [field for field in raw.split("\0") if field]
    return frozenset(_project_relative(paths, prefix.strip()))


def paths_changed_since(project_root: Path, ref: str) -> frozenset[str] | None:
    """Project-relative paths this branch changes against *ref*, or ``None``.

    ``ref...HEAD`` and not ``ref..HEAD``: the three-dot form asks what this
    branch changed since it left *ref*, which is what a pull request contains
    and what an approval was given for. The two-dot form would also report every
    commit that landed on the trunk meanwhile as this branch's work — measured
    on this repository, where a local ``main`` two commits behind the remote
    made another work item's landed change look like this branch's.

    ``None`` means git could not answer — no work tree, no ``git``, an unknown
    ref — and callers must treat it as *not checked*, never as *no changes*.
    """
    prefix = _run_git(project_root, ["rev-parse", "--show-prefix"])
    if prefix is None:
        return None
    if _run_git(project_root, ["rev-parse", "--verify", ref]) is None:
        return None
    raw = _run_git(
        project_root, ["diff", "--name-only", "-z", "--diff-filter=ACMR", f"{ref}...HEAD"]
    )
    if raw is None:
        return None
    paths = [field for field in raw.split("\0") if field]
    return frozenset(_project_relative(paths, prefix.strip()))


@dataclass(frozen=True)
class BranchCommit:
    """One commit a branch holds: its hash, the message it was made with, its paths."""

    sha: str
    message: str
    paths: frozenset[str]
    """Project-relative paths the commit added, modified or deleted."""


def commits_since(project_root: Path, ref: str) -> tuple[BranchCommit, ...] | None:
    """The commits ``HEAD`` holds that *ref* does not, newest first, or ``None``.

    ``ref..HEAD`` is the set ``ref...HEAD`` diffs — the commits made since the
    branch left *ref* — listed one by one instead of folded into one diff,
    because the question is which commit changed a path, not whether one did.
    ``--no-renames`` reports a rename as its deletion and its addition, so both
    paths are changed by the commit; a merge commit lists no path of its own.

    ``None`` means git could not answer — no work tree, no ``git``, an unknown
    ref — and callers must treat it as *not checked*, never as *no commits*.
    """
    prefix = _run_git(project_root, ["rev-parse", "--show-prefix"])
    if prefix is None:
        return None
    if _run_git(project_root, ["rev-parse", "--verify", "--quiet", ref]) is None:
        return None
    raw = _run_git(
        project_root,
        ["log", _COMMIT_FORMAT, "--name-only", "-z", "--no-renames", f"{ref}..HEAD"],
    )
    if raw is None:
        return None
    return tuple(_parse_commits(raw, prefix.strip()))


def _parse_commits(raw: str, prefix: str) -> list[BranchCommit]:
    """Records of ``git log`` in :data:`_COMMIT_FORMAT` with ``--name-only -z``."""
    commits: list[BranchCommit] = []
    for record in raw.split(_COMMIT_START):
        fields = record.split(_COMMIT_FIELD)
        if len(fields) != _COMMIT_FIELDS:
            continue
        sha, message, names = fields
        # `-z` ends the format with a NUL, and git separates it from the path list
        # with a newline; neither is part of a path.
        paths = [name.lstrip("\n") for name in names.split("\0")]
        commits.append(
            BranchCommit(
                sha=sha.strip(),
                message=message,
                paths=frozenset(_project_relative([p for p in paths if p], prefix)),
            )
        )
    return commits


def ref_exists(project_root: Path, ref: str) -> bool:
    """Whether git resolves *ref* in this working copy."""
    return _run_git(project_root, ["rev-parse", "--verify", "--quiet", ref]) is not None


def merge_base(project_root: Path, first: str, second: str) -> str | None:
    """The best common ancestor of *first* and *second* as a full hash, or ``None``.

    ``None`` when git cannot answer or the two share no history; never a guess.
    """
    found = _run_git(project_root, ["merge-base", first, second])
    if found is None:
        return None
    return found.strip() or None


def is_ancestor(project_root: Path, ancestor: str, descendant: str) -> bool:
    """Whether *ancestor* is reachable from *descendant* (a commit is its own ancestor)."""
    answer = _run_git(project_root, ["merge-base", "--is-ancestor", ancestor, descendant])
    return answer is not None


def short_commit(project_root: Path, ref: str) -> str | None:
    """The shortest hash that names *ref* unambiguously in this repository, or ``None``."""
    found = _run_git(project_root, ["rev-parse", "--short", "--verify", "--quiet", ref])
    if found is None:
        return None
    return found.strip() or None


def commit_distance(project_root: Path, ancestor: str, descendant: str) -> int | None:
    """How many commits *descendant* holds that *ancestor* does not, or ``None``."""
    found = _run_git(project_root, ["rev-list", "--count", f"{ancestor}..{descendant}"])
    if found is None:
        return None
    try:
        return int(found.strip())
    except ValueError:
        return None


def branch_names(project_root: Path) -> tuple[str, ...] | None:
    """Every local and remote-tracking branch, by short name; symbolic refs left out.

    ``origin/HEAD`` is a pointer to another branch, not a branch, so it is skipped
    rather than read as a second name for the trunk.
    """
    raw = _run_git(
        project_root,
        ["for-each-ref", "--format=%(refname:short)%00%(symref)", "refs/heads", "refs/remotes"],
    )
    if raw is None:
        return None
    names: list[str] = []
    for line in raw.splitlines():
        name, _, symref = line.partition("\0")
        if name and not symref:
            names.append(name)
    return tuple(sorted(names))


#: The reflog subject git writes when a branch is created, before its start point.
_CREATED_FROM = "branch: Created from "

#: The HEAD reflog subject of a checkout, as ``checkout: moving from <a> to <b>``.
_MOVING_FROM = "checkout: moving from "


def branch_start_point(project_root: Path, branch: str) -> str | None:
    """The start point *branch* was created from, as this machine's reflog recorded it.

    ``git switch -c <branch>`` records ``Created from HEAD``, which names no branch;
    the HEAD reflog then says which branch was checked out when *branch* was first
    entered, and that is the one it was cut from. ``None`` when the reflog holds no
    answer: a fresh clone, a CI checkout, or a reflog that has expired.
    """
    created = _oldest_subject(project_root, f"refs/heads/{branch}")
    if created is None or not created.startswith(_CREATED_FROM):
        return None
    start = created.removeprefix(_CREATED_FROM).strip()
    if start != "HEAD":
        return start or None
    return _entered_from(project_root, branch)


def _entered_from(project_root: Path, branch: str) -> str | None:
    """The branch HEAD left the first time it moved to *branch*, from the HEAD reflog."""
    raw = _run_git(project_root, ["reflog", "show", "--format=%gs", "HEAD", "--"])
    if raw is None:
        return None
    suffix = f" to {branch}"
    entered = [
        line.removeprefix(_MOVING_FROM).removesuffix(suffix)
        for line in raw.splitlines()
        if line.startswith(_MOVING_FROM) and line.endswith(suffix)
    ]
    if not entered:
        return None
    # Newest first, so the oldest entry — the first time HEAD entered it — is last.
    return entered[-1].strip() or None


def _oldest_subject(project_root: Path, ref: str) -> str | None:
    """The subject of the oldest reflog entry of *ref*, or ``None`` when it has none."""
    raw = _run_git(project_root, ["reflog", "show", "--format=%gs", ref, "--"])
    if raw is None:
        return None
    lines = [line for line in raw.splitlines() if line.strip()]
    return lines[-1] if lines else None


def current_branch(project_root: Path) -> str | None:
    """The checked-out branch, or ``None`` outside a repo / on a detached HEAD.

    ``git branch --show-current`` rather than ``rev-parse --abbrev-ref HEAD``:
    the second answers ``HEAD`` on a detached checkout, which reads as a branch
    named ``HEAD`` rather than as the absence of one.
    """
    name = _run_git(project_root, ["branch", "--show-current"])
    if name is None:
        return None
    return name.strip() or None


def _parse_porcelain_z(raw: str) -> list[str]:
    """Paths out of ``git status --porcelain -z`` (repository-relative).

    The NUL format is used rather than the line format because the latter quotes
    and escapes paths that contain spaces or non-ASCII bytes, and a path that
    round-trips wrong silently drops a file out of the comparison.
    """
    fields = [f for f in raw.split("\0") if f]
    paths: list[str] = []
    index = 0
    while index < len(fields):
        record = fields[index]
        index += 1
        if len(record) < _MIN_RECORD_LEN:
            continue
        status, path = record[:2], record[3:]
        paths.append(path)
        if set(status) & _RENAME_STATUS and index < len(fields):
            paths.append(fields[index])  # the rename's source path
            index += 1
    return paths


def _project_relative(paths: list[str], prefix: str) -> list[str]:
    """Re-root repository-relative *paths* onto the project directory.

    ``git status --porcelain`` always reports from the repository root, which is
    not necessarily the Beadloom project root (a monorepo sub-project is the
    ordinary case). Paths outside the project are dropped: they are real changes
    to something this project does not own.
    """
    if not prefix:
        return paths
    return [p[len(prefix) :] for p in paths if p.startswith(prefix)]
