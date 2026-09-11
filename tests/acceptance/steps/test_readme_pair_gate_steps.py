"""Step implementations for BDL-069 S4 — the `readme-pair` Gate leg.

Thin by design: each step builds a real project root and runs the real gate, so
the scenario is red for the reason the leg is missing rather than for the reason
a double was not wired up.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from pytest_bdd import given, scenarios, then, when

from beadloom.application.gate import run_ci_gate
from beadloom.onboarding.scanner import generate_agents_md

if TYPE_CHECKING:
    from pathlib import Path

    from beadloom.application.gate import GateStep

scenarios("../features/readme_pair_gate.feature")

STEP_NAME = "readme-pair"


@pytest.fixture()
def world() -> dict[str, Any]:
    """The one mutable bag the steps share, kept explicit rather than global."""
    return {}


def _project(root: Path) -> None:
    (root / ".beadloom" / "_graph").mkdir(parents=True, exist_ok=True)
    generate_agents_md(root)


def _declare(root: Path) -> None:
    config = root / ".beadloom" / "config.yml"
    existing = config.read_text(encoding="utf-8") if config.is_file() else ""
    config.write_text(
        existing + "\ndocument_pairs:\n  - source: README.md\n    follower: README.ru.md\n",
        encoding="utf-8",
    )


def _step(world: dict[str, Any]) -> GateStep:
    step: GateStep = world["step"]
    return step


@given("a project that declares no document pair")
def _no_pair(tmp_path: Path, world: dict[str, Any]) -> None:
    _project(tmp_path)
    world["root"] = tmp_path


@given("a project whose declared follower is missing a paragraph its source has")
def _diverging_pair(tmp_path: Path, world: dict[str, Any]) -> None:
    (tmp_path / "README.md").write_text(
        "# Title\n\nFirst paragraph.\n\nSecond paragraph.\n", encoding="utf-8"
    )
    (tmp_path / "README.ru.md").write_text(
        "# Zagolovok\n\nPervyi abzats.\n", encoding="utf-8"
    )
    _project(tmp_path)
    _declare(tmp_path)
    world["root"] = tmp_path


@when("the gate runs")
def _run_gate(world: dict[str, Any]) -> None:
    result = run_ci_gate(world["root"], fail_on=None, hub_exports=[], no_reindex=False)
    world["result"] = result
    world["step"] = next(step for step in result.steps if step.name == STEP_NAME)


@then("the readme-pair step is a skip that names the config block to add")
def _named_skip(world: dict[str, Any]) -> None:
    step = _step(world)
    assert step.skipped is True
    assert step.status == "SKIP"
    assert "document_pairs" in step.summary


@then("the gate verdict is green")
def _green(world: dict[str, Any]) -> None:
    assert world["result"].ok is True


@then("the readme-pair step fails and the gate verdict is red")
def _red(world: dict[str, Any]) -> None:
    assert _step(world).passed is False
    assert world["result"].ok is False


@then("the readme-pair line names the pair it held and the blocks it compared")
def _names_population(world: dict[str, Any]) -> None:
    summary = _step(world).summary
    assert "1 pair(s) held" in summary
    assert "block(s) compared" in summary
    assert "README.md <-> README.ru.md" in summary
