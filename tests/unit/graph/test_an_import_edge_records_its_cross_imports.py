"""A derived ``depends_on`` edge records whether every import behind it is a cross-import.

BDL-082 S1a (``beadloom-r15q``), RFC D1. feature-sliced.design's ``@x`` notation: entity A
declares ``entities/A/@x/B.ts`` (or ``@x/B/index.ts``), a public API for the code of entity
B alone. When EVERY import behind an edge from B to A lands on that file, the reindex writes
``via: "@x"`` into the edge's ``extra``; when some do and one does not, it writes
``partly_via: "@x"`` and ``not_via: "<file>:<line>"`` of the first that does not, so the
layer rule can name it without reading ``code_imports``. The fact is about imports, not about
layers: it is recorded on any derived edge, and the layer rule decides what it means.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from beadloom.graph.import_resolver import create_import_edges
from tests.support.in_memory_graph import open_graph

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path

#: The specification's example (``/docs/reference/layers``), plus the files the cases add.
FILES = (
    "src/entities/song/index.ts",
    "src/entities/song/model/song.ts",
    "src/entities/song/@x/artist.ts",
    "src/entities/song/@x/album/index.ts",
    "src/entities/song/model/@x/artist.ts",
    "src/entities/artist/model/artist.ts",
    "src/entities/artist/model/rel.ts",
    "src/entities/artist/ui/card.ts",
    "src/entities/album/model/album.ts",
    "src/entities/playlist/model/playlist.ts",
)
NODES = {
    "entities-song": "src/entities/song/",
    "entities-artist": "src/entities/artist/",
    "entities-album": "src/entities/album/",
    "entities-playlist": "src/entities/playlist/",
}


def _graph(root: Path) -> sqlite3.Connection:
    for rel in FILES:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("export const x = 1\n", encoding="utf-8")
    conn = open_graph()
    for ref_id, source in NODES.items():
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, 'component', '', ?)",
            (ref_id, source),
        )
    return conn


def _import(conn: sqlite3.Connection, importer: str, line: int, specifier: str) -> None:
    conn.execute(
        "INSERT INTO code_imports (file_path, line_number, import_path, resolved_ref_id,"
        " file_hash) VALUES (?, ?, ?, 'entities-song', '')",
        (importer, line, specifier),
    )


def _extra(conn: sqlite3.Connection, src: str) -> dict[str, object]:
    row = conn.execute(
        "SELECT extra FROM edges WHERE src_ref_id = ? AND dst_ref_id = 'entities-song' "
        "AND kind = 'depends_on'",
        (src,),
    ).fetchone()
    assert row is not None
    loaded = json.loads(row[0])
    assert isinstance(loaded, dict)
    return loaded


def test_every_import_through_the_api_opened_to_the_importer_is_via_x(tmp_path: Path) -> None:
    conn = _graph(tmp_path)
    _import(conn, "src/entities/artist/model/artist.ts", 1, "entities/song/@x/artist")
    _import(conn, "src/entities/artist/model/rel.ts", 1, "../../song/@x/artist")
    _import(conn, "src/entities/artist/ui/card.ts", 1, "@/entities/song/@x/artist")

    create_import_edges(conn, project_root=tmp_path)

    assert _extra(conn, "entities-artist") == {"derived": "imports", "via": "@x"}


def test_the_api_as_a_folder_entered_through_its_index_is_via_x(tmp_path: Path) -> None:
    conn = _graph(tmp_path)
    _import(conn, "src/entities/album/model/album.ts", 1, "@/entities/song/@x/album")

    create_import_edges(conn, project_root=tmp_path)

    assert _extra(conn, "entities-album") == {"derived": "imports", "via": "@x"}


def test_one_import_past_the_api_makes_a_mixed_edge_that_names_it(tmp_path: Path) -> None:
    conn = _graph(tmp_path)
    _import(conn, "src/entities/artist/model/artist.ts", 1, "entities/song/@x/artist")
    _import(conn, "src/entities/artist/model/rel.ts", 1, "../../song/@x/artist")
    _import(conn, "src/entities/artist/model/rel.ts", 2, "@/entities/song")

    create_import_edges(conn, project_root=tmp_path)

    assert _extra(conn, "entities-artist") == {
        "derived": "imports",
        "partly_via": "@x",
        "not_via": "src/entities/artist/model/rel.ts:2",
    }


def test_the_api_opened_to_another_slice_is_not_via_x(tmp_path: Path) -> None:
    conn = _graph(tmp_path)
    _import(conn, "src/entities/playlist/model/playlist.ts", 1, "@/entities/song/@x/artist")

    create_import_edges(conn, project_root=tmp_path)

    assert _extra(conn, "entities-playlist") == {"derived": "imports"}


def test_an_x_folder_below_the_slices_top_is_not_its_api(tmp_path: Path) -> None:
    conn = _graph(tmp_path)
    _import(conn, "src/entities/artist/model/artist.ts", 1, "@/entities/song/model/@x/artist")

    create_import_edges(conn, project_root=tmp_path)

    assert _extra(conn, "entities-artist") == {"derived": "imports"}


def test_without_the_project_root_no_fact_is_recorded(tmp_path: Path) -> None:
    conn = _graph(tmp_path)
    _import(conn, "src/entities/artist/model/artist.ts", 1, "entities/song/@x/artist")

    create_import_edges(conn)

    assert _extra(conn, "entities-artist") == {"derived": "imports"}


def test_a_declared_edge_on_the_same_pair_keeps_the_declared_row(tmp_path: Path) -> None:
    conn = _graph(tmp_path)
    conn.execute(
        "INSERT INTO edges (src_ref_id, dst_ref_id, kind, extra) "
        "VALUES ('entities-artist', 'entities-song', 'depends_on', ?)",
        (json.dumps({"note": "declared"}),),
    )
    _import(conn, "src/entities/artist/model/artist.ts", 1, "entities/song/@x/artist")

    create_import_edges(conn, project_root=tmp_path)

    assert _extra(conn, "entities-artist") == {"note": "declared"}
