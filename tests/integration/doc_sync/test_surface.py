"""Tests for beadloom.doc_sync.surface — Layer 2 reference surface-drift.

Covers the coarse, deterministic surface signatures (cli / graph / flow.yml),
the `<!-- beadloom:watches=... -->` annotation parser, and the aggregate hash.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.doc_sync.surface import (
    VALID_SURFACES,
    aggregate_hash,
    cli_signature,
    flow_signature,
    graph_signature,
    parse_watches,
    surface_signature,
)
from beadloom.infrastructure.db import create_schema, open_db

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path


@pytest.fixture()
def conn(tmp_path: Path) -> sqlite3.Connection:
    db_path = tmp_path / "test.db"
    c = open_db(db_path)
    create_schema(c)
    return c


# --------------------------------------------------------------------------
# parse_watches
# --------------------------------------------------------------------------


def test_parse_watches_single() -> None:
    assert parse_watches("<!-- beadloom:watches=cli -->\n# Title") == ["cli"]


def test_parse_watches_multiple_ordered() -> None:
    text = "intro\n<!-- beadloom:watches=cli,graph,flow.yml -->\nbody"
    assert parse_watches(text) == ["cli", "graph", "flow.yml"]


def test_parse_watches_preserves_declared_order() -> None:
    text = "<!-- beadloom:watches=flow.yml,cli -->"
    assert parse_watches(text) == ["flow.yml", "cli"]


def test_parse_watches_tolerates_spaces() -> None:
    text = "<!-- beadloom:watches = cli , graph -->"
    assert parse_watches(text) == ["cli", "graph"]


def test_parse_watches_none_when_absent() -> None:
    assert parse_watches("# A doc with no annotation\n") is None


def test_parse_watches_ignores_unknown_surfaces() -> None:
    text = "<!-- beadloom:watches=cli,bogus,graph -->"
    assert parse_watches(text) == ["cli", "graph"]


def test_parse_watches_none_when_only_unknown() -> None:
    assert parse_watches("<!-- beadloom:watches=bogus -->") is None


def test_parse_watches_dedupes_repeats() -> None:
    assert parse_watches("<!-- beadloom:watches=cli,cli,graph -->") == ["cli", "graph"]


def test_valid_surfaces_known_set() -> None:
    assert VALID_SURFACES == ("cli", "graph", "flow.yml")


# --------------------------------------------------------------------------
# cli_signature
# --------------------------------------------------------------------------


def test_cli_signature_deterministic() -> None:
    assert cli_signature() == cli_signature()


def test_cli_signature_is_a_sha256_digest() -> None:
    sig = cli_signature()
    # Coarse signature is hashed, not raw text: 64 hex chars.
    assert len(sig) == 64
    assert all(c in "0123456789abcdef" for c in sig)


# --------------------------------------------------------------------------
# graph_signature
# --------------------------------------------------------------------------


def _add_node(conn: sqlite3.Connection, ref_id: str, kind: str = "feature") -> None:
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, '')",
        (ref_id, kind),
    )
    conn.commit()


def _add_edge(conn: sqlite3.Connection, src: str, dst: str, kind: str = "part_of") -> None:
    conn.execute(
        "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
        (src, dst, kind),
    )
    conn.commit()


def test_graph_signature_deterministic(conn: sqlite3.Connection) -> None:
    _add_node(conn, "a")
    _add_node(conn, "b")
    assert graph_signature(conn) == graph_signature(conn)


def test_graph_signature_changes_on_node_added(conn: sqlite3.Connection) -> None:
    _add_node(conn, "a")
    before = graph_signature(conn)
    _add_node(conn, "b")
    assert graph_signature(conn) != before


def test_graph_signature_changes_on_edge_added(conn: sqlite3.Connection) -> None:
    _add_node(conn, "a")
    _add_node(conn, "b")
    before = graph_signature(conn)
    _add_edge(conn, "a", "b")
    assert graph_signature(conn) != before


def test_graph_signature_order_independent(conn: sqlite3.Connection) -> None:
    _add_node(conn, "b")
    _add_node(conn, "a")
    sig1 = graph_signature(conn)
    # The identity set is sorted, so insertion order must not matter.
    conn.execute("DELETE FROM nodes")
    conn.commit()
    _add_node(conn, "a")
    _add_node(conn, "b")
    assert graph_signature(conn) == sig1


def test_graph_signature_stable_on_summary_change(conn: sqlite3.Connection) -> None:
    # Coarse identity set = ref_id + kind only; summary text must not move it.
    _add_node(conn, "a")
    before = graph_signature(conn)
    conn.execute("UPDATE nodes SET summary = 'changed' WHERE ref_id = 'a'")
    conn.commit()
    assert graph_signature(conn) == before


# --------------------------------------------------------------------------
# flow_signature
# --------------------------------------------------------------------------


def test_flow_signature_empty_when_absent(tmp_path: Path) -> None:
    assert flow_signature(tmp_path) == ""


def test_flow_signature_deterministic(tmp_path: Path) -> None:
    (tmp_path / ".beadloom").mkdir()
    (tmp_path / ".beadloom" / "flow.yml").write_text("methodology: ddd\nstack: python\n")
    assert flow_signature(tmp_path) == flow_signature(tmp_path)


def test_flow_signature_canonical_ignores_key_order(tmp_path: Path) -> None:
    (tmp_path / ".beadloom").mkdir()
    flow = tmp_path / ".beadloom" / "flow.yml"
    flow.write_text("methodology: ddd\nstack: python\n")
    sig1 = flow_signature(tmp_path)
    flow.write_text("stack: python\nmethodology: ddd\n")
    assert flow_signature(tmp_path) == sig1


def test_flow_signature_changes_on_content_change(tmp_path: Path) -> None:
    (tmp_path / ".beadloom").mkdir()
    flow = tmp_path / ".beadloom" / "flow.yml"
    flow.write_text("methodology: ddd\n")
    before = flow_signature(tmp_path)
    flow.write_text("methodology: fsd\n")
    assert flow_signature(tmp_path) != before


def test_flow_signature_ignores_comments_and_whitespace(tmp_path: Path) -> None:
    (tmp_path / ".beadloom").mkdir()
    flow = tmp_path / ".beadloom" / "flow.yml"
    flow.write_text("methodology: ddd\n")
    before = flow_signature(tmp_path)
    flow.write_text("# a comment\nmethodology:    ddd\n\n")
    assert flow_signature(tmp_path) == before


# --------------------------------------------------------------------------
# surface_signature dispatch + aggregate_hash
# --------------------------------------------------------------------------


def test_surface_signature_dispatch(conn: sqlite3.Connection, tmp_path: Path) -> None:
    assert surface_signature("cli", conn, tmp_path) == cli_signature()
    _add_node(conn, "a")
    assert surface_signature("graph", conn, tmp_path) == graph_signature(conn)
    assert surface_signature("flow.yml", conn, tmp_path) == flow_signature(tmp_path)


def test_surface_signature_unknown_raises(conn: sqlite3.Connection, tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unknown surface"):
        surface_signature("bogus", conn, tmp_path)


def test_aggregate_hash_deterministic(conn: sqlite3.Connection, tmp_path: Path) -> None:
    _add_node(conn, "a")
    h1 = aggregate_hash(["cli", "graph"], conn, tmp_path)
    h2 = aggregate_hash(["cli", "graph"], conn, tmp_path)
    assert h1 == h2


def test_aggregate_hash_order_sensitive(conn: sqlite3.Connection, tmp_path: Path) -> None:
    _add_node(conn, "a")
    assert aggregate_hash(["cli", "graph"], conn, tmp_path) != aggregate_hash(
        ["graph", "cli"], conn, tmp_path
    )


def test_aggregate_hash_changes_when_a_watched_surface_drifts(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    _add_node(conn, "a")
    before = aggregate_hash(["graph"], conn, tmp_path)
    _add_node(conn, "b")
    assert aggregate_hash(["graph"], conn, tmp_path) != before


def test_aggregate_hash_unaffected_by_unwatched_surface(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    (tmp_path / ".beadloom").mkdir()
    flow = tmp_path / ".beadloom" / "flow.yml"
    flow.write_text("methodology: ddd\n")
    _add_node(conn, "a")
    before = aggregate_hash(["graph"], conn, tmp_path)
    # Mutate flow.yml — NOT watched, so the graph-only aggregate must not move.
    flow.write_text("methodology: fsd\n")
    assert aggregate_hash(["graph"], conn, tmp_path) == before
