"""Every branch of `init` that reaches the bootstrap, read out of the source.

BDL-067 `.7`, covering `.6`. The defect `.6` fixed was that the default wizard
took no verdict over the graph it had just written. The defect *this* module
exists for is one level up, and it is the reason the wizard shipped unguarded
through four green waves: the suite could not tell a monkeypatch **binding**
from a **branch** of `init`.

`init --yes` and the default wizard both reach `bootstrap_project` through the
name `init_flow` bound at import time, so one `monkeypatch.setattr` sabotages
both; `init --bootstrap` imports the function inside the command body and needs
its own patch. Two bindings, three branches. The behavioural module
(`tests/test_init_verdict_over_its_own_rules.py`) counted the bindings, a
comment called them "the two ways `init` reaches the bootstrap", and the branch
a human adopter meets first was never run.

`.6` corrected that count by hand, which leaves the same defect available at a
larger number: `THE_BRANCHES` is a tuple somebody maintains, and a fourth branch
added to the command joins the code without joining the tuple. So nothing here
is written out by hand. The command's own source is parsed, every call that
reaches `bootstrap_project` is found, and each one is asserted to be followed by
the Gate's verdict. A fourth branch fails these tests on the day it is written,
whether or not anyone remembers this file.

The instrument is tested before it is trusted (`TestTheEnumeratorItself`): a
scan that silently found nothing would make every assertion below pass while
asserting nothing, which is the exact failure mode this bead is about. The
synthetic commands there are mutants of the real shape — a fourth branch with no
verdict, a fourth branch with one, and a verdict written after the `return` that
makes it unreachable — and the enumerator's verdict on each is asserted.

Known limits, stated rather than discovered later:

- The reachability scan is over the package that owns `bootstrap_project`
  (`beadloom.onboarding`). A branch that reached the bootstrap through some
  *other* package would not be seen. That boundary is the DDD layering — the
  bootstrap is onboarding's, and `services/commands` calls into it — but it is
  an assumption, not a proof.
- Reachability is matched on the callee's *name*, not on a resolved import, so
  two same-named functions in the package are one name here. The set it produces
  is asserted to contain the three names that actually matter.
- A verdict call anywhere in a following statement counts, including inside an
  `if` whose condition is some unrelated path. The enumerator answers "could
  this branch report", not "does it report on every path".
"""

from __future__ import annotations

import ast
import inspect
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from beadloom import onboarding
from beadloom.onboarding.scanner.bootstrap import bootstrap_project
from beadloom.services.commands import setup as init_command
from tests.test_init_verdict_over_its_own_rules import THE_BRANCHES

if TYPE_CHECKING:
    from types import ModuleType

#: The name of the function that takes the Gate's verdict, read off the function
#: object instead of written out: a rename fails at import here rather than
#: leaving a scan that quietly finds no verdict anywhere and reports every branch
#: as unguarded.
THE_VERDICT = init_command._verdict_on_the_generated_graph.__name__

#: The function every reachability question here is seeded from.
THE_BOOTSTRAP = bootstrap_project.__name__

#: The command under examination, by the name it has in its module.
THE_COMMAND = "init"


@dataclass(frozen=True)
class BootstrapCallSite:
    """One call inside `init` that ends in a bootstrap, and what follows it.

    ``guard`` is the chain of `if` conditions the call sits under, outermost
    first, as the source spells them. It is the branch's identity: the empty
    tuple is the fallthrough (the default interactive wizard), which is exactly
    the branch a binding-shaped count cannot see.
    """

    #: The name called, e.g. ``bootstrap_project`` or ``interactive_init``.
    callee: str
    #: The `if` conditions this call sits under, outermost first.
    guard: tuple[str, ...]
    #: Whether the Gate's verdict is reachable after this call in this branch.
    takes_verdict: bool
    #: Line number in the command's module, so a failure names a place.
    lineno: int


def _called_names(node: ast.AST) -> set[str]:
    """Every function name called anywhere inside *node*."""
    names: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            names.add(_callee_name(child))
    return names


def _callee_name(call: ast.Call) -> str:
    """The bare name a call names, ignoring what it is an attribute of."""
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return ""


def _functions_to_their_calls(package: ModuleType) -> dict[str, set[str]]:
    """Map every function defined in *package*'s source to the names it calls."""
    root = Path(inspect.getfile(package)).parent
    calls: dict[str, set[str]] = {}
    for path in sorted(root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                calls.setdefault(node.name, set()).update(_called_names(node))
    return calls


def _callables_that_reach_the_bootstrap(package: ModuleType) -> frozenset[str]:
    """Names that end in a `bootstrap_project` call, directly or through others.

    A least fixed point over *package*: seeded with the bootstrap itself, then
    grown with anything that calls something already in the set. `init` reaching
    any of these names is `init` reaching the bootstrap.
    """
    calls = _functions_to_their_calls(package)
    reaching = {THE_BOOTSTRAP}
    growing = True
    while growing:
        growing = False
        for name, called in calls.items():
            if name not in reaching and called & reaching:
                reaching.add(name)
                growing = True
    return frozenset(reaching)


def _statement_trail(
    node: ast.AST, parents: dict[ast.AST, ast.AST]
) -> list[tuple[list[ast.stmt], int]]:
    """The blocks *node* sits in, outermost first, each with its index in it."""
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


def _guard_path(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> tuple[str, ...]:
    """The `if` conditions *node* sits under, outermost first, as written."""
    conditions: list[str] = []
    current = node
    while current in parents:
        parent = parents[current]
        if isinstance(parent, ast.If):
            if any(s is current for s in parent.body):
                conditions.append(ast.unparse(parent.test))
            elif any(s is current for s in parent.orelse):
                conditions.append(f"not ({ast.unparse(parent.test)})")
        current = parent
    return tuple(reversed(conditions))


def _verdict_follows(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> bool:
    """Whether the verdict can still run after *node*, in execution order.

    Walks what comes after the call: the rest of its own block first, then the
    rest of each enclosing block. A bare `return` or `raise` at any of those
    levels ends the walk — nothing after it in that branch runs, so a verdict
    written below it is not a verdict this branch takes.
    """
    for block, index in reversed(_statement_trail(node, parents)):
        for statement in block[index + 1 :]:
            if THE_VERDICT in _called_names(statement):
                return True
            if isinstance(statement, ast.Return | ast.Raise):
                return False
    return False


def _function_named(name: str, tree: ast.Module) -> ast.FunctionDef:
    """The one function called *name* in *tree*. A missing one is a failure."""
    found = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == name
    ]
    assert found, f"no function named {name!r} in the parsed source"
    return found[0]


def _call_sites_in(source: str, reaching: frozenset[str]) -> tuple[BootstrapCallSite, ...]:
    """Every call in *source*'s `init` that reaches the bootstrap, in order."""
    command = _function_named(THE_COMMAND, ast.parse(source))
    parents: dict[ast.AST, ast.AST] = {
        child: parent
        for parent in ast.walk(command)
        for child in ast.iter_child_nodes(parent)
    }
    sites = [
        BootstrapCallSite(
            callee=_callee_name(node),
            guard=_guard_path(node, parents),
            takes_verdict=_verdict_follows(node, parents),
            lineno=node.lineno,
        )
        for node in ast.walk(command)
        if isinstance(node, ast.Call) and _callee_name(node) in reaching
    ]
    return tuple(sorted(sites, key=lambda site: site.lineno))


def _the_commands_source() -> str:
    """The source file `init` is defined in, as the imported module resolves it."""
    return Path(inspect.getfile(init_command)).read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def reaching() -> frozenset[str]:
    """The names that end in a bootstrap, derived from onboarding's source."""
    return _callables_that_reach_the_bootstrap(onboarding)


@pytest.fixture(scope="module")
def call_sites(reaching: frozenset[str]) -> tuple[BootstrapCallSite, ...]:
    """Every bootstrap-reaching call in the real `init`, in source order."""
    return _call_sites_in(_the_commands_source(), reaching)


#: A command with the shape the real one has: two flag branches that return, and
#: a fallthrough wizard. The mutants below are edits of this, so what the
#: enumerator says about them is a difference this text makes and nothing else.
A_COMMAND_LIKE_INIT = """
def init(*, non_interactive, bootstrap, rescan, project):
    project_root = project
    if non_interactive:
        result = non_interactive_init(project_root)
        click.echo(result)
        VERDICT(project_root)
        return
    if bootstrap:
        result = bootstrap_project(project_root)
        VERDICT(project_root)
        return
    result = interactive_init(project_root)
    if result["mode"] == "cancelled":
        sys.exit(0)
    if result["mode"] in ("bootstrap", "both"):
        VERDICT(project_root)
""".replace("VERDICT", THE_VERDICT)

#: A fourth branch, written the way a fourth branch gets written: it bootstraps
#: and returns, and nobody remembered the verdict. This is what must fail.
A_FOURTH_BRANCH_WITHOUT_A_VERDICT = A_COMMAND_LIKE_INIT.replace(
    "    result = interactive_init(project_root)",
    "    if rescan:\n"
    "        result = bootstrap_project(project_root)\n"
    "        return\n"
    "    result = interactive_init(project_root)",
)

#: The same fourth branch, guarded. The enumerator must accept it — a test that
#: called every fourth branch a defect would be no more informative than one that
#: called none of them.
A_FOURTH_BRANCH_WITH_A_VERDICT = A_COMMAND_LIKE_INIT.replace(
    "    result = interactive_init(project_root)",
    "    if rescan:\n"
    "        result = bootstrap_project(project_root)\n"
    f"        {THE_VERDICT}(project_root)\n"
    "        return\n"
    "    result = interactive_init(project_root)",
)

#: A verdict that is present in the branch and cannot run: the `return` is above
#: it. Reading the file for the call name alone would call this branch guarded.
A_VERDICT_BELOW_THE_RETURN = A_COMMAND_LIKE_INIT.replace(
    f"        {THE_VERDICT}(project_root)\n        return\n",
    f"        return\n        {THE_VERDICT}(project_root)\n",
    1,
)


class TestTheEnumeratorItself:
    """The instrument, before anything is trusted to it.

    An enumerator that found nothing would make every assertion in the next two
    classes pass over an empty set. That is the shape of the defect this bead
    closes, so it is asserted against here rather than assumed away.
    """

    def test_it_finds_the_callables_init_reaches_the_bootstrap_through(
        self, reaching: frozenset[str]
    ) -> None:
        """The three known ones, derived — not a list this test wrote down."""
        assert {THE_BOOTSTRAP, "non_interactive_init", "interactive_init"} <= reaching

    def test_it_reads_the_baseline_shape_as_three_branches(
        self, reaching: frozenset[str]
    ) -> None:
        """Two guarded branches and a fallthrough, which is `init`'s shape."""
        sites = _call_sites_in(A_COMMAND_LIKE_INIT, reaching)

        assert [site.guard for site in sites] == [("non_interactive",), ("bootstrap",), ()]

    def test_it_reports_a_fourth_branch_that_bootstraps_without_a_verdict(
        self, reaching: frozenset[str]
    ) -> None:
        """The failure this whole module exists to produce, produced on demand."""
        assert A_FOURTH_BRANCH_WITHOUT_A_VERDICT != A_COMMAND_LIKE_INIT, (
            "the anchor the mutation edits is gone, so this case is judging the "
            "unmutated command and the mutation it names never happened"
        )

        sites = _call_sites_in(A_FOURTH_BRANCH_WITHOUT_A_VERDICT, reaching)

        assert [site.guard for site in sites if not site.takes_verdict] == [("rescan",)]

    def test_it_accepts_a_fourth_branch_that_does_take_the_verdict(
        self, reaching: frozenset[str]
    ) -> None:
        assert A_FOURTH_BRANCH_WITH_A_VERDICT != A_COMMAND_LIKE_INIT, (
            "the anchor the mutation edits is gone"
        )

        sites = _call_sites_in(A_FOURTH_BRANCH_WITH_A_VERDICT, reaching)

        assert [site.guard for site in sites if not site.takes_verdict] == []
        assert ("rescan",) in [site.guard for site in sites]

    def test_it_does_not_count_a_verdict_the_return_above_it_makes_unreachable(
        self, reaching: frozenset[str]
    ) -> None:
        """Presence of the call is not the claim. Reaching it is."""
        assert A_VERDICT_BELOW_THE_RETURN != A_COMMAND_LIKE_INIT, (
            "the anchor the mutation edits is gone"
        )

        sites = _call_sites_in(A_VERDICT_BELOW_THE_RETURN, reaching)

        assert [site.guard for site in sites if not site.takes_verdict] == [("non_interactive",)]


class TestEveryBranchOfInitThatBootstrapsTakesAVerdict:
    """Read off `init`'s own source, so a branch added later is counted here."""

    def test_the_scan_finds_branches_to_judge(
        self, call_sites: tuple[BootstrapCallSite, ...]
    ) -> None:
        """Anti-vacuity: an empty scan would pass every assertion below it."""
        assert call_sites, (
            f"no call reaching {THE_BOOTSTRAP} was found in `{THE_COMMAND}` — the "
            "enumeration below would assert nothing"
        )

    def test_no_branch_reaches_the_bootstrap_without_taking_a_verdict(
        self, call_sites: tuple[BootstrapCallSite, ...]
    ) -> None:
        """The claim `.2` made about two branches, made about all of them.

        A fourth branch that writes a graph and returns without checking it
        against the rules it wrote fails here, whether or not anybody thought to
        add a case to `THE_BRANCHES`.
        """
        unguarded = [
            f"{site.callee} at line {site.lineno} under {site.guard or '<no flag>'}"
            for site in call_sites
            if not site.takes_verdict
        ]

        assert unguarded == [], (
            "a branch of `init` writes a bootstrap graph and never checks it "
            f"against the rules it wrote: {unguarded}"
        )


class TestTheParametrisedCasesCoverTheBranchesTheSourceHas:
    """The hand-maintained tuple, bound to the source it claims to enumerate.

    `THE_BRANCHES` drives every behavioural case in
    `tests/test_init_verdict_over_its_own_rules.py`. Nothing there fails when the
    tuple falls behind the command, because a case that is not written is a case
    that does not fail. These two assertions are what make it fail.
    """

    def test_every_branch_in_the_source_has_a_case(
        self, call_sites: tuple[BootstrapCallSite, ...]
    ) -> None:
        declared = {branch.guard for branch in THE_BRANCHES}
        found = {site.guard for site in call_sites}

        assert found <= declared, (
            f"branches of `{THE_COMMAND}` with no case in THE_BRANCHES: "
            f"{sorted(found - declared)}"
        )

    def test_no_case_claims_a_branch_the_source_does_not_have(
        self, call_sites: tuple[BootstrapCallSite, ...]
    ) -> None:
        """A case for a branch that was deleted tests nothing and says it does."""
        declared = {branch.guard for branch in THE_BRANCHES}
        found = {site.guard for site in call_sites}

        assert declared <= found, (
            f"THE_BRANCHES names branches `{THE_COMMAND}` does not have: "
            f"{sorted(declared - found)}"
        )
