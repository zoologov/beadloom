"""Step implementations for `features/mutation_runs_on_a_change_or_on_a_sample.feature`.

BDL-074 D1, `beadloom-vr0b`. Every step runs the real commands — `reindex` and
`mutation` through the CLI — against a project written into a temporary directory
and committed to a git repository there, so the change a step makes is a real diff
against a real merge base.

The project is built here rather than imported from another step module or from
`tests.support`: the acceptance suite is copied out of the repository and run
standalone, where the `tests` package is not importable.
"""

from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING, Any

import pytest
import yaml
from click.testing import CliRunner
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../features/mutation_runs_on_a_change_or_on_a_sample.feature")

PACKAGE_NODE = "ledger"
MODULE_NODE = "posting"
POSTING = "src/ledger/posting.py"

CODE: dict[str, str] = {
    "src/ledger/__init__.py": '"""The ledger."""\n',
    POSTING: (
        "def post(amount: int) -> int:\n    return amount\n\n\n"
        "def reverse(amount: int) -> int:\n    return -amount\n"
    ),
    "README.md": "# Ledger\n",
}

POSTING_TEST = "tests/unit/ledger/test_posting.py"
FLAT_TEST = "tests/test_posting_rules.py"
_ONE_TEST = "def test_posts() -> None:\n    pass\n"

GRAPH: dict[str, Any] = {
    "nodes": [
        {"ref_id": PACKAGE_NODE, "kind": "domain", "summary": "Ledger", "source": "src/ledger/"},
        {"ref_id": MODULE_NODE, "kind": "feature", "summary": "Posting", "source": POSTING},
    ],
    "edges": [{"src": MODULE_NODE, "dst": PACKAGE_NODE, "kind": "part_of"}],
}


@pytest.fixture()
def world() -> dict[str, Any]:
    return {}


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _git(project: Path, *args: str) -> None:
    subprocess.run(  # noqa: S603 - a fixed git argv in a temporary repository
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],  # noqa: S607
        cwd=project,
        check=True,
        capture_output=True,
    )


def _cli(project: Path, *args: str, code: int = 0) -> str:
    result = CliRunner().invoke(main, [*args, "--project", str(project)])
    assert result.exit_code == code, result.output
    return result.output


@given("a ledger project whose package is the declared mutation scope, committed to git")
def _given_a_project(world: dict[str, Any], tmp_path: Path) -> None:
    project = tmp_path / "ledger-project"
    for relative, text in CODE.items():
        _write(project, relative, text)
    _write(project, ".beadloom/config.yml", "languages:\n- .py\nscan_paths:\n- src\n")
    _write(project, ".beadloom/flow.yml", "mutation:\n  targets:\n  - src/ledger/\n")
    _write(project, ".beadloom/_graph/ledger.yml", yaml.safe_dump(GRAPH, sort_keys=False))
    _git(project, "init", "-q", "-b", "main")
    _git(project, "add", "-A")
    _git(project, "commit", "-q", "-m", "the ledger")
    world["project"] = project


@given("a unit test laid out under the mirror of the posting module")
def _given_a_posting_test(world: dict[str, Any]) -> None:
    _write(world["project"], POSTING_TEST, _ONE_TEST)


@given("a test file at the top of the tests folder")
def _given_a_flat_test(world: dict[str, Any]) -> None:
    _write(world["project"], FLAT_TEST, _ONE_TEST)


def _print_change(world: dict[str, Any]) -> None:
    project = world["project"]
    _cli(project, "reindex", "--full")
    world["text"] = _cli(project, "mutation", "--changed-since", "HEAD")
    world["change"] = json.loads(_cli(project, "mutation", "--changed-since", "HEAD", "--json"))[
        "change"
    ]


@when("the post function is changed and the population of the change is printed")
def _when_post_changed(world: dict[str, Any]) -> None:
    text = CODE[POSTING].replace("return amount\n", "return amount + 0\n", 1)
    _write(world["project"], POSTING, text)
    _print_change(world)


@when("only the readme is changed and the population of the change is printed")
def _when_readme_changed(world: dict[str, Any]) -> None:
    _write(world["project"], "README.md", "# Ledger\n\nA second line.\n")
    _print_change(world)


@then("the population is the post function of the posting module, over the posting node")
def _then_post_population(world: dict[str, Any]) -> None:
    change = world["change"]
    assert change["functions"] == [{"path": POSTING, "name": "post", "node": MODULE_NODE}]
    assert "1 function(s) in 1 file(s)" in world["text"], world["text"]
    assert MODULE_NODE in world["text"]


@then("the posting node's bound test is the laid-out unit test")
def _then_bound_test(world: dict[str, Any]) -> None:
    nodes = world["change"]["nodes"]
    assert nodes == [{"node": MODULE_NODE, "functions": ["post"], "bound_tests": [POSTING_TEST]}]


@then("the population is stated as empty")
def _then_empty(world: dict[str, Any]) -> None:
    assert world["change"]["functions"] == []
    assert "Population: empty" in world["text"], world["text"]


@then(parsers.parse("the change says {unbound:d} of {total:d} test files is placed under no node"))
def _then_unbound(world: dict[str, Any], unbound: int, total: int) -> None:
    assert world["change"]["unbound_tests"] == [FLAT_TEST]
    assert f"{unbound} of {total} test file(s)" in world["text"], world["text"]


@when("a run over the posting module is reported with one surviving mutant of the post function")
def _when_survivor_reported(world: dict[str, Any]) -> None:
    project = world["project"]
    _cli(project, "reindex", "--full")
    stats = project / "stats.json"
    stats.write_text(json.dumps({"killed": 3, "survived": 1, "total": 4}), encoding="utf-8")
    survivors = project / "survivors.json"
    survivors.write_text(
        json.dumps([{"path": POSTING, "mutant": "ledger.posting.x_post__mutmut_2"}]),
        encoding="utf-8",
    )
    args = ["mutation", "--stats", str(stats), "--target", "src/ledger/"]
    world["text"] = _cli(project, *args, "--survivors", str(survivors))
    world["payload"] = json.loads(_cli(project, *args, "--survivors", str(survivors), "--json"))


@then(parsers.parse("the report lists {count:d} survivor under the posting node"))
def _then_survivor_by_node(world: dict[str, Any], count: int) -> None:
    by_node = world["payload"]["survivors_by_node"]
    assert list(by_node) == [MODULE_NODE]
    assert len(by_node[MODULE_NODE]) == count
    assert f"{MODULE_NODE}: {count} survivor(s)" in world["text"], world["text"]


@when(
    parsers.parse(
        "a sample of {size:d} mutants out of {population:d} is reported with "
        "{killed:d} killed and {survived:d} survived"
    )
)
def _when_sample_reported(
    world: dict[str, Any], size: int, population: int, killed: int, survived: int
) -> None:
    project = world["project"]
    stats = project / "stats.json"
    counters = {"killed": killed, "survived": survived, "total": size}
    stats.write_text(json.dumps(counters), encoding="utf-8")
    args = ["mutation", "--stats", str(stats), "--target", "src/ledger/"]
    world["text"] = _cli(project, *args, "--sample-of", str(population))


@then(parsers.parse("the score reads {score} with a 95% interval from {low} to {high}"))
def _then_interval(world: dict[str, Any], score: str, low: str, high: str) -> None:
    assert f"Score: {score}" in world["text"], world["text"]
    assert f"95% interval {low} to {high}" in world["text"], world["text"]


@then("the population is printed without a score it does not have")
def _then_no_score_line(world: dict[str, Any]) -> None:
    assert "Score:" not in world["text"], world["text"]
    assert "Not judged by this run" not in world["text"], world["text"]
    assert "a change covers functions, not declared targets" in world["text"], world["text"]
