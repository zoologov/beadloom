"""Every function that calls `evaluate_all` is named, with what carries the population on.

A caller of the rule engine's evaluator past `lint()` is a surface that reports a
lint result without a `LintResult`, so it must carry the population another way.
A new caller fails here first and is asked what it tells its reader.

**What this module cannot see.** The caller-set derivation follows `import` and
`from ... import` by name (including `as`), so a module that reaches
`evaluate_all` through `importlib` or an attribute chain is outside it. It is a
guard, not a proof, and the limit is stated in the case that depends on it.

Split out of ``tests/test_every_surface_past_lint_states_the_population.py``
by node (BDL-074 E1); the behaviour is BDL-070 A4's (`beadloom-q6jh`). A4 is
additive at every surface: nothing here changes a count, and whether an advisory
statement counts as a violation is decided once, on `LintResult`.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import beadloom

#: The name the evaluator is called by. Read off the function object so a rename
#: fails at import here rather than leaving a scan that finds no call site and
#: reports every claim below as satisfied.
THE_EVALUATOR = "evaluate_all"


#: The modules `evaluate_all` can be imported from: the one it is defined in and
#: the two that re-export it. Every caller in the product names one of them.
THE_EVALUATOR_MODULES = frozenset(
    {"beadloom.graph.rules", "beadloom.graph.rule_engine", "beadloom.graph"}
)


#: Every function in `src/` that calls the evaluator, mapped to the name in its
#: own module that carries the population onward. Compared for EQUALITY, so a
#: FOURTH call site fails here and is asked the question this bead exists to
#: ask: what does this surface tell its reader about how much of the graph its
#: answer covers?
#:
#: `linter._evaluate` and `debt_report._count_violations` count the reaches
#: themselves, from the same `reach_of` the evaluator uses, so they name the
#: counter. `tui.data_providers.refresh` does neither: it hands the finding on
#: whole, and the population travels as a FIELD of it, so the name is the field.
#: That token is weak evidence on its own, which is why it is evidence and not
#: the check — `TestTheTuiPanelStatesThePopulation` is what holds the behaviour.
THE_CALLERS: dict[str, str] = {
    "beadloom/graph/linter.py::_evaluate": "layer_rule_reaches",
    "beadloom/tui/data_providers.py::refresh": "rule_type",
    "beadloom/application/debt_report/collect.py::_count_violations": ("layer_rule_reaches"),
}


def _package_root() -> Path:
    return Path(inspect.getfile(beadloom)).parent


def _evaluator_names_in(tree: ast.Module) -> set[str]:
    """The local names bound to the evaluator in this file, `as` included."""
    return {
        alias.asname or alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module in THE_EVALUATOR_MODULES
        for alias in node.names
        if alias.name == THE_EVALUATOR
    }


def _callers_in(path: Path, relative: str) -> dict[str, str]:
    """`module::function` for every function in *path* that calls the evaluator."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names = _evaluator_names_in(tree)
    if not names:
        return {}
    source = path.read_text(encoding="utf-8")
    found: dict[str, str] = {}
    for function in ast.walk(tree):
        if not isinstance(function, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        calls = any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in names
            for node in ast.walk(function)
        )
        if calls:
            found[f"{relative}::{function.name}"] = source
    return found


def _derived_callers() -> dict[str, str]:
    root = _package_root()
    callers: dict[str, str] = {}
    for path in sorted(root.rglob("*.py")):
        relative = f"beadloom/{path.relative_to(root).as_posix()}"
        callers.update(_callers_in(path, relative))
    return callers


class TestEveryCallerOfTheEvaluatorIsNamed:
    """A new caller of `evaluate_all` is a new surface, and it fails here first."""

    def test_the_derived_set_is_the_named_set(self) -> None:
        assert set(_derived_callers()) == set(THE_CALLERS)

    def test_each_caller_names_what_carries_the_population(self) -> None:
        """Evidence, not proof: the module names the thing that carries the reach."""
        unhandled = [
            caller
            for caller, source in _derived_callers().items()
            if THE_CALLERS.get(caller, "\0") not in source
        ]
        assert unhandled == []

    def test_a_caller_reached_under_a_name_this_scan_cannot_see(self) -> None:
        """The stated ceiling: an attribute call binds no name this scan reads."""
        tree = ast.parse(
            "from beadloom.graph import rule_engine\n"
            "def surface(conn, rules):\n"
            "    return rule_engine.evaluate_all(conn, rules)\n"
        )
        assert _evaluator_names_in(tree) == set()
