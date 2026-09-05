"""What a reconcile may stage, which is never more than the commit already carries.

**BDL-UX #207.** ``active-sync --stage`` ran inside the pre-commit hook and added
``.beads/issues.jsonl`` to a commit an agent had deliberately removed it from, and
announced the addition on stderr. The agent was following this project's own
instruction — *commit only your own files, by explicit path, never* ``git add -A``
— and committed another agent's tracker export anyway. An instruction cannot
survive a tool that stages after the decision was taken.

**The index at pre-commit time IS the commit's scope**, and the scope is what the
index says DIFFERS FROM ``HEAD`` — a path staged with content identical to
``HEAD`` puts nothing in the commit, so correcting it and staging it would add a
change nobody asked for. A correction to a path outside that set is an addition
to somebody else's decision. This module never makes one: it re-stages the
corrected content of a path the commit already carries, and it NAMES every
correction it therefore withheld, so the committer can stage it themselves if the
commit should carry it. A withheld path is reported, never silently dropped — a
tool that stages without saying so and a tool that declines without saying so are
the same fault with opposite signs.

**And the escape hatch an agent would reach for does not work against a hook that
stages.** Measured on git 2.49.0 in two isolated rigs: ``git commit -- <paths>``
DOES exclude a path that is staged and unnamed, so naming your files to git is a
real defence against an index somebody else wrote into. It is not a defence
against this one, because a pathspec commit builds a temporary index and a
``git add`` run from the pre-commit hook writes into THAT — the hooked file landed
in the commit, and was left staged in the real index afterwards for the next
commit to pick up. So the hook defeated the one instruction an agent could have
followed, and left a residue behind it.

**Why the index and not ``beadloom scope-check``.** The bead naming this defect
proposed ``scope-check`` as the thing that knows an agent's scope. It does not
know this one, and says so itself: its rule reports nothing about a path no graph
node owns, and both paths at issue — an ``ACTIVE.md`` and ``.beads/issues.jsonl``
— are unowned. It answers a different question (does this commit leave the work
item's approved axes) over a population that excludes exactly these two files.

**What this cannot see.** A path already in the index when the hook runs looks the
same whether the agent put it there or another tool did. Commit ``050d63ac`` on
this branch carries a neighbouring bead's ``git mv`` for that reason, with no hook
involved. No pre-commit hook can derive an intent nobody expressed; what makes
that decision visible is the committer naming their paths to git itself, which
the measurement above shows works once nothing stages behind them.
"""

# beadloom:component=active-table

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path


@dataclass(frozen=True)
class StagingDecision:
    """The paths a reconcile staged, and the ones it corrected and did not.

    ``scope_unreadable`` is not the same as an empty ``staged``: a commit that
    stages nothing and a commit whose staged set could not be read both stage
    nothing here, and only one of them is a decision.
    """

    staged: tuple[str, ...] = ()
    withheld: tuple[str, ...] = ()
    scope_unreadable: bool = False

    @property
    def stated(self) -> str:
        """One sentence naming what was staged, what was not, and why."""
        if self.scope_unreadable:
            return (
                "this commit's staged paths could not be read, so nothing was "
                "staged — a scope that cannot be read is not an empty one"
            )
        if not self.withheld:
            return f"staged {len(self.staged)} path(s) this commit already carries"
        return (
            f"staged {len(self.staged)} path(s) this commit already carries and "
            f"withheld {len(self.withheld)} this commit does not stage"
        )


def stageable(candidates: Iterable[str], pending: frozenset[str] | None) -> tuple[str, ...]:
    """The candidates for which staging would actually change the commit.

    *pending* is the set of paths whose working tree differs from the index. A
    reconcile that rewrote nothing into a file leaves it equal to the index, and
    then staging it adds nothing while withholding it withholds nothing — a line
    printed about that on every commit is how a message stops being read, which is
    what this bead was told to measure for before shipping. When the pending set
    could not be read every candidate is kept: a set that is unknown is not an
    empty one.
    """
    ordered = tuple(candidates)
    if pending is None:
        return ordered
    return tuple(path for path in ordered if path in pending)


def decide_staging(
    candidates: Iterable[str], already_staged: frozenset[str] | None
) -> StagingDecision:
    """Split *candidates* into the ones this commit stages and the ones it does not.

    *already_staged* is ``None`` when the commit's scope could not be read, and
    then nothing is staged: staging under an unknown scope is the decision this
    module exists not to take.
    """
    ordered = tuple(candidates)
    if already_staged is None:
        return StagingDecision(withheld=ordered, scope_unreadable=True)
    staged = tuple(path for path in ordered if path in already_staged)
    withheld = tuple(path for path in ordered if path not in already_staged)
    return StagingDecision(staged=staged, withheld=withheld)


def _git_paths(project_root: Path, *args: str) -> frozenset[str] | None:
    """The paths ``git diff`` names for *args*, or ``None`` when git cannot be read.

    The one collector at this module's edge: everything above it is a decision
    over a set somebody hands in.
    """
    try:
        completed = subprocess.run(  # noqa: S603
            ["git", "diff", "--name-only", *args],  # noqa: S607
            cwd=project_root,
            capture_output=True,
            check=False,
        )
    except OSError:
        return None
    if completed.returncode != 0:
        return None
    text = completed.stdout.decode("utf-8", errors="replace")
    return frozenset(line for line in text.splitlines() if line)


def paths_this_commit_stages(project_root: Path) -> frozenset[str] | None:
    """The paths whose index entry differs from ``HEAD`` — the commit's own scope."""
    return _git_paths(project_root, "--cached")


def paths_the_index_has_not_taken(project_root: Path) -> frozenset[str] | None:
    """The paths whose working tree differs from the index."""
    return _git_paths(project_root)


def stage_paths(project_root: Path, paths: tuple[str, ...]) -> bool:
    """``git add`` exactly *paths*; False when git could not be run.

    Fixed argv (no shell); ``--`` guards the explicit paths only. Never stages
    anything beyond what it is handed, and it is only ever handed paths the
    commit already carries.
    """
    if not paths:
        return True
    try:
        completed = subprocess.run(  # noqa: S603
            ["git", "add", "--", *paths],  # noqa: S607
            cwd=project_root,
            capture_output=True,
            check=False,
        )
    except OSError:
        return False
    return completed.returncode == 0
