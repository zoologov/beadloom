"""Tests for beadloom.search — FTS5 full-text search engine."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from beadloom.infrastructure.db import create_schema, open_db

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def search_conn(tmp_path: Path) -> sqlite3.Connection:
    """Return an in-memory-style conn with schema + sample data + FTS5 populated."""
    db_path = tmp_path / "test.db"
    conn = open_db(db_path)
    create_schema(conn)

    # Insert sample nodes.
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
        ("AUTH-1", "feature", "User authentication and session management"),
    )
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
        ("ROUTING", "domain", "Request routing and URL resolution"),
    )
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
        ("PAY-1", "service", "Payment processing gateway"),
    )

    # Insert docs + chunks for AUTH-1.
    conn.execute(
        "INSERT INTO docs (path, kind, ref_id, hash) VALUES (?, ?, ?, ?)",
        ("auth.md", "feature", "AUTH-1", "abc123"),
    )
    doc_id = conn.execute("SELECT id FROM docs WHERE path = 'auth.md'").fetchone()[0]
    conn.execute(
        "INSERT INTO chunks (doc_id, chunk_index, heading, section, content, node_ref_id) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (doc_id, 0, "Auth", "Overview", "OAuth2 login flow with JWT tokens", "AUTH-1"),
    )
    conn.commit()

    # Populate search index.
    from beadloom.context_oracle.search import populate_search_index

    populate_search_index(conn)
    return conn


# ---------------------------------------------------------------------------
# Unit tests: FTS5 search
# ---------------------------------------------------------------------------


class TestSearchFts5:
    def test_basic_keyword_search(self, search_conn: sqlite3.Connection) -> None:
        from beadloom.context_oracle.search import search_fts5

        results = search_fts5(search_conn, "authentication")
        assert len(results) >= 1
        assert any(r["ref_id"] == "AUTH-1" for r in results)

    def test_search_with_kind_filter(self, search_conn: sqlite3.Connection) -> None:
        from beadloom.context_oracle.search import search_fts5

        results = search_fts5(search_conn, "routing", kind="domain")
        assert all(r["kind"] == "domain" for r in results)
        assert any(r["ref_id"] == "ROUTING" for r in results)

    def test_search_no_results(self, search_conn: sqlite3.Connection) -> None:
        from beadloom.context_oracle.search import search_fts5

        results = search_fts5(search_conn, "zzzznonexistent")
        assert results == []

    def test_search_with_limit(self, search_conn: sqlite3.Connection) -> None:
        from beadloom.context_oracle.search import search_fts5

        results = search_fts5(search_conn, "routing", limit=1)
        assert len(results) <= 1

    def test_search_returns_snippet(self, search_conn: sqlite3.Connection) -> None:
        from beadloom.context_oracle.search import search_fts5

        results = search_fts5(search_conn, "OAuth2")
        assert len(results) >= 1
        # snippet comes from chunk content.
        assert any("snippet" in r for r in results)

    def test_search_empty_query(self, search_conn: sqlite3.Connection) -> None:
        from beadloom.context_oracle.search import search_fts5

        results = search_fts5(search_conn, "")
        assert results == []

    def test_search_content_in_chunks(self, search_conn: sqlite3.Connection) -> None:
        """FTS5 searches chunk content (not just node summary)."""
        from beadloom.context_oracle.search import search_fts5

        results = search_fts5(search_conn, "JWT")
        assert len(results) >= 1
        assert results[0]["ref_id"] == "AUTH-1"

    def test_search_result_has_rank(self, search_conn: sqlite3.Connection) -> None:
        from beadloom.context_oracle.search import search_fts5

        results = search_fts5(search_conn, "payment")
        assert len(results) >= 1
        assert "rank" in results[0]


class TestPopulateSearchIndex:
    def test_populates_all_nodes(self, search_conn: sqlite3.Connection) -> None:
        row = search_conn.execute("SELECT count(*) FROM search_index").fetchone()
        assert row[0] == 3

    def test_rebuild_is_idempotent(self, search_conn: sqlite3.Connection) -> None:
        from beadloom.context_oracle.search import populate_search_index

        # Second populate should replace, not duplicate.
        count = populate_search_index(search_conn)
        assert count == 3
        row = search_conn.execute("SELECT count(*) FROM search_index").fetchone()
        assert row[0] == 3


class TestHasFts5:
    def test_has_fts5_with_data(self, search_conn: sqlite3.Connection) -> None:
        from beadloom.context_oracle.search import has_fts5

        assert has_fts5(search_conn) is True

    def test_has_fts5_empty(self, tmp_path: Path) -> None:
        from beadloom.context_oracle.search import has_fts5

        db_path = tmp_path / "empty.db"
        conn = open_db(db_path)
        create_schema(conn)
        assert has_fts5(conn) is False


class TestEscapeFts5Query:
    def test_basic_words(self) -> None:
        from beadloom.context_oracle.search import _escape_fts5_query

        assert _escape_fts5_query("hello world") == '"hello" "world"'

    def test_empty_string(self) -> None:
        from beadloom.context_oracle.search import _escape_fts5_query

        assert _escape_fts5_query("") == ""

    def test_special_characters_escaped(self) -> None:
        from beadloom.context_oracle.search import _escape_fts5_query

        result = _escape_fts5_query("foo:bar*")
        assert '"foo:bar*"' in result


# ---------------------------------------------------------------------------
# CLI search command tests
# ---------------------------------------------------------------------------


class TestSearchCLI:
    @staticmethod
    def _setup_project(tmp_path: Path) -> Path:
        """Create a project with reindexed data for CLI testing."""
        import yaml

        proj = tmp_path / "proj"
        proj.mkdir()

        graph_dir = proj / ".beadloom" / "_graph"
        graph_dir.mkdir(parents=True)
        (graph_dir / "graph.yml").write_text(
            yaml.dump(
                {
                    "nodes": [
                        {
                            "ref_id": "AUTH",
                            "kind": "feature",
                            "summary": "Authentication module",
                            "docs": ["docs/auth.md"],
                        },
                    ],
                }
            )
        )

        docs_dir = proj / "docs"
        docs_dir.mkdir()
        (docs_dir / "auth.md").write_text("## Auth\n\nLogin with OAuth2.\n")

        from beadloom.infrastructure.reindex import reindex

        reindex(proj)
        return proj

    def test_search_finds_results(self, tmp_path: Path) -> None:
        from click.testing import CliRunner

        from beadloom.services.cli import main

        project = self._setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["search", "authentication", "--project", str(project)])
        assert result.exit_code == 0, result.output
        assert "AUTH" in result.output

    def test_search_json_output(self, tmp_path: Path) -> None:
        from click.testing import CliRunner

        from beadloom.services.cli import main

        project = self._setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["search", "OAuth2", "--json", "--project", str(project)])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert isinstance(data, list)

    def test_search_no_results(self, tmp_path: Path) -> None:
        from click.testing import CliRunner

        from beadloom.services.cli import main

        project = self._setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["search", "zzzznothing", "--project", str(project)])
        assert result.exit_code == 0
        assert "No results" in result.output

    def test_search_with_kind(self, tmp_path: Path) -> None:
        from click.testing import CliRunner

        from beadloom.services.cli import main

        project = self._setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main, ["search", "authentication", "--kind", "feature", "--project", str(project)]
        )
        assert result.exit_code == 0

    def test_search_no_db(self, tmp_path: Path) -> None:
        from click.testing import CliRunner

        from beadloom.services.cli import main

        project = tmp_path / "empty"
        project.mkdir()
        runner = CliRunner()
        result = runner.invoke(main, ["search", "test", "--project", str(project)])
        assert result.exit_code != 0
