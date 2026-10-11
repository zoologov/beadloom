"""The ``@x`` notation's one reading: where an import lands, the fact an edge records, its JSON.

BDL-082 S1 (RFC D1). :mod:`beadloom.graph.rules.cross_imports` is the module both slice rules
and the reindex read ``@x`` through. The rule files exercise it through a whole rule; these
cases hold the reading itself, at the edges a rule never reaches: a relative import that lands
nowhere or outside the folder, a specifier whose leading segments climb out of the folder, an
edge with no import through ``@x``, a mixed edge's fact, a stored ``not_via`` that is empty,
and the ``extra`` JSON the reindex writes.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from beadloom.graph.rules.cross_imports import (
    CrossImportFact,
    edge_cross_import,
    edge_extra,
    located,
    read_cross_import_facts,
)
from tests.support.in_memory_graph import open_graph

if TYPE_CHECKING:
    from pathlib import Path

SONG = "src/entities/song"
ARTIST = "src/entities/artist"


def _tree(root: Path, *files: str) -> None:
    for rel in files:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("export {}\n", encoding="utf-8")


@pytest.mark.parametrize(
    "specifier",
    ["../../song/@x/nobody", "../../album/index"],
    ids=["lands-nowhere", "lands-outside-the-folder"],
)
def test_a_relative_import_that_does_not_land_inside_the_folder_is_located_nowhere(
    tmp_path: Path, specifier: str
) -> None:
    _tree(tmp_path, f"{SONG}/@x/artist.ts", "src/entities/album/index.ts")

    found = located(specifier, f"{ARTIST}/model/artist.ts", SONG, tmp_path)

    assert found is None


def test_a_specifier_climbing_out_of_the_folder_is_matched_by_its_trailing_path(
    tmp_path: Path,
) -> None:
    _tree(tmp_path, f"{SONG}/@x/artist.ts")

    found = located("a/../../../song/@x/artist", f"{ARTIST}/model/artist.ts", SONG, tmp_path)

    assert found == f"{SONG}/@x/artist.ts"


def test_an_edge_with_no_import_through_the_api_records_no_fact(tmp_path: Path) -> None:
    _tree(tmp_path, f"{SONG}/index.ts", f"{SONG}/@x/artist.ts")
    imports = [(f"{ARTIST}/model/artist.ts", 1, "@/entities/song")]

    fact = edge_cross_import(imports, ARTIST, SONG, tmp_path)

    assert fact is None


def test_a_mixed_edge_records_that_not_every_import_goes_through_the_api(
    tmp_path: Path,
) -> None:
    _tree(tmp_path, f"{SONG}/index.ts", f"{SONG}/@x/artist.ts")
    imports = [
        (f"{ARTIST}/model/artist.ts", 1, "@/entities/song/@x/artist"),
        (f"{ARTIST}/model/rel.ts", 2, "@/entities/song"),
    ]

    fact = edge_cross_import(imports, ARTIST, SONG, tmp_path)

    assert fact == CrossImportFact(every=False, not_via=f"{ARTIST}/model/rel.ts:2")


def test_a_stored_mixed_fact_with_an_empty_location_names_none() -> None:
    conn = open_graph()
    conn.execute(
        "INSERT INTO edges (src_ref_id, dst_ref_id, kind, extra) VALUES (?, ?, ?, ?)",
        (
            "entities-artist",
            "entities-song",
            "depends_on",
            json.dumps({"derived": "imports", "partly_via": "@x", "not_via": ""}),
        ),
    )

    facts = read_cross_import_facts(conn, "depends_on")

    assert facts == {
        ("entities-artist", "entities-song"): CrossImportFact(every=False, not_via=None)
    }


@pytest.mark.parametrize(
    ("fact", "expected"),
    [
        (None, {"derived": "imports"}),
        (CrossImportFact(every=True, not_via=None), {"derived": "imports", "via": "@x"}),
    ],
    ids=["no-fact", "via-x"],
)
def test_the_extra_of_a_derived_edge_names_its_provenance_and_its_fact(
    fact: CrossImportFact | None, expected: dict[str, str]
) -> None:
    extra = edge_extra("imports", fact)

    assert json.loads(extra) == expected


def test_the_extra_keeps_a_location_in_its_own_characters() -> None:
    fact = CrossImportFact(every=False, not_via="src/entities/артист/model/rel.ts:2")

    extra = edge_extra("imports", fact)

    assert "артист" in extra
