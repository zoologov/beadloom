"""Step implementations for `features/duplicate_ref_id_report.feature`.

BDL-069 S2, the loader half of BDL-UX #214. Nothing here is stubbed: the real
`load_graph` and the real `compute_diff` run over a real directory in a real git
repository, because the subject is what those two readers do with a file that
carries one `ref_id` twice, and a double would agree with whatever they do now.

**FAKES PROVE FAKES.** The fixture is `ledger` / `src/ledger/` — the ordinary
single-package src-layout, and a project this repository cannot be mistaken for:
`src/beadloom/` holds seven packages and none of them is named `beadloom`, so the
collision cannot arise here and a fix that recognised our own tree would fail
these scenarios.

The module is named `test_*` so default pytest collection picks the scenarios up.
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING, Any

import pytest
from pytest_bdd import given, scenarios, then, when

from beadloom.graph.diff import compute_diff
from beadloom.graph.loader import GraphLoadResult, load_graph
from beadloom.infrastructure.db import create_schema, open_db

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path

    from beadloom.graph.diff import GraphDiff

scenarios("../features/duplicate_ref_id_report.feature")

#: The project the collision is ordinary on: its only package is named after it.
PROJECT = "ledger"

#: The graph an earlier release wrote, or a hand edit left: the root service and
#: the package domain under one ref_id. The node carrying the source is second,
#: which is the shape #214 measured — first-wins keeps the empty root.
_SINGLE_NODE = """\
nodes:
  - ref_id: ledger
    kind: service
    summary: The ledger service.
    source: ""
edges: []
"""

_DUPLICATE_NODE = """\
nodes:
  - ref_id: ledger
    kind: service
    summary: The ledger service.
    source: ""
  - ref_id: ledger
    kind: domain
    summary: The ledger package.
    source: src/ledger/
edges: []
"""


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)  # noqa: S603, S607


def _commit_all(root: Path, message: str) -> None:
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", message)


def _loaded(graph_dir: Path, tmp_path: Path) -> tuple[GraphLoadResult, sqlite3.Connection]:
    conn = open_db(tmp_path / "load.db")
    create_schema(conn)
    return load_graph(graph_dir, conn), conn


@pytest.fixture
def state() -> dict[str, Any]:
    """What the steps hand each other: the project, and each reader's answer."""
    return {}


@given(
    "a graph file that carries one ref_id twice, "
    "where only the dropped node declares a source"
)
def _a_duplicate_graph(state: dict[str, Any], tmp_path: Path) -> None:
    root = tmp_path / PROJECT
    (root / "src" / PROJECT).mkdir(parents=True)
    (root / "src" / PROJECT / "__init__.py").write_text('"""ledger."""\n', encoding="utf-8")
    (root / "pyproject.toml").write_text(
        f'[project]\nname = "{PROJECT}"\nversion = "0.1.0"\n', encoding="utf-8"
    )
    graph_dir = root / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True)

    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "config", "user.name", "Test")
    # The commit BEFORE the duplicate: one node, so a diff against it has a
    # side that is unambiguous and a side that is not.
    (graph_dir / "services.yml").write_text(_SINGLE_NODE, encoding="utf-8")
    _commit_all(root, "the graph before the duplicate")
    (graph_dir / "services.yml").write_text(_DUPLICATE_NODE, encoding="utf-8")

    state["root"] = root
    state["graph_dir"] = graph_dir


@when("the graph is loaded")
def _load_it(state: dict[str, Any], tmp_path: Path) -> None:
    result, conn = _loaded(state["graph_dir"], tmp_path)
    state["result"] = result
    state["nodes"] = [
        (row["ref_id"], row["kind"], row["source"])
        for row in conn.execute("SELECT ref_id, kind, source FROM nodes").fetchall()
    ]
    conn.close()


@when("the graph diff reads that graph against the commit before the duplicate")
def _diff_it(state: dict[str, Any], tmp_path: Path) -> None:
    state["diff"] = compute_diff(state["root"], "HEAD")
    result, conn = _loaded(state["graph_dir"], tmp_path)
    state["result"] = result
    conn.close()


@then("the report names the ref_id and the file, the kind and the source of both nodes")
def _report_names_both(state: dict[str, Any]) -> None:
    reported = "\n".join(state["result"].errors)
    assert PROJECT in reported
    assert "services.yml" in reported
    assert "service" in reported, reported
    assert "domain" in reported, reported
    assert "src/ledger/" in reported, reported


@then("the report says what the dropped node's source now owns")
def _report_names_the_consequence(state: dict[str, Any]) -> None:
    reported = "\n".join(state["result"].errors)
    assert "owned, checked or counted" in reported, reported
    assert "src/ledger/" in reported, reported


@then("graph-diff reports the same duplicate the loader reports")
def _diff_reports_it(state: dict[str, Any]) -> None:
    diff: GraphDiff = state["diff"]
    assert diff.duplicates, "graph-diff reported no duplicate"
    diff_refs = {d.ref_id for d in diff.duplicates}
    assert diff_refs == {PROJECT}
    reported = "\n".join(state["result"].errors)
    assert any(d.describe() in reported for d in diff.duplicates), (
        f"diff says {[d.describe() for d in diff.duplicates]}, loader says {reported}"
    )


@then("graph-diff and the loader name the same node as the one that was kept")
def _both_keep_one_node(state: dict[str, Any]) -> None:
    diff: GraphDiff = state["diff"]
    kept_by_diff = {d.kept for d in diff.duplicates}
    assert len(kept_by_diff) == 1
    kept = next(iter(kept_by_diff))
    assert kept.kind == "service"
    assert kept.source == ""
    # And the diff describes the graph the loader loads: the node it dropped is
    # not what a reader is told changed.
    changed_kinds = {n.kind for n in diff.nodes if n.ref_id == PROJECT}
    assert changed_kinds <= {"service"}, changed_kinds


@then("the load is not refused and every node it can keep is in the graph")
def _load_is_not_refused(state: dict[str, Any]) -> None:
    assert state["result"].nodes_loaded == 1
    assert state["nodes"] == [(PROJECT, "service", "")]


@then("a graph whose only anomaly is the duplicate reports no change against itself")
def _no_change_against_itself(state: dict[str, Any]) -> None:
    root: Path = state["root"]
    _commit_all(root, "the duplicate, committed")
    diff = compute_diff(root, "HEAD")
    assert diff.duplicates, "the committed duplicate went unreported"
    assert not diff.has_changes, [n for n in diff.nodes]
