"""Each graph-directory reader, asked about a graph file that carries one ref_id twice."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import yaml
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

#: The colliding ref_id, and the graph file that carries it twice.
REF_ID = "ledger"


GRAPH_FILE = "services.yml"


@dataclass(frozen=True)
class Answer:
    """One reader's whole answer over the duplicate-carrying directory."""

    #: The answer rendered as text, so a report can quote what the reader said.
    text: str
    #: Whether the answer distinguishes fewer nodes than the file carries.
    reduced: bool
    #: Why a non-reducing reader has nothing to drop. Empty when it reduces.
    reason: str


def _conn(root: Path) -> sqlite3.Connection:
    conn = open_db(root / ".beadloom" / "probe.db")
    create_schema(conn)
    return conn


def _nodes_on_disk(root: Path) -> list[dict[str, Any]]:
    text = (root / ".beadloom" / "_graph" / GRAPH_FILE).read_text(encoding="utf-8")
    return list(yaml.safe_load(text)["nodes"])


def _ask_load_graph(root: Path) -> Answer:
    conn = _conn(root)
    try:
        result = load_graph(root / ".beadloom" / "_graph", conn)
        kept = sorted(str(row[0]) for row in conn.execute("SELECT ref_id FROM nodes"))
    finally:
        conn.close()
    text = repr((result.nodes_loaded, kept, result.errors))
    return Answer(text, reduced=result.nodes_loaded < len(_nodes_on_disk(root)), reason="")


def _ask_compute_diff(root: Path) -> Answer:
    diff = compute_diff(root, since="HEAD")
    changes = sorted(f"{change.change_type}:{change.ref_id}" for change in diff.nodes)
    described = [duplicate.describe() for duplicate in diff.duplicates]
    return Answer(repr((changes, described)), reduced=bool(described), reason="")


def _ask_update_node_in_yaml(root: Path) -> Answer:
    conn = _conn(root)
    try:
        update_node_in_yaml(root / ".beadloom" / "_graph", conn, REF_ID, summary="probed")
    finally:
        conn.close()
    after = _nodes_on_disk(root)
    return Answer(
        repr(after),
        reduced=len(after) < 2,
        reason="answers about one ref_id rather than about a set, so it drops no node",
    )


def _ask_link(root: Path) -> Answer:
    result = CliRunner().invoke(
        main, ["link", REF_ID, "https://example.invalid/1", "--project", str(root)]
    )
    after = _nodes_on_disk(root)
    return Answer(
        repr((result.exit_code, after)),
        reduced=len(after) < 2,
        reason="answers about one ref_id rather than about a set, so it drops no node",
    )


def _ask_read_declared_docs(root: Path) -> Answer:
    docs = read_declared_docs(root / ".beadloom" / "_graph", root, root / "docs")
    declared = sum(len(node["docs"]) for node in _nodes_on_disk(root))  # type: ignore[arg-type]
    return Answer(
        repr(docs),
        reduced=len(docs) < declared,
        reason="keyed by document and not by ref_id, so both nodes' documents come back",
    )


def _ask_scan_project_files(root: Path) -> Answer:
    scanned = _scan_project_files(root, root / "docs")
    graph = sorted((rel, h) for rel, (h, kind) in scanned.items() if kind == "graph")
    return Answer(
        repr(graph),
        reduced=False,
        reason="reads bytes, and a file that will not parse into nodes still has bytes",
    )


def _ask_graph_files_now(root: Path) -> Answer:
    return Answer(
        repr(sorted(_graph_files_now(root).items())),
        reduced=False,
        reason="reads bytes, and a file that will not parse into nodes still has bytes",
    )


#: One probe per reader, by the name a traceback spells. The KEYS are checked
#: against the derived population, so a reader added there and not here fails by
#: name rather than by being quietly left out.
PROBES: dict[str, Callable[[Path], Answer]] = {
    "load_graph": _ask_load_graph,
    "compute_diff": _ask_compute_diff,
    "update_node_in_yaml": _ask_update_node_in_yaml,
    "link": _ask_link,
    "read_declared_docs": _ask_read_declared_docs,
    "_scan_project_files": _ask_scan_project_files,
    "_graph_files_now": _ask_graph_files_now,
}
