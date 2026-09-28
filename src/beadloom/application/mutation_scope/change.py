# beadloom:domain=application
# beadloom:component=mutation-scope
"""The population of a change: the functions it touched in the declared scope (BDL-074 D1).

A pull request mutates the functions it changed and runs the tests the binding
ties to their node, instead of mutating the whole declared scope against a
static pool — which is what took the nightly past its runner's limit. This
module answers the runner-independent half of that: **which functions, owned by
which node, bound to which tests**. Turning a function into a runner's mutant
names is the runner's business and stays out of the product (BDL-061 CONTEXT Q5).

**Every part of the answer says what it covered.** The files the change left
lines in are counted, the ones inside the declared scope are named, a changed
line outside any function is counted because no mutant of it exists, a file
that is not readable Python is named rather than guessed, and the test files the
binding has not placed yet are listed — because while they exist, a node's
bound tests can be short of the tests that actually exercise it. An empty
population is a statement too: a change that touches no function of the
declared scope has nothing to mutate and no score.

**Each kind of test file is selected by what it is (BDL-074 G1).** A file the
binding ties to the node is BOUND. An acceptance step file is selected when the
scenarios it loads carry the node's ``@node:`` tag (:mod:`.acceptance`). An
UNPLACED file — outside every kind folder, which the layout has not reached — is
the runner's fallback, because it may exercise the node and the binding cannot
say. A self-check tests the repository's own files rather than the changed code,
and a file under a mirrored folder whose code no node owns names code other than
the change's; neither is listed.

The diff is taken against the MERGE BASE of a ref and the working tree, so a
pull request's own commits are measured in CI (where the tree is the commit) and
uncommitted edits are measured locally. Untracked files are not in a git diff.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from beadloom.application.mutation_scope.acceptance import acceptance_files_by_node
from beadloom.application.mutation_scope.scope import lies_within, load_mutation_targets
from beadloom.application.mutation_scope.touched import changed_lines, touched_functions
from beadloom.context_oracle.test_binding import describe_unbound
from beadloom.graph.rules.suite_tables import read_test_files
from beadloom.infrastructure.repository import (
    KIND_ACCEPTANCE,
    PLACEMENT_UNPLACED,
    count_other_kind_test_files,
    count_test_files_by_placement,
    get_owning_ref_id,
)

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Iterable, Mapping
    from pathlib import Path

    from beadloom.graph.rules.suite_tables import IndexedTestFile

#: The only source this module reads functions from.
_PYTHON = ".py"


class MutationChangeError(RuntimeError):
    """The change cannot be read: git is absent, or the base names no commit."""


@dataclass(frozen=True)
class ChangedFunction:
    """One function a change touched: its file, its name, the node owning the file."""

    path: str
    name: str
    node: str | None


@dataclass(frozen=True)
class NodeSelection:
    """A node the change reaches: its touched functions, and the tests selected for it.

    ``bound_tests`` are the files the binding ties to the node; ``acceptance_tests``
    the step files whose loaded scenarios carry its ``@node:`` tag.
    """

    node: str | None
    functions: tuple[str, ...]
    bound_tests: tuple[str, ...]
    acceptance_tests: tuple[str, ...] = ()


@dataclass(frozen=True)
class ChangePlan:
    """The population of a change, over the declared scope, the graph and the binding.

    ``unplaced_tests`` lists the test files placed under no kind folder: the
    runner's fallback selection (BDL-074 G1). What the plan STATES about the files
    bound to no node is counted by reason from ``test_placements`` and
    ``other_kinds``, so its unplaced count is the one ``ctx`` and the debt report
    state (BDL-074 F1).
    """

    base: str
    files_changed: int
    files_in_scope: tuple[str, ...]
    unread: tuple[str, ...]
    functions: tuple[ChangedFunction, ...]
    outside_lines: int
    nodes: tuple[NodeSelection, ...]
    unplaced_tests: tuple[str, ...]
    test_files: int
    test_placements: Mapping[str, int] = field(default_factory=dict)
    other_kinds: Mapping[str, int] = field(default_factory=dict)

    @property
    def empty(self) -> bool:
        """Whether the change touched no function a run could mutate."""
        return not self.functions

    @property
    def mutated_files(self) -> tuple[str, ...]:
        """The files holding a touched function, in order: what a run covers."""
        return tuple(dict.fromkeys(function.path for function in self.functions))


def diff_since(project_root: Path, base: str) -> str:
    """The zero-context diff between the merge base of *base* and the working tree."""
    merge_base = _git(project_root, "merge-base", base, "HEAD").strip()
    return _git(
        project_root,
        "diff",
        "--unified=0",
        "--no-color",
        "--no-renames",
        "--no-ext-diff",
        "--relative",
        merge_base,
        "--",
    )


def _git(project_root: Path, *args: str) -> str:
    try:
        result = subprocess.run(  # noqa: S603 - a fixed git argv; the ref is an argument
            ["git", *args],  # noqa: S607
            cwd=project_root,
            capture_output=True,
            encoding="utf-8",
            check=False,
        )
    except FileNotFoundError as error:
        msg = "git is not installed, so no change can be read"
        raise MutationChangeError(msg) from error
    if result.returncode != 0:
        msg = f"git {' '.join(args)} failed: {result.stderr.strip() or result.returncode}"
        raise MutationChangeError(msg)
    return result.stdout


def plan_change(
    project_root: Path, conn: sqlite3.Connection, diff_text: str, *, base: str
) -> ChangePlan:
    """The functions *diff_text* touched in the declared scope, by node and binding."""
    declared = load_mutation_targets(project_root)
    touched = changed_lines(diff_text)
    in_scope = tuple(sorted(path for path in touched if lies_within(path, declared)))
    functions: list[ChangedFunction] = []
    unread: list[str] = []
    outside = 0
    for path in in_scope:
        source = _python_source(project_root / path)
        if source is None:
            unread.append(path)
            continue
        try:
            result = touched_functions(source, touched[path])
        except (SyntaxError, ValueError):
            unread.append(path)
            continue
        outside += result.outside
        owner = get_owning_ref_id(conn, path)
        functions.extend(ChangedFunction(path, name, owner) for name in result.functions)
    test_files = read_test_files(conn) or []
    return ChangePlan(
        base=base,
        files_changed=len(touched),
        files_in_scope=in_scope,
        unread=tuple(unread),
        functions=tuple(functions),
        outside_lines=outside,
        nodes=_node_selections(project_root, functions, test_files),
        unplaced_tests=tuple(
            test.path for test in test_files if test.placement == PLACEMENT_UNPLACED
        ),
        test_files=len(test_files),
        test_placements=count_test_files_by_placement(conn),
        other_kinds=count_other_kind_test_files(conn),
    )


def _python_source(path: Path) -> str | None:
    if path.suffix != _PYTHON or not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _node_selections(
    project_root: Path,
    functions: Iterable[ChangedFunction],
    test_files: list[IndexedTestFile],
) -> tuple[NodeSelection, ...]:
    """One selection per node the change reaches, in the order the change reaches it.

    A file is bound when the binding recorded a node for it, whatever placement
    bound it: the mirror, a ``tests:`` declaration, or any placement added later.
    """
    names: dict[str | None, list[str]] = {}
    for function in functions:
        names.setdefault(function.node, []).append(function.name)
    step_files = [test.path for test in test_files if test.kind == KIND_ACCEPTANCE]
    by_tag = acceptance_files_by_node(project_root, step_files) if names else {}
    return tuple(
        NodeSelection(
            node=node,
            functions=tuple(dict.fromkeys(touched)),
            bound_tests=tuple(
                test.path for test in test_files if node is not None and test.ref_id == node
            ),
            acceptance_tests=by_tag.get(node, ()) if node is not None else (),
        )
        for node, touched in names.items()
    )


def describe_change(plan: ChangePlan) -> list[str]:
    """The change's population as lines, each one a statement of what was covered."""
    lines = [
        f"Change since {plan.base}: {plan.files_changed} file(s) changed, "
        f"{len(plan.files_in_scope)} of them in the declared scope"
    ]
    if plan.empty:
        lines.append(
            "Population: empty — the change touches no function of the declared "
            "scope, so there is nothing to mutate and no score"
        )
    else:
        reached = ", ".join(selection.node or "(no node)" for selection in plan.nodes)
        lines.append(
            f"Population: {len(plan.functions)} function(s) in "
            f"{len(plan.mutated_files)} file(s) of the declared scope, over "
            f"{len(plan.nodes)} node(s): {reached}"
        )
        lines.extend(_describe_selection(selection) for selection in plan.nodes)
    if plan.outside_lines:
        lines.append(
            f"{plan.outside_lines} changed line(s) in the declared scope lie outside "
            f"any function, where no mutant exists"
        )
    if plan.unread:
        lines.append(
            f"Not read: {', '.join(plan.unread)} — only Python source that parses "
            f"is read, so the functions these files hold are not counted"
        )
    unbound = describe_unbound(plan.test_placements, plan.other_kinds)
    if unbound is not None:
        lines.append(
            f"Binding: {unbound} — so the tests bound to a node can be short of the "
            f"tests that exercise it"
        )
    return lines


def _describe_selection(selection: NodeSelection) -> str:
    bound = (
        f"{len(selection.bound_tests)} test file(s) bound"
        if selection.bound_tests
        else "no test file is bound to it"
    )
    if selection.acceptance_tests:
        bound += f", {len(selection.acceptance_tests)} acceptance step file(s) by tag"
    return f"  {selection.node or '(no node)'}: {', '.join(selection.functions)}; {bound}"


def change_payload(plan: ChangePlan) -> dict[str, object]:
    """The change in the JSON shape the ``mutation`` command prints."""
    return {
        "base": plan.base,
        "files_changed": plan.files_changed,
        "files_in_scope": list(plan.files_in_scope),
        "unread": list(plan.unread),
        "functions": [
            {"path": function.path, "name": function.name, "node": function.node}
            for function in plan.functions
        ],
        "outside_lines": plan.outside_lines,
        "nodes": [
            {
                "node": selection.node,
                "functions": list(selection.functions),
                "bound_tests": list(selection.bound_tests),
                "acceptance_tests": list(selection.acceptance_tests),
            }
            for selection in plan.nodes
        ],
        "test_files": plan.test_files,
        "unplaced_tests": list(plan.unplaced_tests),
        "test_placements": dict(plan.test_placements),
        "other_kinds": dict(plan.other_kinds),
        "empty": plan.empty,
    }
