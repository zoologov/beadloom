"""``beadloom export`` carries the ``via: "@x"`` an edge records, and adds nothing to the rest.

BDL-082 S1a (``beadloom-r15q``), RFC D1. The reindex writes ``via: "@x"`` into the ``extra``
of a derived ``depends_on`` edge every import of which goes through the target's ``@x``
cross-import API. The export surfaces it as a top-level ``via`` on that edge — additive, as
``contract`` is: an edge without it has no ``via`` key, so an export of a project that does
not use the notation is byte-identical to before.
"""

from __future__ import annotations

import json

from beadloom.graph.federation import build_export
from tests.support.in_memory_graph import add_node, open_graph


def _edges() -> list[dict[str, object]]:
    conn = open_graph()
    for ref_id in ("entities-artist", "entities-song", "entities-album", "pages-home"):
        add_node(conn, ref_id, "component")
    for src, dst, extra in (
        ("entities-artist", "entities-song", {"derived": "imports", "via": "@x"}),
        (
            "entities-album",
            "entities-song",
            {"derived": "imports", "partly_via": "@x", "not_via": "src/a.ts:2"},
        ),
        ("pages-home", "entities-artist", {"derived": "imports"}),
    ):
        conn.execute(
            "INSERT INTO edges (src_ref_id, dst_ref_id, kind, extra) "
            "VALUES (?, ?, 'depends_on', ?)",
            (src, dst, json.dumps(extra)),
        )
    export = build_export(
        conn, repo="probe", commit_sha=None, exported_at="2026-10-11", generator="test"
    )
    edges = export["edges"]
    assert isinstance(edges, list)
    return edges


def test_an_edge_every_import_of_which_is_via_x_exports_it() -> None:
    [edge] = [e for e in _edges() if e["src"] == "entities-artist"]

    assert edge["via"] == "@x"


def test_an_edge_that_is_not_every_import_via_x_exports_no_via() -> None:
    by_src = {str(e["src"]): e for e in _edges()}

    assert "via" not in by_src["entities-album"]
    assert "via" not in by_src["pages-home"]
    assert set(by_src["pages-home"]) == {"src", "dst", "kind", "lifecycle"}
