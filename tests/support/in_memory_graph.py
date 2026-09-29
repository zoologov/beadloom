"""A graph index in memory: the schema, nodes with tags, and edges — nothing else.

Moved out of ``test_the_view_and_the_rule_engine_read_one_layer_declaration.py`` when
BDL-074 E1 split it by node: the architecture view's tests and the rule engine's
liveness tests build the same small graphs, and a helper two test modules share lives
here rather than in either of them.
"""

from __future__ import annotations

import json
import sqlite3

from beadloom.graph.rules.types import LayerDef
from beadloom.infrastructure.db import create_schema

#: The four layers this repository declares, in the order it declares them.
DDD_LAYERS = (
    LayerDef(name="services", tag="layer-service"),
    LayerDef(name="application", tag="layer-application"),
    LayerDef(name="domains", tag="layer-domain"),
    LayerDef(name="infrastructure", tag="layer-infra"),
)


def open_graph() -> sqlite3.Connection:
    """An empty index in memory, with the schema and ``sqlite3.Row`` rows."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    return conn


def add_node(conn: sqlite3.Connection, ref_id: str, kind: str, *tags: str) -> None:
    """A node carrying *tags*, with no source."""
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary, source, extra) VALUES (?, ?, ?, ?, ?)",
        (ref_id, kind, f"{ref_id} summary.", None, json.dumps({"tags": list(tags)})),
    )


def add_edge(conn: sqlite3.Connection, src: str, dst: str, kind: str) -> None:
    """An edge of *kind* from *src* to *dst*."""
    conn.execute(
        "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)", (src, dst, kind)
    )
