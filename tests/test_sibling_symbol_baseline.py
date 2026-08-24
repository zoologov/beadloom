"""A pair whose OWN file did not move says so — BDL-UX #182 / #133, bead `.78`.

``symbols_hash`` is stored per pair but was COMPUTED per node, so one changed
file marked every pair the node owns ``stale/symbols_changed``. The followers
could not be revised — nothing about their files changed — so the only action
the tool offered was bulk re-attestation, which is exactly the hazard #163 was
filed for.

These tests pin the repair: the pair whose own file moved keeps the word
``stale``, and the pairs that merely share its node say ``unverified`` with the
reason ``sibling_symbols_changed`` and NAME the file that actually moved.
"""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

import pytest

from beadloom.doc_sync.engine import (
    REASON_SIBLING_SYMBOLS_CHANGED,
    STATUS_STALE,
    STATUS_UNVERIFIED,
    _compute_symbols_hash,
    check_sync,
    mark_synced,
    mark_synced_by_ref,
)
from beadloom.infrastructure.db import create_schema, ensure_schema_migrations, open_db

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path


def _hash(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


def _code(ref: str, name: str) -> str:
    return f"# beadloom:feature={ref}\ndef {name}():\n    pass\n"


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


def _one_node_two_files(conn: sqlite3.Connection, project: Path) -> None:
    """A single node whose ONE document is paired with TWO code files.

    This is the shape #182 was measured on: `application/README.md` against
    every module of the domain.
    """
    doc = "# Domain\n\nWhat the domain does.\n"
    (project / "docs" / "readme.md").write_text(doc)
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
        ("D1", "domain", "Domain 1"),
    )
    conn.execute(
        "INSERT INTO docs (path, kind, ref_id, hash) VALUES (?, ?, ?, ?)",
        ("readme.md", "domain", "D1", _hash(doc)),
    )
    for name in ("alpha", "beta"):
        body = _code("D1", name)
        (project / "src" / f"{name}.py").write_text(body)
        conn.execute(
            "INSERT INTO code_symbols "
            "(file_path, symbol_name, kind, line_start, line_end, annotations, file_hash) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                f"src/{name}.py",
                name,
                "function",
                1,
                3,
                json.dumps({"feature": "D1"}),
                _hash(body),
            ),
        )
    conn.commit()


def _baseline(conn: sqlite3.Connection, project: Path, *, per_file: bool = True) -> None:
    """Record the sync baseline for both pairs, as a reindex would."""
    node_hash = _compute_symbols_hash(conn, "D1")
    for name in ("alpha", "beta"):
        code_path = f"src/{name}.py"
        file_hash = _compute_symbols_hash(conn, "D1", file_path=code_path) if per_file else ""
        conn.execute(
            "INSERT INTO sync_state "
            "(doc_path, code_path, ref_id, code_hash_at_sync, doc_hash_at_sync, "
            "synced_at, status, symbols_hash, file_symbols_hash) "
            "VALUES (?, ?, ?, ?, ?, ?, 'ok', ?, ?)",
            (
                "readme.md",
                code_path,
                "D1",
                _hash((project / "src" / f"{name}.py").read_text()),
                _hash((project / "docs" / "readme.md").read_text()),
                "2025-01-01",
                node_hash,
                file_hash,
            ),
        )
    conn.commit()


def _move_alpha_symbols(conn: sqlite3.Connection, project: Path) -> None:
    """Rename alpha's symbol AND rewrite its file, as a real edit would."""
    body = "# beadloom:feature=D1\ndef alpha_renamed():\n    pass\n"
    (project / "src" / "alpha.py").write_text(body)
    conn.execute(
        "UPDATE code_symbols SET symbol_name = ?, file_hash = ? WHERE file_path = ?",
        ("alpha_renamed", _hash(body), "src/alpha.py"),
    )
    conn.commit()


def _by_code_path(results: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    return {str(r["code_path"]): r for r in results if r.get("code_path")}


class TestPerFileSymbolsHash:
    """The staleness fact is computed at the granularity of the thing that changed."""

    def test_file_scoped_hash_differs_from_node_hash(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        _one_node_two_files(conn, project)
        node = _compute_symbols_hash(conn, "D1")
        alpha = _compute_symbols_hash(conn, "D1", file_path="src/alpha.py")
        beta = _compute_symbols_hash(conn, "D1", file_path="src/beta.py")
        assert alpha != node
        assert beta != node
        assert alpha != beta

    def test_file_scoped_hash_moves_only_for_the_file_that_moved(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        _one_node_two_files(conn, project)
        before_alpha = _compute_symbols_hash(conn, "D1", file_path="src/alpha.py")
        before_beta = _compute_symbols_hash(conn, "D1", file_path="src/beta.py")
        _move_alpha_symbols(conn, project)
        assert _compute_symbols_hash(conn, "D1", file_path="src/alpha.py") != before_alpha
        assert _compute_symbols_hash(conn, "D1", file_path="src/beta.py") == before_beta

    def test_unannotated_file_has_no_file_scoped_fact(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        """An empty string means "no symbols under this ref in this file"."""
        _one_node_two_files(conn, project)
        assert _compute_symbols_hash(conn, "D1", file_path="src/nowhere.py") == ""


class TestSiblingVerdict:
    """Three states, three words: stale, unverified, ok."""

    def test_the_file_that_moved_is_stale(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        _one_node_two_files(conn, project)
        _baseline(conn, project)
        _move_alpha_symbols(conn, project)
        by_path = _by_code_path(check_sync(conn, project))
        assert by_path["src/alpha.py"]["status"] == STATUS_STALE

    def test_the_sibling_is_not_called_stale(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        _one_node_two_files(conn, project)
        _baseline(conn, project)
        _move_alpha_symbols(conn, project)
        by_path = _by_code_path(check_sync(conn, project))
        sibling = by_path["src/beta.py"]
        assert sibling["status"] == STATUS_UNVERIFIED
        assert sibling["reason"] == REASON_SIBLING_SYMBOLS_CHANGED

    def test_the_sibling_names_the_file_that_moved(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        """The remedy is to look at alpha, so the row has to say `alpha`."""
        _one_node_two_files(conn, project)
        _baseline(conn, project)
        _move_alpha_symbols(conn, project)
        by_path = _by_code_path(check_sync(conn, project))
        assert "alpha.py" in str(by_path["src/beta.py"].get("details", ""))
        assert "beta.py" not in str(by_path["src/beta.py"].get("details", ""))

    def test_the_sibling_is_not_written_to_the_db_as_ok(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        """A follower must not be laundered into a fresh baseline by the check."""
        _one_node_two_files(conn, project)
        _baseline(conn, project)
        _move_alpha_symbols(conn, project)
        check_sync(conn, project)
        row = conn.execute(
            "SELECT status FROM sync_state WHERE code_path = 'src/beta.py'"
        ).fetchone()
        assert row["status"] == STATUS_UNVERIFIED

    def test_nothing_moved_stays_ok(self, conn: sqlite3.Connection, project: Path) -> None:
        _one_node_two_files(conn, project)
        _baseline(conn, project)
        assert {str(r["status"]) for r in check_sync(conn, project)} == {"ok"}

    def test_a_row_without_a_file_baseline_still_reports_stale(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        """A pre-upgrade row has no file-level fact, so the node-level one stands.

        Under-reporting on an un-reindexed database would be the one failure
        mode worse than the noise this bead removes.
        """
        _one_node_two_files(conn, project)
        _baseline(conn, project, per_file=False)
        _move_alpha_symbols(conn, project)
        by_path = _by_code_path(check_sync(conn, project))
        assert by_path["src/beta.py"]["status"] == STATUS_STALE
        assert by_path["src/beta.py"]["reason"] == "symbols_changed"


class TestAttestationWritesTheFileFact:
    """`sync-update` records each pair's OWN file hash, not the node's."""

    def test_mark_synced_records_the_file_fact(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        _one_node_two_files(conn, project)
        _baseline(conn, project, per_file=False)
        mark_synced(conn, "readme.md", "src/beta.py", project)
        row = conn.execute(
            "SELECT file_symbols_hash FROM sync_state WHERE code_path = 'src/beta.py'"
        ).fetchone()
        assert row["file_symbols_hash"] == _compute_symbols_hash(
            conn, "D1", file_path="src/beta.py"
        )

    def test_mark_synced_by_ref_gives_each_pair_its_own_fact(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        _one_node_two_files(conn, project)
        _baseline(conn, project, per_file=False)
        assert mark_synced_by_ref(conn, "D1", project) == 2
        stored = {
            str(r["code_path"]): str(r["file_symbols_hash"])
            for r in conn.execute("SELECT code_path, file_symbols_hash FROM sync_state")
        }
        assert stored["src/alpha.py"] != stored["src/beta.py"]
        assert stored["src/alpha.py"] == _compute_symbols_hash(
            conn, "D1", file_path="src/alpha.py"
        )

    def test_attesting_the_sibling_clears_its_verdict(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        _one_node_two_files(conn, project)
        _baseline(conn, project)
        _move_alpha_symbols(conn, project)
        mark_synced_by_ref(conn, "D1", project)
        assert {str(r["status"]) for r in check_sync(conn, project)} == {"ok"}


class TestMigration:
    """An index built before this column upgrades without a rebuild."""

    def test_migration_adds_the_column(self, project: Path) -> None:
        conn = open_db(project / ".beadloom" / "legacy.db")
        create_schema(conn)
        conn.execute("ALTER TABLE sync_state DROP COLUMN file_symbols_hash")
        conn.commit()
        ensure_schema_migrations(conn)
        columns = {r["name"] for r in conn.execute("PRAGMA table_info(sync_state)")}
        assert "file_symbols_hash" in columns


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

        _one_node_two_files(conn, project)
        _build_initial_sync_state(conn)
        assert all(self._pairs_for(conn).values())

    def test_a_rebuild_does_not_invent_a_file_fact_the_pair_never_had(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        from beadloom.application.reindex import _build_initial_sync_state, _SyncPairSnapshot

        _one_node_two_files(conn, project)
        _baseline(conn, project, per_file=False)
        node_hash = _compute_symbols_hash(conn, "D1")
        _move_alpha_symbols(conn, project)
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
        by_path = _by_code_path(check_sync(conn, project))
        assert by_path["src/beta.py"]["status"] == STATUS_STALE

    def test_a_file_that_arrived_on_a_carried_node_has_no_file_fact(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        """Its arrival is part of what moved the node hash, so it IS the change."""
        from beadloom.application.reindex import _build_initial_sync_state

        _one_node_two_files(conn, project)
        node_hash = _compute_symbols_hash(conn, "D1")
        body = _code("D1", "gamma")
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
                _hash(body),
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

        _one_node_two_files(conn, project)
        _baseline(conn, project, per_file=False)
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
        _move_alpha_symbols(conn, project)
        by_path = _by_code_path(check_sync(conn, project))
        assert by_path["src/beta.py"]["status"] == STATUS_UNVERIFIED
