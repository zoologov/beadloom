"""The Expo bridge edges in an index: written beside every other edge, and only theirs refreshed.

BDL-080 S3b (``beadloom-wbqd``). The bridge set is deleted and rebuilt on every reindex,
as the import edges are; these cases hold what that must not touch: an edge the graph
YAML declares on the same pair keeps the YAML's row, and the derived import edges and
every other declared edge stay as they were.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from beadloom.graph.expo_modules import ExpoModules, refresh_bridge_edges
from beadloom.infrastructure.db import create_schema, open_db
from tests.support.expo_module_tree import EXPO_APP_TREE, HAPTIC_PULSE, SCREEN_LOCK, write_tree

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Iterator
    from pathlib import Path

_NODES = {
    "haptic-pulse": f"{HAPTIC_PULSE}/",
    "haptic-pulse-ios": f"{HAPTIC_PULSE}/ios/",
    "haptic-pulse-android": f"{HAPTIC_PULSE}/android/",
    "screen-lock": f"{SCREEN_LOCK}/",
    "screen-lock-ios": f"{SCREEN_LOCK}/ios/",
    "features-pulse": "src/features/pulse/",
}


@pytest.fixture()
def conn(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    write_tree(tmp_path, EXPO_APP_TREE)
    connection = open_db(tmp_path / "index.db")
    create_schema(connection)
    connection.executemany(
        "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, 'component', '', ?)",
        list(_NODES.items()),
    )
    yield connection
    connection.close()


def _edges(conn: sqlite3.Connection) -> set[tuple[str, str, str, str | None]]:
    rows = conn.execute(
        "SELECT src_ref_id, dst_ref_id, kind, json_extract(extra, '$.derived') FROM edges"
    ).fetchall()
    return {(str(r[0]), str(r[1]), str(r[2]), r[3]) for r in rows}


def test_a_declared_edge_on_the_same_pair_keeps_the_declared_row(
    tmp_path: Path, conn: sqlite3.Connection
) -> None:
    conn.execute(
        "INSERT INTO edges (src_ref_id, dst_ref_id, kind, extra) VALUES (?, ?, 'uses', ?)",
        ("screen-lock", "screen-lock-ios", json.dumps({"note": "declared"})),
    )

    written = refresh_bridge_edges(conn, ExpoModules(tmp_path))
    refresh_bridge_edges(conn, ExpoModules(tmp_path))

    assert written == 2
    assert ("screen-lock", "screen-lock-ios", "uses", None) in _edges(conn)
    assert ("screen-lock", "screen-lock-ios", "uses", "expo-module") not in _edges(conn)


def test_a_refresh_touches_no_edge_it_did_not_derive(
    tmp_path: Path, conn: sqlite3.Connection
) -> None:
    others = {
        ("features-pulse", "haptic-pulse", "depends_on", json.dumps({"derived": "imports"})),
        ("features-pulse", "screen-lock", "uses", "{}"),
    }
    conn.executemany(
        "INSERT INTO edges (src_ref_id, dst_ref_id, kind, extra) VALUES (?, ?, ?, ?)", others
    )

    refresh_bridge_edges(conn, ExpoModules(tmp_path))
    refresh_bridge_edges(conn, ExpoModules(tmp_path))

    assert _edges(conn) == {
        ("features-pulse", "haptic-pulse", "depends_on", "imports"),
        ("features-pulse", "screen-lock", "uses", None),
        ("haptic-pulse", "haptic-pulse-ios", "uses", "expo-module"),
        ("haptic-pulse", "haptic-pulse-android", "uses", "expo-module"),
        ("screen-lock", "screen-lock-ios", "uses", "expo-module"),
    }
