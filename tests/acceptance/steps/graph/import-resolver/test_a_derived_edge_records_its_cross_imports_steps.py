"""Steps for `graph/import-resolver/a_derived_edge_records_its_cross_imports.feature`.

BDL-082 S1a (`beadloom-r15q`). The specification's `@x` example is written to disk, the real
`reindex` and `incremental_reindex` index it, and the edge row is read back from the index;
`beadloom export` runs through the CLI. The comparison with a fresh index reads each derived
edge's `extra` as well as its ends, because the fact lives there.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
from typing import TYPE_CHECKING, Any

import pytest
from click.testing import CliRunner
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.application.reindex import incremental_reindex, reindex
from beadloom.services.cli import main
from tests.support.fsd_cross_import_tree import (
    SPEC_CROSS_IMPORTS,
    SPEC_SLICES,
    write_fsd_project,
)

if TYPE_CHECKING:
    from pathlib import Path

pytest.importorskip("tree_sitter_typescript")

scenarios("../../../graph/import-resolver/a_derived_edge_records_its_cross_imports.feature")

_EDGES = "SELECT src_ref_id, dst_ref_id, extra FROM edges WHERE kind = 'depends_on'"


@given(
    "the specification's song and artist entities, the artist importing the song's API "
    "three ways"
)
def _spec(tmp_path: Path, state: dict[str, Any]) -> None:
    state["root"] = tmp_path / "probe"
    write_fsd_project(state["root"], SPEC_CROSS_IMPORTS, SPEC_SLICES)


def _extra(root: Path, src: str, dst: str) -> dict[str, object]:
    with sqlite3.connect(root / ".beadloom" / "beadloom.db") as conn:
        row = conn.execute(
            "SELECT extra FROM edges WHERE kind = 'depends_on' AND src_ref_id = ? "
            "AND dst_ref_id = ?",
            (src, dst),
        ).fetchone()
    assert row is not None, (src, dst)
    loaded = json.loads(row[0])
    assert isinstance(loaded, dict)
    return loaded


@when(
    parsers.parse(
        '"{importer}" imports the song through its index and the index is updated'
    )
)
def _plain_import(state: dict[str, Any], importer: str) -> None:
    root: Path = state["root"]
    (root / importer).write_text(
        "import type { Song } from '@/entities/song'\nexport const rel = (s: Song) => s\n",
        encoding="utf-8",
    )
    incremental_reindex(root)


@when(
    parsers.parse(
        'the song\'s API for the artist moves into "{folder_index}" and the index is updated'
    )
)
def _api_moves(state: dict[str, Any], folder_index: str) -> None:
    root: Path = state["root"]
    old = root / "src/entities/song/@x/artist.ts"
    new = root / folder_index
    new.parent.mkdir(parents=True, exist_ok=True)
    new.write_text("export type { Song } from '../../model/song'\n", encoding="utf-8")
    old.unlink()
    incremental_reindex(root)


@then(parsers.parse('the edge from "{src}" to "{dst}" records via "{via}"'))
def _records_via(state: dict[str, Any], src: str, dst: str, via: str) -> None:
    assert _extra(state["root"], src, dst) == {"derived": "imports", "via": via}


@then(
    parsers.parse(
        'the edge from "{src}" to "{dst}" records partly via "{via}", not via "{where}"'
    )
)
def _records_partly(state: dict[str, Any], src: str, dst: str, via: str, where: str) -> None:
    assert _extra(state["root"], src, dst) == {
        "derived": "imports",
        "partly_via": via,
        "not_via": where,
    }


@then(
    parsers.parse(
        'beadloom export carries via "{via}" on the edge from "{src}" to "{dst}"'
    )
)
def _export_carries(state: dict[str, Any], via: str, src: str, dst: str) -> None:
    result = CliRunner().invoke(main, ["export", "--project", str(state["root"])])
    assert result.exit_code == 0, result.output
    edges = json.loads(result.stdout)["edges"]
    [edge] = [e for e in edges if (e["src"], e["dst"], e["kind"]) == (src, dst, "depends_on")]
    assert edge["via"] == via


def _rows(root: Path) -> list[tuple[str, str, str]]:
    with sqlite3.connect(root / ".beadloom" / "beadloom.db") as conn:
        return sorted((str(a), str(b), str(c)) for a, b, c in conn.execute(_EDGES).fetchall())


@then("every derived edge and its extra equals a fresh index of the same tree")
def _equals_fresh(tmp_path: Path, state: dict[str, Any]) -> None:
    root: Path = state["root"]
    fresh = tmp_path / "fresh"
    shutil.copytree(root, fresh, ignore=shutil.ignore_patterns("beadloom.db*"))
    reindex(fresh)
    assert _rows(root) == _rows(fresh)
