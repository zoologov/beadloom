"""Guard: the TUI presentation layer must not touch raw SQLite.

S2 (#122) closes the presentation->SQLite leak: ``tui`` reads route through the
``application.graph_reads`` facade (which wraps ``infrastructure.repository``),
never through ``conn.execute()`` or ``import sqlite3`` for queries. This test
statically asserts no ``.execute(`` SQL call survives in the tui package
(the one allowed ``conn.execute`` is the WAL PRAGMA in ``app.py``).
"""

from __future__ import annotations

from pathlib import Path

_TUI_DIR = Path(__file__).resolve().parent.parent / "src" / "beadloom" / "tui"

# The single legitimate raw execute: enabling WAL on the app's own connection.
_ALLOWED_EXECUTE = '.execute("PRAGMA journal_mode=WAL")'


def _py_files() -> list[Path]:
    return sorted(_TUI_DIR.rglob("*.py"))


def test_tui_has_no_sql_execute_calls() -> None:
    offenders: list[str] = []
    for path in _py_files():
        text = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), 1):
            if ".execute(" not in line:
                continue
            if _ALLOWED_EXECUTE in line:
                continue
            offenders.append(f"{path.relative_to(_TUI_DIR)}:{lineno}: {line.strip()}")
    assert not offenders, "Raw SQL execute in tui:\n" + "\n".join(offenders)


def test_tui_does_not_reference_db_tables() -> None:
    # data_providers / widgets must read through the facade, not build SQL.
    # A query against the index references a known table by name — assert no
    # such reference survives in the tui package (prose is not affected).
    table_refs = (
        "FROM nodes",
        "FROM edges",
        "FROM docs",
        "FROM sync_state",
        "FROM code_symbols",
        "INTO nodes",
    )
    offenders: list[str] = []
    for path in _py_files():
        text = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), 1):
            if any(ref in line for ref in table_refs):
                offenders.append(f"{path.relative_to(_TUI_DIR)}:{lineno}: {line.strip()}")
    assert not offenders, "DB table reference in tui:\n" + "\n".join(offenders)
