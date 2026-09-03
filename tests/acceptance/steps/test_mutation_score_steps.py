"""Step implementations for `features/mutation_score.feature` (BDL-068 S3.1).

Thin by design: each step arranges real files on disk and runs the real
`beadloom mutation` command through Click's runner. Nothing is doubled, because
a scenario that passes against a double proves the double.

The module is named ``test_*`` so default pytest collection picks the scenarios
up — the acceptance suite runs inside ``uv run pytest``, not beside it.
"""

from __future__ import annotations

import json
import platform
from typing import TYPE_CHECKING, Any

import pytest
from click.testing import CliRunner
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../features/mutation_score.feature")


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    """The one mutable bag the steps share, kept explicit rather than global."""
    return {"root": tmp_path}


def _declare(world: dict[str, Any], target: str) -> None:
    root = world["root"]
    (root / ".beadloom").mkdir(parents=True, exist_ok=True)
    (root / ".beadloom" / "config.yml").write_text(
        "languages:\n- .py\nscan_paths:\n- src\n", encoding="utf-8"
    )
    (root / ".beadloom" / "flow.yml").write_text(
        f"mutation:\n  targets:\n  - {target}\n", encoding="utf-8"
    )
    _place(root, target)


def _place(root: Path, target: str) -> None:
    """Put a Python file where a declared target says its code lives.

    A declaration whose path is not on disk is itself a finding since BDL-068
    S3.3 — `report_mutation_score` now asks the scope half about every target it
    judges — so an arrangement that only declares is arranging a broken project
    and would report two things at once. Placing the source keeps each test
    about the one state it names.
    """
    directory = root / target
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "unit.py").write_text("VALUE = 1\n", encoding="utf-8")


def _record_run(world: dict[str, Any], covered: str, **counters: int) -> None:
    stats = world["root"] / "stats.json"
    stats.write_text(json.dumps(counters), encoding="utf-8")
    world["args"] = ["--stats", str(stats), "--target", covered, "--tool", "a runner"]


@given(parsers.parse('a project declaring the mutation target "{target}"'))
def _a_project_declaring(world: dict[str, Any], target: str) -> None:
    _declare(world, target)


@given(
    parsers.parse(
        'a project declaring the mutation targets "{first}" and "{second}"'
    )
)
def _a_project_declaring_two(world: dict[str, Any], first: str, second: str) -> None:
    root = world["root"]
    (root / ".beadloom").mkdir(parents=True, exist_ok=True)
    (root / ".beadloom" / "config.yml").write_text(
        "languages:\n- .py\nscan_paths:\n- src\n", encoding="utf-8"
    )
    (root / ".beadloom" / "flow.yml").write_text(
        f"mutation:\n  targets:\n  - {first}\n  - {second}\n", encoding="utf-8"
    )
    _place(root, first)
    _place(root, second)


@given(parsers.parse('the run is answerable only for "{target}"'))
def _answerable_only_for(world: dict[str, Any], target: str) -> None:
    world["args"] = [*world["args"], "--only", target]


@given(parsers.parse('a run over "{covered}" that killed 8 of 10 mutants'))
def _a_run_that_killed_eight(world: dict[str, Any], covered: str) -> None:
    _record_run(world, covered, killed=8, survived=2, total=10)


@given(parsers.parse('a run over "{covered}" that produced no mutants at all'))
def _a_run_with_no_mutants(world: dict[str, Any], covered: str) -> None:
    _record_run(world, covered, killed=0, survived=0, total=0)


@given(
    parsers.parse(
        'a run over "{covered}" whose counters do not say how many were killed'
    )
)
def _a_run_missing_a_counter(world: dict[str, Any], covered: str) -> None:
    _record_run(world, covered, survived=2, total=10)


@when("the mutation score is reported")
def _report(world: dict[str, Any]) -> None:
    result = CliRunner().invoke(
        main,
        ["mutation", "--project", str(world["root"]), "--json", *world.get("args", [])],
    )
    world["result"] = result
    world["payload"] = json.loads(result.stdout) if result.stdout.startswith("{") else {}


@then(parsers.parse("the score is {percent:d} percent"))
def _the_score_is(world: dict[str, Any], percent: int) -> None:
    assert world["payload"]["score"] == pytest.approx(percent / 100)


@then("the report names the room the run was measured in")
def _the_room_is_named(world: dict[str, Any]) -> None:
    room = world["payload"]["room"]
    assert platform.python_version() in room
    assert platform.system() in room


@then("no score is stated")
def _no_score(world: dict[str, Any]) -> None:
    assert world["payload"]["score"] is None


@then("the run is reported as having produced no mutants")
def _zero_mutants_reported(world: dict[str, Any]) -> None:
    assert "mutation-run-zero-mutants" in _checks(world)


@then(parsers.parse('"{target}" is reported as measured by no run'))
def _unmeasured_reported(world: dict[str, Any], target: str) -> None:
    findings = world["payload"]["findings"]
    assert any(
        f["check"] == "mutation-target-unmeasured" and f["target"] == target
        for f in findings
    )


@then("the missing counter is reported")
def _missing_counter_reported(world: dict[str, Any]) -> None:
    assert "mutation-counters-missing" in _checks(world)
    assert any("killed" in f["why"] for f in world["payload"]["findings"])


@then(parsers.parse('"{target}" is named as not judged by this run'))
def _named_as_not_judged(world: dict[str, Any], target: str) -> None:
    assert target in world["payload"]["not_judged"]


@then(parsers.parse('nothing is reported about "{target}"'))
def _nothing_reported_about(world: dict[str, Any], target: str) -> None:
    assert not [f for f in world["payload"]["findings"] if f["target"] == target]


def _checks(world: dict[str, Any]) -> list[str]:
    return [f["check"] for f in world["payload"]["findings"]]


# --- BDL-068 S3.3: the populations that were empty and read as clean -------


@given(
    parsers.parse(
        'a project declaring the mutation target "{target}" whose code is not '
        "on disk"
    )
)
def _a_project_whose_target_moved(world: dict[str, Any], target: str) -> None:
    root = world["root"]
    (root / ".beadloom").mkdir(parents=True, exist_ok=True)
    (root / ".beadloom" / "config.yml").write_text(
        "languages:\n- .py\nscan_paths:\n- src\n", encoding="utf-8"
    )
    (root / ".beadloom" / "flow.yml").write_text(
        f"mutation:\n  targets:\n  - {target}\n", encoding="utf-8"
    )


@given(
    parsers.parse(
        'a run over "{covered}" that produced 10 mutants and classified none of '
        "them"
    )
)
def _a_run_that_classified_none(world: dict[str, Any], covered: str) -> None:
    _record_run(world, covered, killed=0, survived=0, skipped=10, total=10)


@then(parsers.parse('"{target}" is reported as unable to produce a mutant'))
def _target_cannot_produce_a_mutant(world: dict[str, Any], target: str) -> None:
    assert any(
        f["target"] == target and f["check"] == "mutation-target-missing"
        for f in world["payload"]["findings"]
    )


@then("the report is not clean")
def _the_report_is_not_clean(world: dict[str, Any]) -> None:
    assert world["result"].exit_code == 1


@then("the run is reported as having classified none of its mutants")
def _classified_none_reported(world: dict[str, Any]) -> None:
    assert "mutation-run-zero-mutants" in _checks(world)
    assert any(
        "reached a verdict on none of them" in f["why"]
        for f in world["payload"]["findings"]
    )
