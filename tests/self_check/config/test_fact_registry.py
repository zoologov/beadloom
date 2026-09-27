"""Self-checks of this repository's manifest, CI workflows and configuration (BDL-074 A3).

Moved out of ``tests/test_fact_registry.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from beadloom.doc_sync.audit import FactRegistry
from beadloom.infrastructure.db import create_schema, open_db

if TYPE_CHECKING:
    import sqlite3


#: This repository's root — the one project whose own surfaces the audit reports.
BEADLOOM_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    """Create a minimal project directory for fact registry tests."""
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / ".beadloom").mkdir()
    return proj


@pytest.fixture()
def conn(project: Path) -> sqlite3.Connection:
    """Open an in-memory-equivalent test DB with schema."""
    db_path = project / ".beadloom" / "test.db"
    c = open_db(db_path)
    create_schema(c)
    return c


class TestMcpToolCount:
    """The MCP tool count is Beadloom's own surface, so only Beadloom gets it.

    These two tests used to assert the opposite — that ANY project, including a
    bare temporary directory, is handed the running catalog's length. That is
    the defect BDL-062 `.3` removed, and the assertions are inverted here rather
    than deleted so the leak cannot come back unnoticed.
    """

    def test_beadloom_itself_still_reports_the_catalog_length(
        self, conn: sqlite3.Connection
    ) -> None:
        from beadloom.infrastructure.mcp_tools import MCP_TOOL_CATALOG

        fact_set = FactRegistry().collect_set(BEADLOOM_ROOT, conn)
        fact = fact_set.facts["mcp_tool_count"]
        assert fact.value == len(MCP_TOOL_CATALOG)
        assert fact.source == "MCP tool catalog"


class TestCliCommandCount:
    """The CLI command count, likewise, describes the package that provides it."""

    def test_beadloom_itself_still_reports_the_registered_commands(
        self, conn: sqlite3.Connection
    ) -> None:
        import beadloom.services.cli  # noqa: F401  — registers the CLI surface
        from beadloom.infrastructure.surface_registry import get_cli_group

        group = get_cli_group()
        assert group is not None, "the CLI surface must be live for this test"
        fact = FactRegistry().collect_set(BEADLOOM_ROOT, conn).facts["cli_command_count"]
        assert fact.value == FactRegistry._count_click_commands(group)
        assert fact.source == "CLI"
