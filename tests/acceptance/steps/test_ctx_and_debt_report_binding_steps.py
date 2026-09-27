"""Step implementations for `features/ctx_and_debt_report_read_the_test_binding.feature`.

BDL-074 C2, `beadloom-3z94`. Every step runs the real commands — `reindex`, `ctx`
and `status --debt-report --json` through the CLI — against a project written into
a temporary directory, so what is asserted is what a reader of those commands sees,
read from the index the rebuild wrote.

**The laid-out files are written down here, not derived.** A count checked against
what the index returns would agree with any binding, so each step records what it
laid out and the assertions read that.

The project is built here rather than imported from another step module or from
`tests.adopter_project`: the acceptance suite is copied out of the repository and
run standalone, where the `tests` package is not importable.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest
import yaml
from click.testing import CliRunner
from pytest_bdd import given, scenarios, then, when

from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../features/ctx_and_debt_report_read_the_test_binding.feature")

PACKAGE_NODE = "ledger"
MODULE_NODE = "posting"

CODE: dict[str, str] = {
    "src/ledger/__init__.py": '"""The ledger."""\n',
    "src/ledger/posting.py": "def post() -> None:\n    pass\n",
    "src/ledger/balance.py": "def balance() -> int:\n    return 0\n",
}

POSTING_TEST = "tests/unit/ledger/test_posting.py"
BALANCE_TEST = "tests/unit/ledger/test_balance.py"
FLAT_TEST = "tests/test_posting_rules.py"

_TWO_TESTS = "def test_posts() -> None:\n    pass\n\n\ndef test_reverses() -> None:\n    pass\n"

GRAPH: dict[str, Any] = {
    "nodes": [
        {"ref_id": PACKAGE_NODE, "kind": "domain", "summary": "Ledger", "source": "src/ledger/"},
        {
            "ref_id": MODULE_NODE,
            "kind": "feature",
            "summary": "Posting",
            "source": "src/ledger/posting.py",
        },
    ],
    "edges": [{"src": MODULE_NODE, "dst": PACKAGE_NODE, "kind": "part_of"}],
}


@pytest.fixture()
def world() -> dict[str, Any]:
    return {"laid_out": []}


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _cli(project: Path, *args: str) -> str:
    result = CliRunner().invoke(main, [*args, "--project", str(project)])
    assert result.exit_code == 0, result.output
    return result.output


@given("a project whose ledger package holds a posting module owned by its own node")
def _given_a_project(world: dict[str, Any], tmp_path: Path) -> None:
    project = tmp_path / "ledger-project"
    for relative, text in CODE.items():
        _write(project, relative, text)
    _write(project, ".beadloom/config.yml", "languages:\n- .py\nscan_paths:\n- src\n")
    _write(project, ".beadloom/_graph/ledger.yml", yaml.safe_dump(GRAPH, sort_keys=False))
    world["project"] = project


@given("a unit test laid out under the mirror of the posting module")
def _given_a_posting_test(world: dict[str, Any]) -> None:
    _write(world["project"], POSTING_TEST, _TWO_TESTS)
    world["laid_out"].append(POSTING_TEST)


@given("a unit test laid out under the mirror of a ledger module no child node owns")
def _given_a_balance_test(world: dict[str, Any]) -> None:
    _write(world["project"], BALANCE_TEST, _TWO_TESTS)
    world["laid_out"].append(BALANCE_TEST)


@given("a test file at the top of the tests folder")
def _given_a_flat_test(world: dict[str, Any]) -> None:
    # Written, and NOT recorded as laid out: it is the file no node may be given.
    _write(world["project"], FLAT_TEST, _TWO_TESTS)


def _rebuild(world: dict[str, Any]) -> None:
    _cli(world["project"], "reindex", "--full")


@when("the index is rebuilt and the context of the posting node is printed")
def _when_ctx_printed(world: dict[str, Any]) -> None:
    _rebuild(world)
    world["ctx"] = _cli(world["project"], "ctx", MODULE_NODE)


@when("the index is rebuilt and the debt report is read")
def _when_debt_read(world: dict[str, Any]) -> None:
    _rebuild(world)
    world["debt"] = json.loads(_cli(world["project"], "status", "--debt-report", "--json"))


def _tests_line(world: dict[str, Any]) -> str:
    lines = [line for line in world["ctx"].splitlines() if line.startswith("Tests:")]
    assert len(lines) == 1, world["ctx"]
    return lines[0]


@then("the Tests line names the one laid-out test file")
def _then_one_file(world: dict[str, Any]) -> None:
    assert world["laid_out"] == [POSTING_TEST]
    assert "2 tests in 1 files" in _tests_line(world), world["ctx"]


@then("the context says that 1 of 2 test files in the repository is unplaced")
def _then_ctx_names_unplaced(world: dict[str, Any]) -> None:
    unplaced = [line for line in world["ctx"].splitlines() if "unplaced" in line]
    assert len(unplaced) == 1, world["ctx"]
    assert "1 of 2 test file(s)" in unplaced[0], unplaced


@then("the context does not mention unplaced test files")
def _then_ctx_silent(world: dict[str, Any]) -> None:
    assert "unplaced" not in world["ctx"], world["ctx"]


def _untested(world: dict[str, Any]) -> int:
    test_gaps = [c for c in world["debt"]["categories"] if c["name"] == "test_gaps"]
    assert len(test_gaps) == 1, world["debt"]
    return int(test_gaps[0]["details"]["untested"])


@then("the debt report counts no node as untested")
def _then_none_untested(world: dict[str, Any]) -> None:
    assert _untested(world) == 0, world["debt"]
    for offender in world["debt"]["top_offenders"]:
        assert "untested" not in offender["reasons"], offender


@then("the debt report says the count was withheld because 1 of 1 test files is unplaced")
def _then_withheld(world: dict[str, Any]) -> None:
    population = world["debt"]["test_population"]
    assert population.startswith("not counted:"), population
    assert "1 of 1 test file(s)" in population, population


@then("the debt report counts the posting node as untested and the ledger node as tested")
def _then_posting_untested(world: dict[str, Any]) -> None:
    assert _untested(world) == 1, world["debt"]
    reasons = {o["ref_id"]: o["reasons"] for o in world["debt"]["top_offenders"]}
    assert "untested" in reasons[MODULE_NODE], reasons
    assert "untested" not in reasons.get(PACKAGE_NODE, []), reasons
    assert world["debt"]["test_population"].startswith("counted over"), world["debt"]
