"""Tests for beadloom.application.site_mermaid_guard (BDL-041 BEAD-01).

The generation-time Mermaid validity guard rejects the two F4 render bug
classes in pytest (no browser/node):

1. flowchart/``graph`` node ids that collide with a reserved keyword
   (e.g. a node literally named ``graph``) or carry an illegal charset.
2. C4 ``Rel(a, b, …)`` whose endpoint is NOT a declared diagram node
   (``Container``/``Component``/``Person``/``System*``) — the ``drawRels``
   crash on a Rel to the undeclared ``System`` root.

Known-bad fixtures must be caught; the real generated landscape + C4 (which
contain a ``graph`` domain node and a ``beadloom`` System root) must pass clean.
"""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

import pytest

from beadloom.application.site import (
    MermaidValidationError,
    _guard_diagrams,
    generate_site,
)
from beadloom.application.site_mermaid_guard import MermaidIssue, validate_mermaid
from beadloom.infrastructure.db import create_schema

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Flowchart / graph reserved-id + charset
# ---------------------------------------------------------------------------


def test_clean_flowchart_passes() -> None:
    text = "\n".join(
        [
            "```mermaid",
            "graph LR",
            "    n_cli[cli]",
            "    n_graph[graph]",
            '    click n_graph "/services/graph"',
            "    n_cli -->|USES| n_graph",
            "```",
        ]
    )
    assert validate_mermaid(text) == []


def test_reserved_keyword_node_id_is_caught() -> None:
    # A node literally named `graph` collides with the `graph LR` keyword.
    text = "\n".join(
        [
            "graph LR",
            "    graph[graph]",
            "    cli -->|USES| graph",
        ]
    )
    issues = validate_mermaid(text)
    assert any(i.kind == "reserved-id" for i in issues)
    assert any("graph" in i.message for i in issues)


def test_other_reserved_keywords_are_caught() -> None:
    for keyword in ("end", "subgraph", "class", "click", "style", "linkStyle"):
        text = f"graph LR\n    {keyword}[label]\n"
        issues = validate_mermaid(text)
        assert any(i.kind == "reserved-id" for i in issues), keyword


def test_illegal_charset_node_id_is_caught() -> None:
    text = "graph LR\n    bad-id[label]\n"
    issues = validate_mermaid(text)
    assert any(i.kind == "charset" for i in issues)


def test_prefixed_keyword_id_passes() -> None:
    # The fix: prefix ids so `graph` becomes `n_graph` — no longer reserved.
    text = "graph LR\n    n_graph[graph]\n"
    assert validate_mermaid(text) == []


# ---------------------------------------------------------------------------
# C4 Rel integrity
# ---------------------------------------------------------------------------


def test_clean_c4_passes() -> None:
    text = "\n".join(
        [
            "C4Container",
            '    Container(a, "A", "", "")',
            '    Container(b, "B", "", "")',
            '    Rel(a, b, "uses")',
        ]
    )
    assert validate_mermaid(text) == []


def test_c4_rel_to_undeclared_endpoint_is_caught() -> None:
    # Rel to `beadloom`, which is only a boundary wrapper, not a declared node.
    text = "\n".join(
        [
            "C4Container",
            '    System_Boundary(beadloom_boundary, "Beadloom") {',
            '        Container(application, "Application", "", "")',
            "    }",
            '    Rel(beadloom, application, "uses")',
        ]
    )
    issues = validate_mermaid(text)
    assert any(i.kind == "c4-rel-undeclared" for i in issues)
    assert any("beadloom" in i.message for i in issues)


def test_c4_rel_between_declared_nodes_passes() -> None:
    text = "\n".join(
        [
            "C4Container",
            '    System_Boundary(beadloom_boundary, "Beadloom") {',
            '        Container(application, "Application", "", "")',
            '        Container(graph, "Graph", "", "")',
            "    }",
            '    Rel(application, graph, "uses")',
        ]
    )
    assert validate_mermaid(text) == []


def test_c4_person_and_system_endpoints_are_declared() -> None:
    text = "\n".join(
        [
            "C4Container",
            '    Person(user, "User", "")',
            '    System(sys, "Sys", "")',
            '    Rel(user, sys, "uses")',
        ]
    )
    assert validate_mermaid(text) == []


def test_issue_repr_is_stable() -> None:
    issue = MermaidIssue(kind="reserved-id", message="node id 'graph' is reserved")
    assert issue.kind == "reserved-id"
    assert "graph" in issue.message


# ---------------------------------------------------------------------------
# Wiring into generate_site (raises on broken diagrams; real graph passes)
# ---------------------------------------------------------------------------


def _open() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    return conn


def _seed_graph_node_repro(conn: sqlite3.Connection) -> None:
    """A graph that reproduces BOTH F4 bug classes before the fix.

    - a domain literally named ``graph`` (landscape id collision);
    - a ``beadloom`` System root with children + a ``uses`` edge from the root
      (the C4 ``Rel(beadloom, …)`` to the undeclared boundary anchor).

    A produces/consumes contract on the ``graph`` node puts it into the local
    contract landscape, so the landscape id-prefix fix (``n_graph``) is still
    exercised by the real generator path (BDL-041 F4.4 made the landscape a
    contract graph rather than the structural arch).
    """
    nodes = [
        ("beadloom", "service", "Beadloom CLI.", None),
        ("graph", "domain", "Graph format.", "src/beadloom/graph"),
        ("cli", "service", "CLI.", "src/beadloom/services"),
    ]
    for ref_id, kind, summary, source in nodes:
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            (ref_id, kind, summary, source),
        )
    edges = [
        ("graph", "beadloom", "part_of", ""),
        ("cli", "beadloom", "part_of", ""),
        ("cli", "graph", "uses", ""),
        ("beadloom", "graph", "uses", ""),  # root -> child: the Rel-to-root repro
        # A contract on the reserved-keyword node, so it lands in the landscape.
        ("graph", "beadloom", "produces", "amqp:*/*:graph-event"),
        ("beadloom", "graph", "consumes", "amqp:*/*:graph-event"),
    ]
    for src, dst, kind, ckey in edges:
        conn.execute(
            "INSERT INTO edges (src_ref_id, dst_ref_id, kind, contract_key) "
            "VALUES (?, ?, ?, ?)",
            (src, dst, kind, ckey),
        )


def test_generate_site_passes_on_real_graph(tmp_path: Path) -> None:
    conn = _open()
    out = tmp_path / "site"
    try:
        _seed_graph_node_repro(conn)
        conn.commit()
        # Both bug classes are present in the seed graph; generation must NOT
        # raise — the fixes (n_ prefix + Rel-drop) keep every diagram clean.
        result = generate_site(conn, out, project_root=tmp_path)
    finally:
        conn.close()
    assert (out / "landscape.md") in result.written
    # The `graph` domain landscape id is prefixed; never the bare keyword.
    landscape = (out / "landscape.md").read_text(encoding="utf-8")
    assert "n_graph" in landscape


def test_guard_diagrams_raises_on_reserved_id(tmp_path: Path) -> None:
    bad = "\n".join(["# Page", "", "```mermaid", "graph LR", "    graph[graph]", "```"])
    with pytest.raises(MermaidValidationError) as exc:
        _guard_diagrams(tmp_path / "bad.md", bad)
    assert any(i.kind == "reserved-id" for i in exc.value.issues)


def test_guard_diagrams_raises_on_undeclared_rel(tmp_path: Path) -> None:
    bad = "\n".join(
        [
            "# Page",
            "",
            "```mermaid",
            "C4Container",
            '    System_Boundary(beadloom_boundary, "Beadloom") {',
            '        Container(application, "App", "", "")',
            "    }",
            '    Rel(beadloom, application, "uses")',
            "```",
        ]
    )
    with pytest.raises(MermaidValidationError) as exc:
        _guard_diagrams(tmp_path / "bad.md", bad)
    assert any(i.kind == "c4-rel-undeclared" for i in exc.value.issues)


def test_guard_ignores_non_markdown(tmp_path: Path) -> None:
    # A .json file is never guarded (it is not a rendered page).
    _guard_diagrams(tmp_path / "dashboard.data.json", "graph LR\n    graph[x]\n")
