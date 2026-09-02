# beadloom:domain=application
# beadloom:component=source-derivation
"""How many branches a command has, and what still runs after each of them.

The question is *how many ways does this command do the thing*, answered from
the command's own source. BDL-067 `.7` is the measurement behind it: a suite
could not tell a monkeypatch BINDING from a BRANCH, counted two where there were
three, and the branch a human adopter meets first was never run for four waves.

A branch is identified by the chain of `if` conditions a call sits under, as the
source spells them. The empty tuple is the fallthrough — which is exactly the
branch a binding-shaped count cannot see.

Two ceilings, stated rather than discovered later:

- A marker call anywhere in a following statement counts, including inside an
  `if` whose condition is some unrelated path. This answers "could this branch
  reach the marker", not "does it reach it on every path".
- **The reading is syntactic.** It reads that a call follows a branch; it cannot
  read what that call SEES. MEASURED: `init --yes --mode both` carried the
  verdict call and passed this reading while judging an index written before the
  run's last graph file, and reported clean over a tree the adopter's next
  `lint --strict` failed. Nothing here could have caught that.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass

from beadloom.application.source_derivation.calls import called_names, callee_name
from beadloom.application.source_derivation.source_tree import function_named
from beadloom.application.source_derivation.termination import ends_the_branch


@dataclass(frozen=True)
class CallSite:
    """One call inside a command, the branch it sits in, and what follows it."""

    #: The name called, e.g. ``bootstrap_project`` or ``interactive_init``.
    callee: str
    #: The `if` conditions this call sits under, outermost first, as written.
    guard: tuple[str, ...]
    #: Whether the marker call is still reachable after this call in this branch.
    reaches_marker: bool
    #: Line number in the parsed source, so a failure names a place.
    lineno: int
    #: The source of everything that still runs after the call in this branch.
    #: A branch that does not reach the marker has to say something to whoever
    #: ran it instead, and this is what that claim can be checked against.
    follows: str = ""


def call_sites_in(
    source: str,
    reaching: frozenset[str],
    *,
    command: str,
    marker: str,
    resolving_in: object,
) -> tuple[CallSite, ...]:
    """Every call in *source*'s *command* whose callee is in *reaching*, in order.

    *reaching* is a set of names — typically
    :func:`~beadloom.application.source_derivation.call_graph.callables_that_reach`
    — so what counts as an interesting call is derived elsewhere and this module
    only reads where those calls sit. *marker* is the call whose reachability
    after each site is recorded, and *resolving_in* is the module terminator
    names are resolved through.
    """
    function = function_named(command, ast.parse(source))
    parents: dict[ast.AST, ast.AST] = {
        child: parent
        for parent in ast.walk(function)
        for child in ast.iter_child_nodes(parent)
    }
    sites = [
        CallSite(
            callee=callee_name(node),
            guard=_guard_path(node, parents),
            reaches_marker=_marker_follows(node, parents, marker, resolving_in),
            lineno=node.lineno,
            follows=_what_follows(node, parents, resolving_in),
        )
        for node in ast.walk(function)
        if isinstance(node, ast.Call) and callee_name(node) in reaching
    ]
    return tuple(sorted(sites, key=lambda site: site.lineno))


def _guard_path(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> tuple[str, ...]:
    """The `if` conditions *node* sits under, outermost first, as written."""
    conditions: list[str] = []
    current = node
    while current in parents:
        parent = parents[current]
        if isinstance(parent, ast.If):
            if any(statement is current for statement in parent.body):
                conditions.append(ast.unparse(parent.test))
            elif any(statement is current for statement in parent.orelse):
                conditions.append(f"not ({ast.unparse(parent.test)})")
        current = parent
    return tuple(reversed(conditions))


def statement_trail(
    node: ast.AST, parents: dict[ast.AST, ast.AST]
) -> list[tuple[list[ast.stmt], int]]:
    """The blocks *node* sits in, outermost first, each with its index in it.

    Public because "what runs before and after this call, in its branch" is a
    question more than one derivation asks, and two derivations of one fact are
    two things that can disagree.
    """
    trail: list[tuple[list[ast.stmt], int]] = []
    current = node
    while current in parents:
        parent = parents[current]
        for field in ("body", "orelse", "finalbody"):
            block = getattr(parent, field, None)
            if isinstance(block, list):
                at = next((i for i, s in enumerate(block) if s is current), None)
                if at is not None:
                    trail.append((block, at))
                    break
        current = parent
    trail.reverse()
    return trail


def _marker_follows(
    node: ast.AST,
    parents: dict[ast.AST, ast.AST],
    marker: str,
    resolving_in: object,
) -> bool:
    """Whether *marker* can still run after *node*, in execution order.

    Walks what comes after the call: the rest of its own block first, then the
    rest of each enclosing block. A statement that ends the branch at any of
    those levels ends the walk — nothing after it in that branch runs, so a
    marker written below it is not one this branch reaches.
    """
    for block, index in reversed(statement_trail(node, parents)):
        for statement in block[index + 1 :]:
            if marker in called_names(statement):
                return True
            if ends_the_branch(statement, resolving_in):
                return False
    return False


def _what_follows(
    node: ast.AST, parents: dict[ast.AST, ast.AST], resolving_in: object
) -> str:
    """The source of everything that still runs after *node*, in this branch.

    The same walk :func:`_marker_follows` does, unparsed instead of searched, so
    a claim about what a branch TELLS its caller can be read off the branch
    rather than restated somewhere that can go stale.
    """
    written: list[str] = []
    for block, index in reversed(statement_trail(node, parents)):
        for statement in block[index + 1 :]:
            written.append(ast.unparse(statement))
            if ends_the_branch(statement, resolving_in):
                return "\n".join(written)
    return "\n".join(written)
