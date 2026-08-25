"""Which sync pairs a commit is about, and how many it therefore left unjudged.

**The defect this closes.** The pre-commit hook judged the whole working tree. In
a single tree with several agents in it — the mode `/coordinator` prescribes,
not an exotic one — that meant one agent's commit was blocked by a neighbour's
half-written file, in a module the committer had never opened (BDL-UX #118).
Serialising *who* commits does not help: the merge slot orders the commits and
leaves the tree exactly as shared as it was.

**The repair is a boundary, not a tolerance.** The commit gate judges the commit;
the push gate judges the tree. Nothing stops being enforced, because nothing
reaches ``main`` without the pre-push Gate running over everything — what moves
is *when* a pair is judged, from "whenever a neighbour happens to be mid-edit"
to "when the commit that changes it is made".

**And the half it did not judge is stated.** A check that silently narrowed its
own scope would be the false-green this epic exists to remove: a green count is
not a checked count. So the answer carries the number of pairs left out, and the
caller prints it next to the verdict.
"""

# beadloom:domain=doc-sync
# beadloom:feature=sync-check

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

#: Why a commit-scoped run checked nothing at all. Not an error: a commit that
#: stages no indexed code is a perfectly ordinary commit.
NOTHING_STAGED = "no staged path belongs to an indexed doc-code pair"

#: Why a commit-scoped run could not narrow itself. git could not answer, so the
#: run judges everything rather than judging a set it invented.
GIT_SILENT = "git could not say what this commit stages, so nothing was narrowed"


@dataclass(frozen=True)
class CommitScope:
    """The pairs a commit is about, and what was left to the push gate."""

    pairs: tuple[dict[str, Any], ...]
    not_checked: int
    reason: str | None = None

    @property
    def narrowed(self) -> bool:
        """True when this really is a commit-scoped answer."""
        return self.reason != GIT_SILENT

    def describe(self) -> str:
        """The one line a commit gate prints about what it did not judge."""
        if not self.narrowed:
            return f"Scoped to the commit: {GIT_SILENT}"
        left = (
            f"{self.not_checked} pair(s) outside this commit were not checked "
            "— the pre-push Gate judges the whole tree"
        )
        return f"Scoped to the commit: {len(self.pairs)} pair(s) checked, {left}."


def _pair_paths(pair: dict[str, Any], docs_dir: str) -> set[str]:
    """Both sides of a pair as project-relative POSIX paths."""
    paths: set[str] = set()
    code_path = pair.get("code_path")
    if code_path:
        paths.add(str(code_path))
    doc_path = pair.get("doc_path")
    if doc_path:
        paths.add(Path(docs_dir, str(doc_path)).as_posix())
        paths.add(str(doc_path))
    return paths


def scope_to_commit(
    pairs: Sequence[dict[str, Any]],
    staged: Iterable[str] | None,
    *,
    docs_dir: str,
) -> CommitScope:
    """The subset of *pairs* this commit stages either side of.

    Either side, deliberately: a commit that stages only the DOC of a stale pair
    is the commit that fixes it, and a gate that looked at code paths alone would
    refuse the repair it asked for.

    ``staged is None`` means git did not answer. Every pair is kept and the
    reason says so — narrowing a check on an absent answer would be inventing the
    scope, which is the same category error as inventing a baseline.
    """
    if staged is None:
        return CommitScope(pairs=tuple(pairs), not_checked=0, reason=GIT_SILENT)
    staged_set = set(staged)
    kept = tuple(
        pair for pair in pairs if _pair_paths(pair, docs_dir) & staged_set
    )
    return CommitScope(
        pairs=kept,
        not_checked=len(pairs) - len(kept),
        reason=NOTHING_STAGED if not kept else None,
    )
