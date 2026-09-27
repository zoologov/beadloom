"""Every reader of the graph directory, and what each one reads it for.

The population was derived by experiment in ``beadloom-4ad3``; the tests that
hold it are ``tests/test_what_each_reader_of_the_graph_directory_reads_for.py``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from click.testing import CliRunner

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

#: The ref_ids the two mutating readers are probed with: both real nodes and one
#: that is in no graph, so "found everything" and "found anything" differ.
PROBE_REFS = ("orders", "ledger", "not-a-node")


def _conn(root: Path) -> sqlite3.Connection:
    db_path = root / ".beadloom" / "probe.db"
    conn = open_db(db_path)
    create_schema(conn)
    return conn


def _asked_of_update_node_in_yaml(root: Path) -> str:
    """Which ref_ids the writer found, read off the tree it wrote.

    It answers `True`/`False` per ref_id rather than about the directory, so it
    is asked once per probe ref and the answer is the set it accepted.
    """
    graph_dir = root / ".beadloom" / "_graph"
    conn = _conn(root)
    try:
        found = [
            ref
            for ref in PROBE_REFS
            if update_node_in_yaml(graph_dir, conn, ref, summary="probed")
        ]
    finally:
        conn.close()
    return repr(found)


def _asked_of_load_graph(root: Path) -> str:
    conn = _conn(root)
    try:
        result = load_graph(root / ".beadloom" / "_graph", conn)
        loaded = sorted(str(row[0]) for row in conn.execute("SELECT ref_id FROM nodes"))
    finally:
        conn.close()
    return repr((result.nodes_loaded, loaded, result.errors))


def _asked_of_compute_diff(root: Path) -> str:
    diff = compute_diff(root, since="HEAD")
    return repr(sorted(f"{change.change_type}:{change.ref_id}" for change in diff.nodes))


def _asked_of_scan_project_files(root: Path) -> str:
    scanned = _scan_project_files(root, root / "docs")
    return repr(sorted((rel, h) for rel, (h, kind) in scanned.items() if kind == "graph"))


def _asked_of_read_declared_docs(root: Path) -> str:
    return repr(read_declared_docs(root / ".beadloom" / "_graph", root, root / "docs"))


def _asked_of_link(root: Path) -> str:
    """Which ref_ids `beadloom link` found, by whether it exited 0 for each."""
    runner = CliRunner()
    found = [
        ref
        for ref in PROBE_REFS
        if runner.invoke(
            main, ["link", ref, "https://example.invalid/1", "--project", str(root)]
        ).exit_code
        == 0
    ]
    return repr(found)


def _asked_of_graph_files_now(root: Path) -> str:
    return repr(sorted(_graph_files_now(root).items()))


@dataclass(frozen=True)
class AReaderOfTheGraphDirectory:
    """One body that walks `.beadloom/_graph/`, and what this table claims of it.

    *reads_for* is the CLAIM; the experiments below are what check it. *routed*
    says whether the body goes through `each_graph_file`, and it is derived from
    the source rather than trusted, so a body that stops routing fails here.
    """

    #: The body, as a traceback spells it.
    name: str
    #: Where the epic's grep found it, so its list and this table are comparable.
    where: str
    #: The reader's whole answer over a project root, rendered as text.
    ask: Callable[[Path], str]
    #: `nodes` or `bytes` — checked by `TestWhatEachReaderReadsFor`.
    reads_for: str
    #: Whether it calls `each_graph_file`. Node readers that do not must name the
    #: policy in their own docstring with the reason.
    routed: bool


THE_READERS: tuple[AReaderOfTheGraphDirectory, ...] = (
    AReaderOfTheGraphDirectory(
        name="update_node_in_yaml",
        where="src/beadloom/graph/loader.py",
        ask=_asked_of_update_node_in_yaml,
        reads_for="nodes",
        routed=False,
    ),
    AReaderOfTheGraphDirectory(
        name="load_graph",
        where="src/beadloom/graph/loader.py",
        ask=_asked_of_load_graph,
        reads_for="nodes",
        routed=False,
    ),
    AReaderOfTheGraphDirectory(
        name="compute_diff",
        where="src/beadloom/graph/diff.py",
        ask=_asked_of_compute_diff,
        reads_for="nodes",
        routed=False,
    ),
    AReaderOfTheGraphDirectory(
        name="_scan_project_files",
        where="src/beadloom/application/reindex/change_detection.py",
        ask=_asked_of_scan_project_files,
        reads_for="bytes",
        routed=False,
    ),
    AReaderOfTheGraphDirectory(
        name="read_declared_docs",
        where="src/beadloom/application/reindex/indexing.py",
        ask=_asked_of_read_declared_docs,
        reads_for="nodes",
        routed=True,
    ),
    AReaderOfTheGraphDirectory(
        name="link",
        where="src/beadloom/services/commands/index_ops.py",
        ask=_asked_of_link,
        reads_for="nodes",
        routed=True,
    ),
    AReaderOfTheGraphDirectory(
        name="_graph_files_now",
        where="src/beadloom/services/commands/setup.py",
        ask=_asked_of_graph_files_now,
        reads_for="bytes",
        routed=False,
    ),
)


NODE_READERS = tuple(r for r in THE_READERS if r.reads_for == "nodes")


BYTE_READERS = tuple(r for r in THE_READERS if r.reads_for == "bytes")
