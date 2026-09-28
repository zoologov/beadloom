"""Step implementations for `features/test_files_bind_to_the_node_their_path_mirrors.feature`.

BDL-074 C1, `beadloom-5qgt`. Every step runs the real commands — `reindex` and
`ctx --json` through the CLI — against a project written into a temporary
directory, so the tests compared are the ones `ctx` hands a reader, read from the
index the rebuild wrote rather than from one written by hand.

**The expected files are written down here, not derived.** A list checked against
what the index returns would agree with any binding, including the guess this bead
retires, so each step records the files it laid out and the assertions read that.

**The rebuild runs twice, full and then incremental.** A binding that the full
rebuild writes and the incremental one loses — the fate of a `tests:` key the old
reindex overwrote — would pass a scenario that rebuilt once.

The project is built here rather than imported from `tests.support.adopter_project`, for
the reason `test_bootstrap_self_consistency_steps` records: the acceptance suite is
copied out of the repository and run standalone, where the `tests` package is not
importable.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

import pytest
import yaml
from click.testing import CliRunner
from pytest_bdd import given, scenarios, then, when

from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../features/test_files_bind_to_the_node_their_path_mirrors.feature")

#: The two nodes: a package, and one module inside it that has a node of its own.
PACKAGE_NODE = "ledger"
MODULE_NODE = "posting"

#: The code of the project, by path under its root.
CODE: dict[str, str] = {
    "src/ledger/__init__.py": '"""The ledger."""\n',
    "src/ledger/posting.py": "def post() -> None:\n    pass\n",
    "src/ledger/balance.py": "def balance() -> int:\n    return 0\n",
}

#: Test files, each with the number of test functions it defines.
POSTING_TEST = "tests/unit/ledger/test_posting.py"
BALANCE_TEST = "tests/unit/ledger/test_balance.py"
FLAT_TEST = "tests/test_posting_rules.py"
MUTANT_COPY = "mutants/tests/unit/ledger/test_posting.py"

_TWO_TESTS = "def test_posts() -> None:\n    pass\n\n\ndef test_reverses() -> None:\n    pass\n"
_ONE_TEST = "def test_balances() -> None:\n    pass\n"


@pytest.fixture()
def world() -> dict[str, Any]:
    return {"laid_out": {}}


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _graph(declared_tests: list[str] | None) -> dict[str, Any]:
    posting: dict[str, Any] = {
        "ref_id": MODULE_NODE,
        "kind": "feature",
        "summary": "Posting",
        "source": "src/ledger/posting.py",
    }
    if declared_tests is not None:
        posting["tests"] = declared_tests
    return {
        "nodes": [
            {
                "ref_id": PACKAGE_NODE,
                "kind": "domain",
                "summary": "Ledger",
                "source": "src/ledger/",
            },
            posting,
        ],
        "edges": [{"src": MODULE_NODE, "dst": PACKAGE_NODE, "kind": "part_of"}],
    }


def _write_graph(project: Path, declared_tests: list[str] | None) -> None:
    graph = project / ".beadloom" / "_graph" / "ledger.yml"
    graph.parent.mkdir(parents=True, exist_ok=True)
    graph.write_text(yaml.safe_dump(_graph(declared_tests), sort_keys=False), encoding="utf-8")


def _cli(project: Path, *args: str) -> str:
    result = CliRunner().invoke(main, [*args, "--project", str(project)])
    assert result.exit_code == 0, result.output
    return result.output


def _lay_out(world: dict[str, Any], relative: str, text: str, count: int) -> None:
    _write(world["project"], relative, text)
    world["laid_out"][relative] = count


@given("a project whose ledger package holds a posting module owned by its own node")
def _given_a_project(world: dict[str, Any], tmp_path: Path) -> None:
    project = tmp_path / "ledger-project"
    for relative, text in CODE.items():
        _write(project, relative, text)
    _write(project, ".beadloom/config.yml", "languages:\n- .py\nscan_paths:\n- src\n")
    _write_graph(project, declared_tests=None)
    world["project"] = project


@given("a unit test laid out under the mirror of the posting module")
def _given_a_posting_test(world: dict[str, Any]) -> None:
    _lay_out(world, POSTING_TEST, _TWO_TESTS, 2)


@given("a unit test laid out under the mirror of a ledger module no child node owns")
def _given_a_balance_test(world: dict[str, Any]) -> None:
    _lay_out(world, BALANCE_TEST, _ONE_TEST, 1)


@given(
    "a test file at the top of the tests folder that the posting node declares in its tests list"
)
def _given_a_declared_flat_test(world: dict[str, Any]) -> None:
    _lay_out(world, FLAT_TEST, _TWO_TESTS, 2)
    _write_graph(world["project"], declared_tests=[FLAT_TEST])


@given("a test file at the top of the tests folder that no node declares")
def _given_an_undeclared_flat_test(world: dict[str, Any]) -> None:
    _lay_out(world, FLAT_TEST, _TWO_TESTS, 2)


@given("a mutation-testing copy of that unit test under the mutants folder")
def _given_a_mutant_copy(world: dict[str, Any]) -> None:
    # Written, and NOT recorded as laid out: it is the file no node may be given.
    _write(world["project"], MUTANT_COPY, _TWO_TESTS)


def _rebuild(world: dict[str, Any]) -> None:
    project = world["project"]
    _cli(project, "reindex", "--full")
    world["reindex_output"] = _cli(project, "reindex")


def _read_tests(world: dict[str, Any], ref_id: str) -> None:
    bundle = json.loads(_cli(world["project"], "ctx", ref_id, "--json"))
    world["tests"] = bundle["tests"]


@when("the index is rebuilt and the context of the posting node is read")
def _when_rebuilt_posting(world: dict[str, Any]) -> None:
    _rebuild(world)
    _read_tests(world, MODULE_NODE)


@when("the index is rebuilt and the context of the ledger node is read")
def _when_rebuilt_ledger(world: dict[str, Any]) -> None:
    _rebuild(world)
    _read_tests(world, PACKAGE_NODE)


@when("the index is rebuilt")
def _when_rebuilt(world: dict[str, Any]) -> None:
    _rebuild(world)


def _assert_names(world: dict[str, Any], expected: list[str]) -> None:
    tests = world["tests"]
    assert set(tests) == {"framework", "test_files", "test_count", "coverage_estimate"}, tests
    assert tests["test_files"] == sorted(expected), tests
    assert tests["test_count"] == sum(world["laid_out"][path] for path in expected), tests


@then("the tests it names are that unit test and no other")
def _then_the_posting_test(world: dict[str, Any]) -> None:
    _assert_names(world, [POSTING_TEST])


@then("the tests it names are both unit tests, each counted once")
def _then_both_tests(world: dict[str, Any]) -> None:
    _assert_names(world, [POSTING_TEST, BALANCE_TEST])


@then("the tests it names are the declared test file and no other")
def _then_the_declared_test(world: dict[str, Any]) -> None:
    _assert_names(world, [FLAT_TEST])


@then("the rebuild reports one unplaced test file")
def _then_one_unplaced(world: dict[str, Any]) -> None:
    line = next((ln for ln in world["reindex_output"].splitlines() if ln.startswith("Tests:")), "")
    assert re.search(r"\b1 unplaced\b", line), world["reindex_output"]


@then("the context of the posting node names no test")
def _then_no_test(world: dict[str, Any]) -> None:
    _read_tests(world, MODULE_NODE)
    _assert_names(world, [])
