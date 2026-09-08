"""Step implementations for `features/guard_unresolved.feature` (beadloom-0mdo.60).

Against the real boundary, the real evaluator and the real probe set. The
inability is produced where it happened rather than described to a double: the
scenarios that need a guard which cannot run install a meta-path finder that
refuses ``beadloom.services.bd_seam``, so the ``ImportError`` is raised by the
interpreter at ``services/guard_probes.py:79`` — the exact line
``beadloom-0mdo.51`` met when ``git mv`` had moved the module and
``__init__.py`` did not yet exist. What the finder stands in for is only the
REASON the import fails; the failure, its site and everything downstream of it
are the product's own.

The verdicts are read through :func:`run_invocation`, which is the one function
the CLI and the harness hook both call, so a scenario here settles both callers.
``harness="claude-code"`` is passed because the whole question is what the bound
harness receives: the same inability answers a shell caller with a different
code, and that half is asserted in ``tests/test_guards_unresolved.py``.
"""

from __future__ import annotations

import importlib
import sys
from typing import TYPE_CHECKING, Any

import pytest
from pytest_bdd import given, scenarios, then, when

from beadloom.application.guards.contract import ClaimedBead, GuardProbes
from beadloom.application.guards.invocation import GuardInvocation, run_invocation
from beadloom.application.guards.liveness import build_liveness
from beadloom.application.guards.models import (
    EXIT_CODE_BLOCK,
    GuardOutcome,
)
from beadloom.services.guard_probes import build_probes

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

scenarios("../features/guard_unresolved.feature")

_GUARD = "bead-claimed"

#: The module `guard_probes` imports to reach the tracker — the one `.51` moved.
_PROBE_DEPENDENCY = "beadloom.services.bd_seam"

_VALID_FLOW = "guards:\n  bead-claimed:\n    strictness: {default: warn}\n"


class _Refuse:
    """A meta-path finder that makes one module genuinely unimportable."""

    def __init__(self, blocked: str) -> None:
        self._blocked = blocked

    def find_module(self, fullname: str, path: object = None) -> None:
        """Present for older import protocols; the modern hook is below."""
        return None

    def find_spec(self, fullname: str, path: object = None, target: object = None) -> None:
        if fullname == self._blocked or fullname.startswith(f"{self._blocked}."):
            msg = (
                f"cannot import name 'BdUnavailableError' from '{self._blocked}' "
                "(unknown location)"
            )
            raise ImportError(msg, name=fullname)
        return None


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    (tmp_path / ".beadloom").mkdir()
    (tmp_path / ".beadloom" / "flow.yml").write_text(_VALID_FLOW, encoding="utf-8")
    (tmp_path / ".beads").mkdir()
    return {"root": tmp_path, "probes_for": build_probes}


@pytest.fixture()
def unimportable_probe_dependency() -> Iterator[None]:
    """Make `beadloom.services.bd_seam` unimportable, exactly as a half-moved package is."""
    saved = {
        name: module
        for name, module in sys.modules.items()
        if name == _PROBE_DEPENDENCY or name.startswith(f"{_PROBE_DEPENDENCY}.")
    }
    for name in saved:
        del sys.modules[name]
    finder = _Refuse(_PROBE_DEPENDENCY)
    sys.meta_path.insert(0, finder)
    try:
        yield
    finally:
        sys.meta_path.remove(finder)
        sys.modules.update(saved)
        importlib.invalidate_caches()


@given("a project whose guard cannot import the probe it reaches the tracker through")
def _broken_probe(world: dict[str, Any], unimportable_probe_dependency: None) -> None:
    world["probes_for"] = build_probes


@given("a project whose flow.yml will not parse")
def _broken_flow(world: dict[str, Any]) -> None:
    (world["root"] / ".beadloom" / "flow.yml").write_text("guards: [1, 2\n", encoding="utf-8")


@given("a bead is claimed")
def _claimed(world: dict[str, Any]) -> None:
    class _Tracker:
        def claimed_beads(self) -> tuple[ClaimedBead, ...]:
            return (ClaimedBead(id="beadloom-0mdo.60", title="the verdict on inability"),)

    world["probes_for"] = lambda _root: GuardProbes(tracker=_Tracker())


def _ask(world: dict[str, Any], path: str) -> None:
    world["result"] = run_invocation(
        GuardInvocation(
            name=_GUARD,
            declared_project=world["root"],
            harness="claude-code",
            context_pairs=(f"path={path}",),
            probes_for=world["probes_for"],
        )
    )


@when("the harness asks that guard about a write to that project")
def _ask_about_a_write(world: dict[str, Any]) -> None:
    _ask(world, str(world["root"] / "src" / "beadloom" / "services" / "bd_seam" / "__init__.py"))


@when("the guard is asked about an edit target it refuses to interpret")
def _ask_about_a_refused_target(world: dict[str, Any]) -> None:
    _ask(world, "src/beadloom\x00/services.py")


@then("the verdict is unresolved")
def _unresolved(world: dict[str, Any]) -> None:
    assert world["result"].verdict.outcome is GuardOutcome.UNRESOLVED


@then("the verdict is an error about the edit")
def _error(world: dict[str, Any]) -> None:
    assert world["result"].verdict.outcome is GuardOutcome.ERROR


@then("the edit is permitted")
def _permitted(world: dict[str, Any]) -> None:
    assert world["result"].exit_code != EXIT_CODE_BLOCK


@then("the edit is blocked")
def _blocked(world: dict[str, Any]) -> None:
    assert world["result"].exit_code == EXIT_CODE_BLOCK


@then("the verdict states that nothing was checked")
def _states_nothing_checked(world: dict[str, Any]) -> None:
    verdict = world["result"].verdict
    assert verdict.not_covered
    assert any("bead-claimed" in item for item in verdict.not_covered)


@then("the verdict is not a pass")
def _not_a_pass(world: dict[str, Any]) -> None:
    assert world["result"].verdict.outcome is not GuardOutcome.PASS


@then("the exit code is not the one a passing guard returns")
def _not_the_passing_code(world: dict[str, Any]) -> None:
    assert world["result"].exit_code != 0


@then("the remediation does not claim the edit is blocked")
def _remediation_is_reachable(world: dict[str, Any]) -> None:
    assert "blocked" not in world["result"].verdict.remediation


@then("the liveness report still calls that guard never-fired")
def _never_fired(world: dict[str, Any]) -> None:
    assert world["result"].recorded
    rows = {row.guard: row for row in build_liveness(world["root"])}
    assert rows[_GUARD].never_fired
