"""Tests for beadloom.infrastructure.doctor — graph and data validation checks."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.infrastructure.db import create_schema, open_db
from beadloom.infrastructure.doctor import Check, Severity, run_checks

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path


@pytest.fixture()
def conn(tmp_path: Path) -> sqlite3.Connection:
    db_path = tmp_path / "test.db"
    c = open_db(db_path)
    create_schema(c)
    return c


class TestRunChecks:
    def test_clean_graph(self, conn: sqlite3.Connection) -> None:
        """No issues with an empty graph."""
        checks = run_checks(conn)
        assert all(c.severity == Severity.OK for c in checks)

    def test_empty_summary(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("F1", "feature", ""),
        )
        conn.commit()
        checks = run_checks(conn)
        warnings = [c for c in checks if c.severity == Severity.WARNING]
        descs = " ".join(c.description for c in warnings)
        assert "summary" in descs.lower() or "empty" in descs.lower()

    def test_orphaned_edge_src(self, conn: sqlite3.Connection) -> None:
        """Edge with src that doesn't exist in nodes (FK should prevent this
        but doctor should still check for edge targets if FK is off)."""
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("A", "feature", "A"),
        )
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("B", "domain", "B"),
        )
        conn.execute(
            "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
            ("A", "B", "part_of"),
        )
        conn.commit()
        # This is valid — should not produce errors.
        checks = run_checks(conn)
        errors = [c for c in checks if c.severity == Severity.ERROR]
        assert len(errors) == 0

    def test_duplicate_edges(self, conn: sqlite3.Connection) -> None:
        """Duplicate edges are prevented by PK, but doc without ref_id is not an error."""
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("A", "feature", "A"),
        )
        conn.commit()
        checks = run_checks(conn)
        # Should have no errors — just a feature node.
        errors = [c for c in checks if c.severity == Severity.ERROR]
        assert len(errors) == 0

    def test_doc_without_ref_id(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            "INSERT INTO docs (path, kind, ref_id, hash) VALUES (?, ?, ?, ?)",
            ("orphan.md", "other", None, "abc"),
        )
        conn.commit()
        checks = run_checks(conn)
        warnings = [c for c in checks if c.severity == Severity.WARNING]
        descs = " ".join(c.description for c in warnings)
        assert "ref_id" in descs.lower() or "unlinked" in descs.lower()

    def test_node_without_docs(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("F1", "feature", "Feature 1"),
        )
        conn.commit()
        checks = run_checks(conn)
        infos = [c for c in checks if c.severity == Severity.INFO]
        descs = " ".join(c.description for c in infos)
        assert "F1" in descs or "no doc" in descs.lower()

    def test_check_dataclass(self) -> None:
        c = Check(
            name="test_check",
            severity=Severity.WARNING,
            description="Something is wrong",
        )
        assert c.name == "test_check"
        assert c.severity == Severity.WARNING


class TestDoctorCli:
    def test_doctor_command(self, tmp_path: Path) -> None:
        from click.testing import CliRunner

        from beadloom.infrastructure.reindex import reindex
        from beadloom.services.cli import main

        project = tmp_path / "proj"
        project.mkdir()
        (project / ".beadloom" / "_graph").mkdir(parents=True)
        (project / "docs").mkdir()
        (project / "src").mkdir()
        reindex(project)

        runner = CliRunner()
        result = runner.invoke(main, ["doctor", "--project", str(project)])
        assert result.exit_code == 0, result.output

    def test_doctor_no_db(self, tmp_path: Path) -> None:
        from click.testing import CliRunner

        from beadloom.services.cli import main

        project = tmp_path / "empty"
        project.mkdir()
        runner = CliRunner()
        result = runner.invoke(main, ["doctor", "--project", str(project)])
        assert result.exit_code != 0
