"""Step implementations for BDL-068 S1.6 — a commit judged against declared axes.

Thin by design: every step builds a real ``## Axes`` section, reads it through
the real grammar and runs the real check. Nothing is doubled, because a
scenario that passes against a double proves the double.

The module is named ``test_*`` so default pytest collection picks the scenarios
up — the acceptance suite runs inside ``uv run pytest``, not beside it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from pytest_bdd import given, scenarios, then, when

from beadloom.doc_sync.axes_section import read_axes_section
from beadloom.doc_sync.scope_check import (
    OUTSIDE_THE_DECLARED_AXES,
    check_commit_scope,
    declared_scope,
)

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../features/declared_axes.feature")

#: Where every fixture path is owned, so a scenario says what it means rather
#: than restating a mapping in each step.
_OWNERSHIP: dict[str, tuple[str | None, str | None]] = {
    "src/beadloom/doc_sync/engine.py": ("sync-check", "doc-sync"),
    "src/beadloom/doc_sync/scanner.py": ("scanner", "doc-sync"),
    "src/beadloom/graph/linter.py": ("rule-engine", "graph"),
    "src/beadloom/doc_sync/axes_section.py": ("axes-section", "doc-sync"),
    "README.md": (None, None),
}

_NODE_CONTEXTS = {
    "sync-check": "doc-sync",
    "scanner": "doc-sync",
    "rule-engine": "graph",
    "axes-section": "doc-sync",
}


def _section(rows: str, derived_by: str = "`beadloom impact` over `x.py`") -> str:
    return (
        "## Axes\n\n"
        f"> **Derived by:** {derived_by}\n"
        "> **Seed:** `none`, under the rule `reaches-an-effect-sink`\n"
        "> **Unresolved:** none\n\n"
        "| Axis | Node | Sites | In scope | Why |\n"
        "|---|---|---|---|---|\n" + rows
    )


@pytest.fixture
def state() -> dict[str, Any]:
    return {}


@given("a work item whose declared axes reach one bounded context")
def _one_context(state: dict[str, Any]) -> None:
    state["text"] = _section(
        "| callers | sync-check | 1 — `doc_sync/engine.py:10` | yes | the surface |\n"
    )


@given("a work item whose axes name a node and rule it out of scope")
def _ruled_out(state: dict[str, Any]) -> None:
    state["text"] = _section(
        "| callers | sync-check | 1 — `doc_sync/engine.py:10` | yes | the surface |\n"
        "| co-writers | scanner | 2 — `doc_sync/scanner.py:40` | no | not this work item |\n"
    )


@given("a work item whose Axes section names the target it was derived over")
def _names_target(state: dict[str, Any]) -> None:
    state["text"] = _section(
        "| callers | sync-check | 1 — `doc_sync/engine.py:10` | yes | the surface |\n",
        derived_by="`beadloom impact` over `graph/linter.py`",
    )
    state["targets"] = ("rule-engine",)


@given("a work item whose axes carry a row nobody decided")
def _undecided(state: dict[str, Any]) -> None:
    state["text"] = _section(
        "| callers | sync-check | 1 — `doc_sync/engine.py:10` | yes | the surface |\n"
        "| callers | rule-engine | 1 — `graph/linter.py:5` | ? |  |\n"
    )


@given("a branch that names no work item")
def _no_work_item(state: dict[str, Any]) -> None:
    state["branch"] = "features/NOT-A-KEY"


@given("a work item carrying no Axes section")
def _no_section(state: dict[str, Any], tmp_path: Path) -> None:
    folder = tmp_path / ".claude" / "development" / "docs" / "features" / "KEY-1"
    folder.mkdir(parents=True)
    (folder / "BRIEF.md").write_text("# BRIEF\n\n## Problem\n\nnone.\n", encoding="utf-8")
    state["project_root"] = tmp_path
    state["branch"] = "features/KEY-1"


def _judge(state: dict[str, Any], paths: tuple[str, ...]) -> None:
    section = read_axes_section(state["text"])
    assert section is not None
    scope = declared_scope(
        section,
        document="RFC.md",
        target_nodes=state.get("targets", ()),
        node_contexts=_NODE_CONTEXTS,
    )
    state["verdict"] = check_commit_scope(paths, scope, ownership=_OWNERSHIP)


@when("a commit staging a path in another bounded context is judged")
def _stage_other_context(state: dict[str, Any]) -> None:
    _judge(state, ("src/beadloom/graph/linter.py",))


@when("a commit staging a path that node owns is judged")
def _stage_ruled_out(state: dict[str, Any]) -> None:
    _judge(state, ("src/beadloom/doc_sync/scanner.py",))


@when("a commit staging a path a kept axis names is judged")
def _stage_kept(state: dict[str, Any]) -> None:
    _judge(state, ("src/beadloom/doc_sync/engine.py",))


@when("a commit staging a path in that context which no row names is judged")
def _stage_sibling(state: dict[str, Any]) -> None:
    _judge(state, ("src/beadloom/doc_sync/axes_section.py",))


@when("a commit staging a path no node owns is judged")
def _stage_unowned(state: dict[str, Any]) -> None:
    _judge(state, ("README.md",))


@when("a commit staging that target is judged")
def _stage_target(state: dict[str, Any]) -> None:
    _judge(state, ("src/beadloom/graph/linter.py",))


@when("a commit staging a path that row names is judged")
def _stage_undecided(state: dict[str, Any]) -> None:
    _judge(state, ("src/beadloom/graph/linter.py",))


@when("the branch is asked which work item's axes to judge against")
def _ask_branch(state: dict[str, Any], tmp_path: Path) -> None:
    from beadloom.application.declared_scope import scope_of_branch

    state["run"] = scope_of_branch(
        state.get("project_root", tmp_path), branch=state["branch"]
    )


@then("the path is reported as outside the declared axes")
def _reported(state: dict[str, Any]) -> None:
    findings = state["verdict"].findings
    assert len(findings) == 1, findings
    assert findings[0].check == OUTSIDE_THE_DECLARED_AXES


@then("nothing is reported")
def _silent(state: dict[str, Any]) -> None:
    assert state["verdict"].findings == ()


@then("the finding names every axis the work item declared")
def _names_axes(state: dict[str, Any]) -> None:
    assert "callers" in state["verdict"].findings[0].why


@then("the finding names the axis that ruled it out")
def _names_ruling_axis(state: dict[str, Any]) -> None:
    finding = state["verdict"].findings[0]
    assert "co-writers" in finding.excerpt
    assert "callers" not in finding.excerpt


@then("the verdict states how many staged paths no node owns")
def _states_unowned(state: dict[str, Any]) -> None:
    assert state["verdict"].unowned == 1


@then("the verdict states how many rows nobody decided")
def _states_undecided(state: dict[str, Any]) -> None:
    assert state["verdict"].undecided == 1


@then("the run reports that it checked nothing, with the reason")
def _not_checked(state: dict[str, Any]) -> None:
    scope, reason = state["run"]
    assert scope is None
    assert reason
