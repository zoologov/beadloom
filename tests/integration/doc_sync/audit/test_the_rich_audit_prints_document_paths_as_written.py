"""The Rich ``docs audit`` prints a document's path as it is named.

``beadloom-2mj3.19``: the audit passed each document path to Rich as markup, so a folder
or file named in brackets — a Next.js route such as ``docs/app/[slug]/`` — lost that part
of its path.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from click.testing import CliRunner

from beadloom.infrastructure.db import create_schema, open_db
from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def _project_with_a_bracketed_document(tmp_path: Path) -> Path:
    project = tmp_path / "proj"
    (project / ".beadloom").mkdir(parents=True)
    (project / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "3.0.0"\n', encoding="utf-8"
    )
    route = project / "docs" / "app" / "[slug]"
    route.mkdir(parents=True)
    (route / "[draft].md").write_text(
        "# Route\n\nDemo v2.0.0 is the current release.\n", encoding="utf-8"
    )
    conn = open_db(project / ".beadloom" / "beadloom.db")
    create_schema(conn)
    conn.close()
    return project


def test_a_bracketed_document_path_is_printed_as_written(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("COLUMNS", "200")
    project = _project_with_a_bracketed_document(tmp_path)

    result = CliRunner().invoke(main, ["docs", "audit", "--project", str(project)])

    assert result.exception is None, result.output
    assert "docs/app/[slug]/[draft].md:3" in result.output
