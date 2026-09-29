"""A reindex rebuilds each pair's file fact only when its provenance matches the node fact's.

``_build_initial_sync_state`` carries a node's symbols hash from the earlier index
or computes it from the tree just indexed, and the per-file hash beside it must
say the same kind of thing (BDL-UX #182 / #133, bead ``.78``). Split out of
``tests/test_sibling_symbol_baseline.py`` (BDL-074 ``beadloom-2mj3.7``); the sync
engine's verdicts over these baselines stayed there.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from beadloom.doc_sync.engine import (
    STATUS_STALE,
    STATUS_UNVERIFIED,
    _compute_symbols_hash,
    check_sync,
)
from beadloom.infrastructure.db import create_schema, open_db
from tests.support.one_node_two_files import (
    annotated_function,
    by_code_path,
    content_hash,
    move_alpha_symbols,
    one_node_two_files,
    record_baseline,
)

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    proj = tmp_path / "proj"
    (proj / "docs").mkdir(parents=True)
    (proj / "src").mkdir(parents=True)
    (proj / ".beadloom").mkdir(parents=True)
    return proj


@pytest.fixture()
def conn(project: Path) -> sqlite3.Connection:
    c = open_db(project / ".beadloom" / "test.db")
    create_schema(c)
    return c


class TestBaselineProvenanceMatches:
    """The file fact's provenance matches the node fact's, or it is not written.

    A node hash CARRIED from an earlier generation beside a file hash COMPUTED
    from the tree just indexed states two incompatible things: something under
    this node moved, and no file moved. Measured on this repository at the first
    reindex after the column was added — 77 pairs read
    ``sibling_symbols_changed`` with nothing named in ``details``, because every
    file baseline had just been fabricated from the post-edit tree. The rule is
    the one BDL-UX #175 already established for the pair hashes: carry it, or do
    not invent it.
    """

    def _pairs_for(self, conn: sqlite3.Connection) -> dict[str, str]:
        return {
            str(r["code_path"]): str(r["file_symbols_hash"] or "")
            for r in conn.execute("SELECT code_path, file_symbols_hash FROM sync_state")
        }

    def test_a_first_build_records_the_file_fact(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        """Nothing is carried, so nothing is contradicted — both facts are fresh."""
        from beadloom.application.reindex import _build_initial_sync_state

        one_node_two_files(conn, project)
        _build_initial_sync_state(conn)
        assert all(self._pairs_for(conn).values())

    def test_a_rebuild_does_not_invent_a_file_fact_the_pair_never_had(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        from beadloom.application.reindex import _build_initial_sync_state, _SyncPairSnapshot

        one_node_two_files(conn, project)
        record_baseline(conn, project, per_file=False)
        node_hash = _compute_symbols_hash(conn, "D1")
        move_alpha_symbols(conn, project)
        conn.execute("DELETE FROM sync_state")
        _build_initial_sync_state(
            conn,
            preserved_symbols={"D1": node_hash},
            preserved_pairs={
                ("readme.md", f"src/{n}.py"): _SyncPairSnapshot(
                    doc_hash_at_last_edit="", code_hash_at_sync="", baseline_source="carried"
                )
                for n in ("alpha", "beta")
            },
        )
        assert set(self._pairs_for(conn).values()) == {""}
        # And therefore the node-level answer still stands, which is what this
        # index reported before the column existed.
        by_path = by_code_path(check_sync(conn, project))
        assert by_path["src/beta.py"]["status"] == STATUS_STALE

    def test_a_file_that_arrived_on_a_carried_node_has_no_file_fact(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        """Its arrival is part of what moved the node hash, so it IS the change."""
        from beadloom.application.reindex import _build_initial_sync_state

        one_node_two_files(conn, project)
        node_hash = _compute_symbols_hash(conn, "D1")
        body = annotated_function("D1", "gamma")
        (project / "src" / "gamma.py").write_text(body)
        conn.execute(
            "INSERT INTO code_symbols "
            "(file_path, symbol_name, kind, line_start, line_end, annotations, file_hash) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "src/gamma.py",
                "gamma",
                "function",
                1,
                3,
                json.dumps({"feature": "D1"}),
                content_hash(body),
            ),
        )
        conn.commit()
        _build_initial_sync_state(conn, preserved_symbols={"D1": node_hash})
        assert self._pairs_for(conn)["src/gamma.py"] == ""

    def test_a_node_not_in_drift_records_its_file_facts_at_once(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        """Nothing is contradicted, so nothing is invented by writing them.

        A carried node hash that still MATCHES the tree is the index already
        saying no file moved. Recording each file's surface then adds no claim,
        and it is what converges the nodes that are not in drift — most of a
        project — on the reindex that adds the column rather than on their first
        storm. Measured on this repository: with the stricter rule, perturbing
        one `application` module left `site-generation`'s 16 untouched pairs
        reading `symbols_changed`, because that node had never been stale and so
        had never been attested.
        """
        from beadloom.application.reindex import _build_initial_sync_state, _SyncPairSnapshot

        one_node_two_files(conn, project)
        record_baseline(conn, project, per_file=False)
        node_hash = _compute_symbols_hash(conn, "D1")
        conn.execute("DELETE FROM sync_state")
        _build_initial_sync_state(
            conn,
            preserved_symbols={"D1": node_hash},
            preserved_pairs={
                ("readme.md", f"src/{n}.py"): _SyncPairSnapshot(
                    doc_hash_at_last_edit="", code_hash_at_sync="", baseline_source="carried"
                )
                for n in ("alpha", "beta")
            },
        )
        assert all(self._pairs_for(conn).values())
        # And the distinction now works on the very next change.
        move_alpha_symbols(conn, project)
        by_path = by_code_path(check_sync(conn, project))
        assert by_path["src/beta.py"]["status"] == STATUS_UNVERIFIED
