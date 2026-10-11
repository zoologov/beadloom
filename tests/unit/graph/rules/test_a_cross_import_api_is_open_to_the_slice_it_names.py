"""``slice_public_api``: ``A/@x/B`` is a second public API of A, open to B alone (BDL-082 S1b).

feature-sliced.design, *Public API for cross-imports*: "entity A can declare a separate
public API just for entity B" — the file ``entities/A/@x/B.ts``, imported as
``entities/A/@x/B`` by B. The specification's own example is the artist entity reading the
song entity through ``entities/song/@x/artist``. 9.0.0 read every import of it as reaching
past the song slice's index: three false errors on the spec's example (axes.md, gap 1).

Which LAYER may use ``@x`` is the layer rule's question (RFC D1, the derived edge fact);
this rule answers only who may enter the API.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from beadloom.graph.rules.slices import evaluate_slice_public_api_rules
from beadloom.graph.rules.types import SlicePublicApiRule
from tests.support.in_memory_graph import open_graph

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path

RULE = SlicePublicApiRule(
    name="fsd-public-api", description="", tags=("fsd-pages", "fsd-features", "fsd-entities")
)


def _write(root: Path, *paths: str) -> None:
    for rel in paths:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("export const x = 1\n", encoding="utf-8")


def _graph(root: Path) -> sqlite3.Connection:
    """The specification's song and artist, a third entity, a page and two features."""
    _write(
        root,
        "src/entities/song/index.ts",
        "src/entities/song/model/song.ts",
        "src/entities/song/@x/artist.ts",
        "src/entities/song/@x/playlist/index.ts",
        "src/entities/song/@x/playlist/deep.ts",
        "src/entities/artist/index.ts",
        "src/entities/artist/model/artist.ts",
        "src/entities/album/index.ts",
        "src/entities/album/model/album.ts",
        "src/entities/playlist/index.ts",
        "src/entities/playlist/model/playlist.ts",
        "src/pages/artist/index.ts",
        "src/pages/artist/ui/page.ts",
        "src/features/a/index.ts",
        "src/features/a/@x/b.ts",
        "src/features/b/index.ts",
        "src/features/b/model/b.ts",
    )
    conn = open_graph()
    for ref_id, source, tag in (
        ("entities-song", "src/entities/song/", "fsd-entities"),
        ("entities-artist", "src/entities/artist/", "fsd-entities"),
        ("entities-album", "src/entities/album/", "fsd-entities"),
        ("entities-playlist", "src/entities/playlist/", "fsd-entities"),
        ("pages-artist", "src/pages/artist/", "fsd-pages"),
        ("features-a", "src/features/a/", "fsd-features"),
        ("features-b", "src/features/b/", "fsd-features"),
    ):
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source, extra) VALUES (?, ?, ?, ?, ?)",
            (ref_id, "component", ref_id, source, json.dumps({"tags": [tag]})),
        )
    return conn


def _import(conn: sqlite3.Connection, importer: str, specifier: str, resolved: str) -> None:
    conn.execute(
        "INSERT INTO code_imports (file_path, line_number, import_path, resolved_ref_id, "
        "file_hash) VALUES (?, ?, ?, ?, 'h')",
        (importer, 1, specifier, resolved),
    )


def _findings(conn: sqlite3.Connection, root: Path) -> list[tuple[str | None, str | None]]:
    return [
        (v.file_path, v.to_ref_id)
        for v in evaluate_slice_public_api_rules(conn, [RULE], project_root=root)
    ]


@pytest.mark.parametrize(
    "specifier",
    ["entities/song/@x/artist", "@/entities/song/@x/artist", "../../song/@x/artist"],
)
def test_the_named_slice_enters_through_the_api_opened_to_it(
    tmp_path: Path, specifier: str
) -> None:
    # The three import forms the axes probe measured: bare through baseUrl, the alias,
    # and relative. 9.0.0 reported each as reaching past entities-song's index.
    conn = _graph(tmp_path)
    _import(conn, "src/entities/artist/model/artist.ts", specifier, "entities-song")

    assert _findings(conn, tmp_path) == []


def test_a_folder_form_of_the_api_is_entered_through_its_index(tmp_path: Path) -> None:
    # `@x/<B>/index.*` is the folder form `@feature-sliced/filesystem` reads as well.
    conn = _graph(tmp_path)
    _import(
        conn,
        "src/entities/playlist/model/playlist.ts",
        "@/entities/song/@x/playlist",
        "entities-song",
    )

    assert _findings(conn, tmp_path) == []


def test_a_file_past_the_folder_form_of_the_api_is_a_finding(tmp_path: Path) -> None:
    conn = _graph(tmp_path)
    _import(
        conn,
        "src/entities/playlist/model/playlist.ts",
        "@/entities/song/@x/playlist/deep",
        "entities-song",
    )

    assert _findings(conn, tmp_path) == [
        ("src/entities/playlist/model/playlist.ts", "entities-song")
    ]


def test_a_third_slice_reaching_the_api_opened_to_another_is_a_finding(
    tmp_path: Path,
) -> None:
    conn = _graph(tmp_path)
    _import(
        conn, "src/entities/album/model/album.ts", "@/entities/song/@x/artist", "entities-song"
    )

    (finding,) = evaluate_slice_public_api_rules(conn, [RULE], project_root=tmp_path)

    assert finding.file_path == "src/entities/album/model/album.ts"
    assert finding.from_ref_id == "entities-album"
    assert finding.to_ref_id == "entities-song"
    assert "src/entities/song/@x/artist.ts" in finding.message
    assert "'artist'" in finding.message
    assert "a cross-import API is open to the one slice it names" in finding.message
    assert "entity A can declare a separate public API just for entity B" in finding.message
    assert finding.remediation is not None


def test_a_slice_of_the_same_name_on_another_layer_is_not_the_slice_named(
    tmp_path: Path,
) -> None:
    # `pages/artist` is no entity: the API is the artist ENTITY's, a sibling of the song.
    conn = _graph(tmp_path)
    _import(conn, "src/pages/artist/ui/page.ts", "@/entities/song/@x/artist", "entities-song")

    assert _findings(conn, tmp_path) == [("src/pages/artist/ui/page.ts", "entities-song")]


def test_a_cross_import_api_off_the_entities_layer_is_left_to_the_layer_rule(
    tmp_path: Path,
) -> None:
    # `features/a/@x/b` is a finding of the layer rule ("@x is for the Entities layer
    # only", RFC D1); this rule says only that b is the slice the API is open to.
    conn = _graph(tmp_path)
    _import(conn, "src/features/b/model/b.ts", "@/features/a/@x/b", "features-a")

    assert _findings(conn, tmp_path) == []
