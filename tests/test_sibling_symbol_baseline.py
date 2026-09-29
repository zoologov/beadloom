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
from tests.support.one_node_two_files import (
    by_code_path,
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


class TestPerFileSymbolsHash:
    """The staleness fact is computed at the granularity of the thing that changed."""

    def test_file_scoped_hash_differs_from_node_hash(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        one_node_two_files(conn, project)
        node = _compute_symbols_hash(conn, "D1")
        alpha = _compute_symbols_hash(conn, "D1", file_path="src/alpha.py")
        beta = _compute_symbols_hash(conn, "D1", file_path="src/beta.py")
        assert alpha != node
        assert beta != node
        assert alpha != beta

    def test_file_scoped_hash_moves_only_for_the_file_that_moved(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        one_node_two_files(conn, project)
        before_alpha = _compute_symbols_hash(conn, "D1", file_path="src/alpha.py")
        before_beta = _compute_symbols_hash(conn, "D1", file_path="src/beta.py")
        move_alpha_symbols(conn, project)
        assert _compute_symbols_hash(conn, "D1", file_path="src/alpha.py") != before_alpha
        assert _compute_symbols_hash(conn, "D1", file_path="src/beta.py") == before_beta

    def test_unannotated_file_has_no_file_scoped_fact(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        """An empty string means "no symbols under this ref in this file"."""
        one_node_two_files(conn, project)
        assert _compute_symbols_hash(conn, "D1", file_path="src/nowhere.py") == ""


class TestSiblingVerdict:
    """Three states, three words: stale, unverified, ok."""

    def test_the_file_that_moved_is_stale(self, conn: sqlite3.Connection, project: Path) -> None:
        one_node_two_files(conn, project)
        record_baseline(conn, project)
        move_alpha_symbols(conn, project)
        by_path = by_code_path(check_sync(conn, project))
        assert by_path["src/alpha.py"]["status"] == STATUS_STALE

    def test_the_sibling_is_not_called_stale(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        one_node_two_files(conn, project)
        record_baseline(conn, project)
        move_alpha_symbols(conn, project)
        by_path = by_code_path(check_sync(conn, project))
        sibling = by_path["src/beta.py"]
        assert sibling["status"] == STATUS_UNVERIFIED
        assert sibling["reason"] == REASON_SIBLING_SYMBOLS_CHANGED

    def test_the_sibling_names_the_file_that_moved(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        """The remedy is to look at alpha, so the row has to say `alpha`."""
        one_node_two_files(conn, project)
        record_baseline(conn, project)
        move_alpha_symbols(conn, project)
        by_path = by_code_path(check_sync(conn, project))
        assert "alpha.py" in str(by_path["src/beta.py"].get("details", ""))
        assert "beta.py" not in str(by_path["src/beta.py"].get("details", ""))

    def test_the_sibling_is_not_written_to_the_db_as_ok(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        """A follower must not be laundered into a fresh baseline by the check."""
        one_node_two_files(conn, project)
        record_baseline(conn, project)
        move_alpha_symbols(conn, project)
        check_sync(conn, project)
        row = conn.execute(
            "SELECT status FROM sync_state WHERE code_path = 'src/beta.py'"
        ).fetchone()
        assert row["status"] == STATUS_UNVERIFIED

    def test_nothing_moved_stays_ok(self, conn: sqlite3.Connection, project: Path) -> None:
        one_node_two_files(conn, project)
        record_baseline(conn, project)
        assert {str(r["status"]) for r in check_sync(conn, project)} == {"ok"}

    def test_a_row_without_a_file_baseline_still_reports_stale(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        """A pre-upgrade row has no file-level fact, so the node-level one stands.

        Under-reporting on an un-reindexed database would be the one failure
        mode worse than the noise this bead removes.
        """
        one_node_two_files(conn, project)
        record_baseline(conn, project, per_file=False)
        move_alpha_symbols(conn, project)
        by_path = by_code_path(check_sync(conn, project))
        assert by_path["src/beta.py"]["status"] == STATUS_STALE
        assert by_path["src/beta.py"]["reason"] == "symbols_changed"


class TestAttestationWritesTheFileFact:
    """`sync-update` records each pair's OWN file hash, not the node's."""

    def test_mark_synced_records_the_file_fact(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        one_node_two_files(conn, project)
        record_baseline(conn, project, per_file=False)
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
        one_node_two_files(conn, project)
        record_baseline(conn, project, per_file=False)
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
        one_node_two_files(conn, project)
        record_baseline(conn, project)
        move_alpha_symbols(conn, project)
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
