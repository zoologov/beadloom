# beadloom:domain=graph
# beadloom:feature=rule-engine
"""A lint result narrowed to the nodes a commit touches, and the sentence that says so.

BDL-083 S1a (``beadloom-7i09``, BDL-UX #326). Until 9.0.0 the pre-commit hook ran no
architecture lint at all: on an adopter's monorepo a widget's spec imported the app layer,
``lint --strict`` on the tree exited 1, and the commit was made and pushed with both hooks
installed. The hook now runs ``beadloom lint --staged``, and this module is the narrowing
that flag asks for.

**The commit, not the tree.** The hook judges what the commit stages, because in a tree
several agents share a whole-tree check fails one agent's commit on a neighbour's work
(BDL-UX #118). So the result keeps the findings of the nodes that own a staged path, and
the findings located in a staged file whatever their node; everything else is COUNTED and
left to the pre-push Gate, which lints the whole tree. A finding about a rule rather than
a node — a liveness or population advisory names no node — is among what is left: the
commit did not change the rule.

**A git that did not answer narrows nothing.** ``None`` for the staged paths means git
could not say what the commit holds, and narrowing on an absent answer would be inventing
the scope (the same rule :mod:`beadloom.doc_sync.commit_scope` follows for the sync pairs).

Pure: the staged paths and the ownership lookup are handed in, so the graph layer reads
neither git nor the index here.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from beadloom.graph.linter import LintResult

#: How the commit-scope sentence begins. The pre-commit hook finds the verdict of its lint
#: leg by this lead, so the two must not each spell it.
COMMIT_SCOPE_LEAD = "Lint over this commit: "

#: How many node names the sentence lists before it says how many more there are.
_NODES_NAMED = 5


@dataclass(frozen=True)
class CommitLintScope:
    """A lint result over one commit, and the counts that say how far it reached."""

    result: LintResult
    #: How many paths the commit stages; ``None`` when git could not say.
    staged: int | None
    #: How many of the staged paths a node owns.
    owned: int
    #: The nodes that own a staged path, sorted.
    nodes: tuple[str, ...]
    #: How many findings of the whole run the narrowing left to the pre-push Gate.
    left_out: int

    @property
    def sentence(self) -> str:
        """The one line that states the scope, the verdict on it, and what was left out."""
        if self.staged is None:
            return (
                f"{COMMIT_SCOPE_LEAD}git did not name the paths this commit stages, "
                "so the whole tree was judged"
            )
        if not self.nodes:
            return (
                f"{COMMIT_SCOPE_LEAD}none of the {self.staged} staged path(s) belongs to "
                "a node, so no node was judged; the pre-push Gate lints the whole tree"
            )
        return (
            f"{COMMIT_SCOPE_LEAD}{len(self.nodes)} node(s) own {self.owned} of "
            f"{self.staged} staged path(s) ({_listed_nodes(self.nodes)}); "
            f"{self.result.error_count} error(s), {self.result.warning_count} warning(s) "
            f"on them; {self.left_out} finding(s) elsewhere left to the pre-push Gate"
        )


def scope_lint_to_commit(
    result: LintResult,
    staged: frozenset[str] | None,
    owner_of: Callable[[str], str | None],
) -> CommitLintScope:
    """Narrow *result* to the nodes that own a path in *staged*, by *owner_of*."""
    if staged is None:
        return CommitLintScope(result=result, staged=None, owned=0, nodes=(), left_out=0)
    owners = {path: owner_of(path) for path in staged}
    nodes = frozenset(owner for owner in owners.values() if owner is not None)
    kept = [
        violation
        for violation in result.violations
        if violation.from_ref_id in nodes or violation.file_path in staged
    ]
    return CommitLintScope(
        result=replace(result, violations=kept),
        staged=len(staged),
        owned=sum(1 for owner in owners.values() if owner is not None),
        nodes=tuple(sorted(nodes)),
        left_out=len(result.violations) - len(kept),
    )


def _listed_nodes(nodes: tuple[str, ...]) -> str:
    """The node names, the list cut after :data:`_NODES_NAMED` with the rest counted."""
    shown = ", ".join(nodes[:_NODES_NAMED])
    rest = len(nodes) - _NODES_NAMED
    return f"{shown}, and {rest} more" if rest > 0 else shown
