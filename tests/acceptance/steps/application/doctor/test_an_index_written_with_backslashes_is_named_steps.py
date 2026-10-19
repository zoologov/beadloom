"""Steps of `application/doctor/an_index_written_with_backslashes_is_named.feature`.

BDL-083 S2f (``beadloom-27br``), RFC D11. The monorepo fixture is indexed by the real
``reindex``, and then its path columns are rewritten with backslashes in place: that is the
index an older version built on a Windows checkout, which this platform cannot otherwise
produce. ``doctor`` and ``reindex --full`` run through the CLI.
"""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING, Any

import pytest
from click.testing import CliRunner
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.services.cli import main
from tests.support.monorepo_fixture import monorepo_checkout

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../../../application/doctor/an_index_written_with_backslashes_is_named.feature")

#: The two columns an older Windows index spelled with a backslash and a match reads.
_REWRITTEN = (("file_index", "path"), ("code_symbols", "file_path"))

#: The words every line of the check carries, which the scenario looks for.
_CHECK_WORDS = "backslash"


@pytest.fixture
def state() -> dict[str, Any]:
    return {}


@given("the monorepo fixture indexed")
def _indexed(tmp_path: Path, state: dict[str, Any]) -> None:
    root = monorepo_checkout(tmp_path)
    result = CliRunner().invoke(main, ["reindex", "--project", str(root)])
    assert result.exit_code == 0, result.output
    state["root"] = root


@given("its index rewritten with backslashes, as an older version wrote it on Windows")
def _rewritten(state: dict[str, Any]) -> None:
    with sqlite3.connect(state["root"] / ".beadloom" / "beadloom.db") as conn:
        for table, column in _REWRITTEN:
            conn.execute(
                f"UPDATE {table} SET {column} = replace({column}, '/', '\\')"  # noqa: S608
            )
        held = conn.execute(
            "SELECT COUNT(*) FROM file_index WHERE instr(path, '\\') > 0"
        ).fetchone()[0]
    assert held, "the rewritten index holds backslash paths"


@when("the index is rebuilt with a full reindex")
def _full(state: dict[str, Any]) -> None:
    result = CliRunner().invoke(main, ["reindex", "--full", "--project", str(state["root"])])
    assert result.exit_code == 0, result.output


@when("doctor runs")
def _doctor(state: dict[str, Any]) -> None:
    result = CliRunner().invoke(main, ["doctor", "--project", str(state["root"])])
    state["output"] = result.output


@then(parsers.parse('doctor warns that the index holds backslash paths and names "{command}"'))
def _warned(state: dict[str, Any], command: str) -> None:
    lines = [line for line in state["output"].splitlines() if _CHECK_WORDS in line]

    assert lines, state["output"]
    assert all(line.lstrip().startswith("[warn]") for line in lines), lines
    assert any(command in line for line in lines), lines


@then("doctor says nothing about backslash paths")
def _silent(state: dict[str, Any]) -> None:
    assert _CHECK_WORDS not in state["output"], state["output"]
