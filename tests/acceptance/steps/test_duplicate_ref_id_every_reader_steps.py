"""Step implementations for `features/duplicate_ref_id_every_reader.feature`.

BDL-069 acceptance (`beadloom-956f`). `beadloom-39ap` put the duplicate report
into the two readers that reduce a graph file to one node per `ref_id`. The PRD's
criterion is stated over the whole directory, so what this module checks is the
*population*: every reader is asked, and each one either names what it dropped or
is a reader that drops nothing.

**The population is written here and BOUND to the derived one elsewhere.**
`beadloom-4ad3` classified the seven readers by experiment, and
`tests/test_what_each_reader_of_the_graph_directory_reads_for.py` holds that
classification. This module cannot import it: the acceptance suite is copied out
of the repository and run standalone by `tests/test_bead14_s4_binding.py`, and in
that copy the `tests` package is not importable, so the import would turn a
sabotage of somebody else's step into a collection failure of this one. What
keeps the two lists equal is `tests/test_the_acceptance_asks_every_graph_reader.py`,
which fails by name on a reader present in one and absent in the other — so an
eighth reader added to the derivation reddens this scenario's population rather
than being quietly left out of it.

The probes are this module's own rather than `THE_READERS[i].ask`, which renders
each reader's answer to a DIFFERENT question: `compute_diff`'s renders its node
changes and not its `duplicates`, and "its whole answer" is what this scenario is
about.

The fixture is `ledger` / `src/ledger/`, a project this repository cannot be
mistaken for: `src/beadloom/` holds seven packages and none is named `beadloom`,
so the collision cannot arise here and a fix recognising our own tree would fail.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import pytest
import yaml
from click.testing import CliRunner
from pytest_bdd import given, scenarios, then, when

from beadloom.application.reindex.change_detection import _scan_project_files
from beadloom.application.reindex.indexing import read_declared_docs
from beadloom.graph.diff import compute_diff
from beadloom.graph.loader import load_graph, update_node_in_yaml
from beadloom.infrastructure.db import create_schema, open_db
from beadloom.services.cli import main
from beadloom.services.commands.setup import _graph_files_now

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Callable
    from pathlib import Path

scenarios("../features/duplicate_ref_id_every_reader.feature")

#: The colliding ref_id, and the graph file that carries it twice.
REF_ID = "ledger"
GRAPH_FILE = "services.yml"

#: The two nodes, in the order BDL-UX #214 measured: the empty `service` root
#: first, then the `domain` that carries the code. First-wins keeps the root, so
#: the node that is lost is the one holding the adopter's source.
ROOT_NODE: dict[str, object] = {
    "ref_id": REF_ID,
    "kind": "service",
    "summary": "root",
    "source": "",
    "docs": ["root.md"],
}
PACKAGE_NODE: dict[str, object] = {
    "ref_id": REF_ID,
    "kind": "domain",
    "summary": "the package",
    "source": f"src/{REF_ID}/",
    "docs": ["package.md"],
}

#: What a reducing reader has to name: both nodes, told apart, and the file.
#: The source is the discriminator that matters — it is what the dropped node
#: owned, and a report naming only the ref_id names neither node.
MUST_NAME = ("service", "domain", f"src/{REF_ID}/", GRAPH_FILE)


@dataclass(frozen=True)
class _Answer:
    """One reader's whole answer over the duplicate-carrying directory."""

    #: The answer rendered as text, so a report can quote what the reader said.
    text: str
    #: Whether the answer distinguishes fewer nodes than the file carries.
    reduced: bool
    #: Why a non-reducing reader has nothing to drop. Empty when it reduces.
    reason: str


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)  # noqa: S603, S607


def _project(tmp_path: Path) -> Path:
    """A git repository that is not this one, whose graph file carries one ref_id twice.

    The graph is committed EMPTY and then written, because `compute_diff` reads
    the previous side at a git ref and has no answer without one.
    """
    root = tmp_path / REF_ID
    graph_dir = root / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True)
    (root / "src" / REF_ID).mkdir(parents=True)
    (root / "src" / REF_ID / "__init__.py").write_text('"""x."""\n', encoding="utf-8")
    (root / "docs").mkdir()
    for name in ("root.md", "package.md"):
        (root / "docs" / name).write_text(f"# {name}\n", encoding="utf-8")
    (graph_dir / GRAPH_FILE).write_text("nodes: []\n", encoding="utf-8")
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "config", "user.name", "Test")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "an empty graph")
    (graph_dir / GRAPH_FILE).write_text(
        yaml.safe_dump({"nodes": [ROOT_NODE, PACKAGE_NODE]}, sort_keys=False), encoding="utf-8"
    )
    return root


def _conn(root: Path) -> sqlite3.Connection:
    conn = open_db(root / ".beadloom" / "probe.db")
    create_schema(conn)
    return conn


def _nodes_on_disk(root: Path) -> list[dict[str, Any]]:
    text = (root / ".beadloom" / "_graph" / GRAPH_FILE).read_text(encoding="utf-8")
    return list(yaml.safe_load(text)["nodes"])


def _ask_load_graph(root: Path) -> _Answer:
    conn = _conn(root)
    try:
        result = load_graph(root / ".beadloom" / "_graph", conn)
        kept = sorted(str(row[0]) for row in conn.execute("SELECT ref_id FROM nodes"))
    finally:
        conn.close()
    text = repr((result.nodes_loaded, kept, result.errors))
    return _Answer(text, reduced=result.nodes_loaded < len(_nodes_on_disk(root)), reason="")


def _ask_compute_diff(root: Path) -> _Answer:
    diff = compute_diff(root, since="HEAD")
    changes = sorted(f"{change.change_type}:{change.ref_id}" for change in diff.nodes)
    described = [duplicate.describe() for duplicate in diff.duplicates]
    return _Answer(repr((changes, described)), reduced=bool(described), reason="")


def _ask_update_node_in_yaml(root: Path) -> _Answer:
    conn = _conn(root)
    try:
        update_node_in_yaml(root / ".beadloom" / "_graph", conn, REF_ID, summary="probed")
    finally:
        conn.close()
    after = _nodes_on_disk(root)
    return _Answer(
        repr(after),
        reduced=len(after) < 2,
        reason="answers about one ref_id rather than about a set, so it drops no node",
    )


def _ask_link(root: Path) -> _Answer:
    result = CliRunner().invoke(
        main, ["link", REF_ID, "https://example.invalid/1", "--project", str(root)]
    )
    after = _nodes_on_disk(root)
    return _Answer(
        repr((result.exit_code, after)),
        reduced=len(after) < 2,
        reason="answers about one ref_id rather than about a set, so it drops no node",
    )


def _ask_read_declared_docs(root: Path) -> _Answer:
    docs = read_declared_docs(root / ".beadloom" / "_graph", root, root / "docs")
    declared = sum(len(node["docs"]) for node in _nodes_on_disk(root))  # type: ignore[arg-type]
    return _Answer(
        repr(docs),
        reduced=len(docs) < declared,
        reason="keyed by document and not by ref_id, so both nodes' documents come back",
    )


def _ask_scan_project_files(root: Path) -> _Answer:
    scanned = _scan_project_files(root, root / "docs")
    graph = sorted((rel, h) for rel, (h, kind) in scanned.items() if kind == "graph")
    return _Answer(
        repr(graph),
        reduced=False,
        reason="reads bytes, and a file that will not parse into nodes still has bytes",
    )


def _ask_graph_files_now(root: Path) -> _Answer:
    return _Answer(
        repr(sorted(_graph_files_now(root).items())),
        reduced=False,
        reason="reads bytes, and a file that will not parse into nodes still has bytes",
    )


#: One probe per reader, by the name a traceback spells. The KEYS are checked
#: against the derived population, so a reader added there and not here fails by
#: name rather than by being quietly left out.
PROBES: dict[str, Callable[[Path], _Answer]] = {
    "load_graph": _ask_load_graph,
    "compute_diff": _ask_compute_diff,
    "update_node_in_yaml": _ask_update_node_in_yaml,
    "link": _ask_link,
    "read_declared_docs": _ask_read_declared_docs,
    "_scan_project_files": _ask_scan_project_files,
    "_graph_files_now": _ask_graph_files_now,
}


def _declared_population() -> tuple[str, ...]:
    """The readers this scenario asks, in the order `beadloom-4ad3` measured them."""
    return tuple(PROBES)


@pytest.fixture()
def world() -> dict[str, Any]:
    return {}


@given("a project that is not this one, whose graph file carries one ref_id twice")
def _given_a_duplicate(world: dict[str, Any], tmp_path: Path) -> None:
    world["population"] = _declared_population()
    world["projects"] = {name: _project(tmp_path / name) for name in world["population"]}


@when("every reader of the graph directory is asked for its whole answer")
def _when_every_reader_is_asked(world: dict[str, Any]) -> None:
    """Each reader gets its OWN copy of the project: two of them write to the file."""
    world["answers"] = {
        name: PROBES[name](world["projects"][name]) for name in world["population"]
    }


@then("the readers that reduce the file to one node name both nodes and the file")
def _then_a_reducer_names_both(world: dict[str, Any]) -> None:
    answers: dict[str, _Answer] = world["answers"]
    reducers = {name: answer for name, answer in answers.items() if answer.reduced}
    # Anti-vacuity, and the shape of the defect: before `beadloom-39ap` both
    # reducers reduced and neither named anything. A run in which nothing reduces
    # would satisfy every claim below by having no subject.
    assert len(reducers) >= 2, f"fewer than two readers reduced, so nothing was checked: {answers}"
    for name, answer in reducers.items():
        unnamed = [token for token in MUST_NAME if token not in answer.text]
        assert not unnamed, (name, unnamed, answer.text)


@then("no reader hands back a reduced answer without naming what it dropped")
def _then_no_silent_reduction(world: dict[str, Any]) -> None:
    answers: dict[str, _Answer] = world["answers"]
    silent = {
        name: answer.text
        for name, answer in answers.items()
        if answer.reduced and str(PACKAGE_NODE["source"]) not in answer.text
    }
    assert not silent, silent


@then("each reader outside that population is named with the reason it drops nothing")
def _then_the_rest_state_their_reason(world: dict[str, Any]) -> None:
    answers: dict[str, _Answer] = world["answers"]
    quiet = {name: answer for name, answer in answers.items() if not answer.reduced}
    assert quiet, "every reader reduced, so this claim has no subject"
    for name, answer in quiet.items():
        assert answer.reason, f"{name} drops nothing and says nothing about why"
        # The reason has to be true of the answer: a reader claiming it keeps
        # both nodes has to have returned something about both.
        assert answer.text, (name, answer.reason)


@then("the population asked is the whole declared population of readers")
def _then_the_population_is_whole(world: dict[str, Any]) -> None:
    """An eighth reader of `.beadloom/_graph/` fails here, by name."""
    declared = set(world["population"])
    asked = set(world["answers"])
    assert asked == declared, {"asked but not declared": asked - declared,
                               "declared but not asked": declared - asked}
    assert set(PROBES) == declared, {"probed but not declared": set(PROBES) - declared,
                                     "declared but not probed": declared - set(PROBES)}
