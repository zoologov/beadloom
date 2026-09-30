"""A node with some annotated files keeps a pair for every file it owns (``beadloom-oo4m``).

BDL-076 K2. ``build_sync_state`` took a node's annotated files OR the files its
``source`` owns, so one annotation dropped the pairs of every unannotated sibling.
``check_source_coverage`` listed only ``*.py`` directly inside the source
directory, so the dropped files were never named. These tests pin both halves
against rows written straight into an index, with no parser involved.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from beadloom.doc_sync.engine import build_sync_state, check_source_coverage
from beadloom.infrastructure.db import create_schema, open_db

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Iterator
    from pathlib import Path


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    proj = tmp_path / "proj"
    (proj / "docs").mkdir(parents=True)
    (proj / ".beadloom").mkdir(parents=True)
    return proj


@pytest.fixture()
def conn(project: Path) -> Iterator[sqlite3.Connection]:
    c = open_db(project / ".beadloom" / "test.db")
    create_schema(c)
    try:
        yield c
    finally:
        c.close()


def _node(conn: sqlite3.Connection, ref_id: str, source: str, doc: str | None) -> None:
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, 'component', ?, ?)",
        (ref_id, ref_id, source),
    )
    if doc is not None:
        conn.execute(
            "INSERT INTO docs (path, kind, ref_id, hash) VALUES (?, 'other', ?, 'dochash')",
            (doc, ref_id),
        )


def _code_file(
    conn: sqlite3.Connection, project: Path, path: str, *, annotated_as: str | None = None
) -> None:
    """Write *path* to disk and into ``file_index``; annotate one symbol if asked."""
    on_disk = project / path
    on_disk.parent.mkdir(parents=True, exist_ok=True)
    on_disk.write_text("export const x = 1\n", encoding="utf-8")
    conn.execute(
        "INSERT INTO file_index (path, hash, kind, indexed_at) VALUES (?, ?, 'code', 'now')",
        (path, f"hash-of-{path}"),
    )
    if annotated_as is not None:
        conn.execute(
            "INSERT INTO code_symbols (file_path, symbol_name, kind, line_start, line_end, "
            "annotations, file_hash) VALUES (?, 'x', 'variable', 1, 1, ?, ?)",
            (path, json.dumps({"component": annotated_as}), f"hash-of-{path}"),
        )


def _pairs_of(conn: sqlite3.Connection, ref_id: str) -> set[str]:
    return {p.code_path for p in build_sync_state(conn) if p.ref_id == ref_id}


def _record_pairs(conn: sqlite3.Connection) -> None:
    for pair in build_sync_state(conn):
        conn.execute(
            "INSERT INTO sync_state (doc_path, code_path, ref_id, code_hash_at_sync, "
            "doc_hash_at_sync, synced_at, status) VALUES (?, ?, ?, ?, ?, 'now', 'ok')",
            (pair.doc_path, pair.code_path, pair.ref_id, pair.code_hash, pair.doc_hash),
        )


class TestBuildSyncState:
    def test_an_annotation_on_one_file_keeps_the_unannotated_siblings(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        _node(conn, "counter", "src/counter/", "counter.md")
        _code_file(conn, project, "src/counter/model/useCounter.js", annotated_as="counter")
        _code_file(conn, project, "src/counter/lib/format.js")
        _code_file(conn, project, "src/counter/ui/Counter.vue")

        assert _pairs_of(conn, "counter") == {
            "src/counter/model/useCounter.js",
            "src/counter/lib/format.js",
            "src/counter/ui/Counter.vue",
        }

    def test_a_file_annotated_for_another_node_is_left_to_that_node(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        _node(conn, "counter", "src/counter/", "counter.md")
        _node(conn, "badge", "src/badge/", "badge.md")
        _code_file(conn, project, "src/counter/model/useCounter.js", annotated_as="counter")
        _code_file(conn, project, "src/counter/ui/Badge.vue", annotated_as="badge")

        assert _pairs_of(conn, "counter") == {"src/counter/model/useCounter.js"}
        assert _pairs_of(conn, "badge") == {"src/counter/ui/Badge.vue"}

    def test_boilerplate_is_not_newly_held_beside_annotated_files(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        """A package facade the backstop calls boilerplate does not become a
        pair of an annotated node: the backstop says the document need not
        describe it, so pairing it would add a claim nobody made."""
        _node(conn, "widgets", "src/widgets/", "widgets.md")
        _code_file(conn, project, "src/widgets/alpha.py", annotated_as="widgets")
        _code_file(conn, project, "src/widgets/__init__.py")
        _code_file(conn, project, "src/widgets/sub/__main__.py")

        assert _pairs_of(conn, "widgets") == {"src/widgets/alpha.py"}

    def test_a_node_with_no_annotation_keeps_every_file_it_owns(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        """The #146 fallback is unchanged: with no annotation of its own, a node
        is held to every file its source owns, whatever those files carry."""
        _node(conn, "counter", "src/counter/", "counter.md")
        _code_file(conn, project, "src/counter/lib/format.js")
        _code_file(conn, project, "src/counter/ui/Badge.vue", annotated_as="badge")

        assert _pairs_of(conn, "counter") == {
            "src/counter/lib/format.js",
            "src/counter/ui/Badge.vue",
        }

    def test_a_file_a_nested_node_owns_stays_with_the_nested_node(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        _node(conn, "site", "site/", "site.md")
        _node(conn, "viewer", "site/theme/viewer/", "viewer.md")
        _code_file(conn, project, "site/theme/index.js", annotated_as="site")
        _code_file(conn, project, "site/theme/app.js")
        _code_file(conn, project, "site/theme/viewer/ui/Viewer.vue")

        assert _pairs_of(conn, "site") == {"site/theme/index.js", "site/theme/app.js"}
        assert _pairs_of(conn, "viewer") == {"site/theme/viewer/ui/Viewer.vue"}


class TestCheckSourceCoverage:
    def test_an_indexed_vue_file_below_the_source_that_no_pair_holds_is_named(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        _node(conn, "counter", "src/counter/", "counter.md")
        _code_file(conn, project, "src/counter/model/useCounter.js", annotated_as="counter")
        _code_file(conn, project, "src/counter/ui/Badge.vue", annotated_as="countr")
        _record_pairs(conn)

        gaps = check_source_coverage(conn, project)

        assert gaps == [
            {
                "ref_id": "counter",
                "doc_path": "counter.md",
                "untracked_files": ["src/counter/ui/Badge.vue"],
            }
        ]

    @pytest.mark.parametrize("suffix", [".js", ".ts", ".jsx", ".tsx", ".vue"])
    def test_every_indexed_language_is_read(
        self, conn: sqlite3.Connection, project: Path, suffix: str
    ) -> None:
        _node(conn, "counter", "src/counter/", "counter.md")
        _code_file(conn, project, "src/counter/model/useCounter.js", annotated_as="counter")
        _code_file(conn, project, f"src/counter/deep/er/orphan{suffix}", annotated_as="nobody")
        _record_pairs(conn)

        gaps = check_source_coverage(conn, project)

        assert [g["untracked_files"] for g in gaps] == [[f"src/counter/deep/er/orphan{suffix}"]]

    def test_every_file_of_a_partly_annotated_node_is_held_so_nothing_is_named(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        _node(conn, "counter", "src/counter/", "counter.md")
        _code_file(conn, project, "src/counter/model/useCounter.js", annotated_as="counter")
        _code_file(conn, project, "src/counter/lib/format.js")
        _code_file(conn, project, "src/counter/ui/Counter.vue")
        _record_pairs(conn)

        assert check_source_coverage(conn, project) == []

    def test_a_file_a_nested_node_owns_is_not_named_under_its_container(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        _node(conn, "site", "site/", "site.md")
        _node(conn, "viewer", "site/theme/viewer/", None)
        _code_file(conn, project, "site/theme/index.js", annotated_as="site")
        _code_file(conn, project, "site/theme/viewer/ui/Viewer.vue")
        _record_pairs(conn)

        assert check_source_coverage(conn, project) == []
