"""Steps of `application/reindex/the_index_is_posix_on_every_platform.feature`.

BDL-083 S2f (``beadloom-27br``), RFC D11. Two checkouts of the monorepo fixture, each indexed
with ``reindex --full`` and read with ``sync-check --json`` through the CLI. The second runs
under :func:`~tests.support.windows_separator.spell_relative_paths_as_windows`, which makes a
relative path print with a backslash and leaves ``as_posix()`` answering with a forward slash,
as Windows does. Nothing else is patched: the reindex, the pairing and the reason a node gets
no pair are the real ones.
"""

from __future__ import annotations

import json
import sqlite3
from typing import TYPE_CHECKING, Any

import pytest
from click.testing import CliRunner
from pytest_bdd import given, scenarios, then, when

from beadloom.services.cli import main
from tests.support.monorepo_fixture import monorepo_checkout
from tests.support.windows_separator import spell_relative_paths_as_windows

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../../../application/reindex/the_index_is_posix_on_every_platform.feature")

#: Every column of the index that holds a project-relative or docs-relative path.
_PATH_COLUMNS = (
    ("file_index", "path"),
    ("code_symbols", "file_path"),
    ("code_imports", "file_path"),
    ("docs", "path"),
    ("sync_state", "doc_path"),
    ("sync_state", "code_path"),
)


@pytest.fixture
def state() -> dict[str, Any]:
    return {}


def _index_and_check(root: Path) -> dict[str, Any]:
    reindexed = CliRunner().invoke(main, ["reindex", "--full", "--project", str(root)])
    assert reindexed.exit_code == 0, reindexed.output
    checked = CliRunner().invoke(main, ["sync-check", "--json", "--project", str(root)])
    report: dict[str, Any] = json.loads(checked.output)
    return report


def _declared_pairs(report: dict[str, Any]) -> set[tuple[str, str]]:
    return {(p["doc_path"], p["code_path"]) for p in report["pairs"] if p["code_path"]}


@given("the monorepo fixture indexed and sync-checked on this platform")
def _first(tmp_path: Path, state: dict[str, Any]) -> None:
    state["first"] = _index_and_check(monorepo_checkout(tmp_path / "posix"))
    assert _declared_pairs(state["first"]), "the fixture declares pairs to compare"


@given("a second checkout of it on which a relative path prints with a backslash")
def _second(tmp_path: Path, state: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    state["root"] = monorepo_checkout(tmp_path / "windows")
    spell_relative_paths_as_windows(monkeypatch)
    probe = state["root"] / "backend" / "src"
    assert str(probe.relative_to(state["root"])) == "backend\\src", "the simulation is on"


@when("the second checkout is indexed and sync-checked")
def _index_second(state: dict[str, Any]) -> None:
    state["second"] = _index_and_check(state["root"])


@then("no path in the second checkout's index holds a backslash")
def _no_backslash(state: dict[str, Any]) -> None:
    with sqlite3.connect(state["root"] / ".beadloom" / "beadloom.db") as conn:
        spelled = {
            (table, column, str(value))
            for table, column in _PATH_COLUMNS
            for (value,) in conn.execute(f"SELECT {column} FROM {table}")  # noqa: S608
            if value is not None and "\\" in str(value)
        }
        held = conn.execute("SELECT COUNT(*) FROM file_index").fetchone()[0]

    assert held, "the index holds files to read"
    assert spelled == set()


@then("the second checkout's declared pairs are the first checkout's, pair for pair")
def _same_pairs(state: dict[str, Any]) -> None:
    assert _declared_pairs(state["second"]) == _declared_pairs(state["first"])


@then("no node of the second checkout reads no indexed code")
def _no_unindexed_node(state: dict[str, Any]) -> None:
    reasons = {(u["ref_id"], u["reason"]) for u in state["second"]["unchecked"]}
    first = {(u["ref_id"], u["reason"]) for u in state["first"]["unchecked"]}

    assert reasons == first
    assert not {ref for ref, reason in reasons if reason == "no_indexed_code"}
