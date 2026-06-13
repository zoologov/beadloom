"""Hardening tests for the ACTIVE.md reconcile core (BDL-053 BEAD-03).

Fills gaps left by ``test_active_table.py``: the fail-safe OSError branches, the
``open + blocker -> blocked`` / plain-``open -> ready`` reconcile matrix, the
byte-level preservation of non-status columns + surrounding prose, and the
proof that the moved S4 primitives still back ``mcp_server`` via its re-export
aliases. These assert PUBLIC behaviour (file contents, return values) — never
private attributes. ``bd`` is never touched here (pure core).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.application.active_table import (
    bd_status_to_cell,
    reconcile_active_tables,
    set_active_table_status,
)

if TYPE_CHECKING:
    from pathlib import Path


def _features_dir(root: Path, epic: str) -> Path:
    d = root / ".claude" / "development" / "docs" / "features" / epic
    d.mkdir(parents=True, exist_ok=True)
    return d


# ---------------------------------------------------------------------------
# bd status -> cell : the blocked / ready reconcile matrix (parametrized)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("bd_status", "expected_cell"),
    [
        ("closed", "✓ done"),
        ("in_progress", "in progress"),
        ("blocked", "blocked"),
        ("open", "ready"),
        ("ready", "ready"),
    ],
)
def test_reconcile_writes_mapped_cell_for_each_status(
    tmp_path: Path, bd_status: str, expected_cell: str
) -> None:
    active = _features_dir(tmp_path, "MX") / "ACTIVE.md"
    active.write_text(
        "| Bead | Role | Status |\n| --- | --- | --- |\n| b.1 | dev | xxx |\n",
        encoding="utf-8",
    )
    reconcile_active_tables(tmp_path, {"b.1": bd_status}, epic="MX")
    assert f"| b.1 | dev | {expected_cell} |" in active.read_text(encoding="utf-8")


def test_reconcile_blocked_status_renders_blocked_cell(tmp_path: Path) -> None:
    # The caller (cli) injects "blocked" for an open bead w/ an open blocker;
    # reconcile must render the "blocked" cell verbatim from that token.
    active = _features_dir(tmp_path, "BLK") / "ACTIVE.md"
    active.write_text(
        "| Bead | Role | Status |\n| --- | --- | --- |\n| b.2 | test | ready |\n",
        encoding="utf-8",
    )
    result = reconcile_active_tables(tmp_path, {"b.2": "blocked"}, epic="BLK")
    assert "| b.2 | test | blocked |" in active.read_text(encoding="utf-8")
    assert len(result.drifted_rows) == 1


def test_reconcile_plain_open_becomes_ready(tmp_path: Path) -> None:
    active = _features_dir(tmp_path, "OPN") / "ACTIVE.md"
    active.write_text(
        "| Bead | Role | Status |\n| --- | --- | --- |\n| b.3 | dev | blocked |\n",
        encoding="utf-8",
    )
    reconcile_active_tables(tmp_path, {"b.3": "open"}, epic="OPN")
    assert "| b.3 | dev | ready |" in active.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# byte-level preservation of everything except the touched status cell
# ---------------------------------------------------------------------------


def test_reconcile_4col_depends_column_byte_preserved(tmp_path: Path) -> None:
    active = _features_dir(tmp_path, "DEP") / "ACTIVE.md"
    active.write_text(
        "| Bead | Role | Status | Depends |\n"
        "| --- | --- | --- | --- |\n"
        "| b.1 | dev | ready | b.0, b.9 |\n",
        encoding="utf-8",
    )
    reconcile_active_tables(tmp_path, {"b.1": "closed"}, epic="DEP")
    # The Depends cell content (incl. its comma list) survives verbatim.
    assert "| b.1 | dev | ✓ done | b.0, b.9 |" in active.read_text(encoding="utf-8")


def test_reconcile_leaves_non_status_columns_unrelated_rows_untouched(
    tmp_path: Path,
) -> None:
    active = _features_dir(tmp_path, "MULTI") / "ACTIVE.md"
    original = (
        "# Heading\n\nIntro prose with a | pipe.\n\n"
        "| Bead | Role | Status | Depends |\n"
        "| --- | --- | --- | --- |\n"
        "| b.1 | dev | ready | - |\n"
        "| b.2 | review | in progress (wip) | b.1 |\n"
        "\n## Progress Log\n\n- note one\n- note two\n"
    )
    active.write_text(original, encoding="utf-8")
    # Only b.1 drifts (closed); b.2 stays in_progress -> unchanged.
    reconcile_active_tables(tmp_path, {"b.1": "closed", "b.2": "in_progress"}, epic="MULTI")
    text = active.read_text(encoding="utf-8")
    assert "| b.1 | dev | ✓ done | - |" in text
    assert "| b.2 | review | in progress (wip) | b.1 |" in text  # note preserved
    assert text.startswith("# Heading\n\nIntro prose with a | pipe.\n\n")
    assert text.endswith("\n## Progress Log\n\n- note one\n- note two\n")


def test_reconcile_no_trailing_newline_preserved(tmp_path: Path) -> None:
    active = _features_dir(tmp_path, "NONL") / "ACTIVE.md"
    # Last row has no trailing newline — the rewrite must not add one.
    active.write_text(
        "| Bead | Role | Status |\n| --- | --- | --- |\n| b.1 | dev | ready |",
        encoding="utf-8",
    )
    reconcile_active_tables(tmp_path, {"b.1": "closed"}, epic="NONL")
    text = active.read_text(encoding="utf-8")
    assert text.endswith("| b.1 | dev | ✓ done |")
    assert not text.endswith("\n")


# ---------------------------------------------------------------------------
# fail-safe: never raise, never corrupt
# ---------------------------------------------------------------------------


def test_reconcile_unreadable_file_is_skipped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    active = _features_dir(tmp_path, "OSERR") / "ACTIVE.md"
    active.write_text(
        "| Bead | Role | Status |\n| --- | --- | --- |\n| b.1 | dev | ready |\n",
        encoding="utf-8",
    )

    def boom(self: Path, *a: object, **k: object) -> str:
        raise OSError("unreadable")

    monkeypatch.setattr("pathlib.Path.read_text", boom)
    result = reconcile_active_tables(tmp_path, {"b.1": "closed"}, epic="OSERR")
    assert result.changed_files == []
    assert result.drifted_rows == []


def test_reconcile_unwritable_file_does_not_corrupt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    active = _features_dir(tmp_path, "WRERR") / "ACTIVE.md"
    before = "| Bead | Role | Status |\n| --- | --- | --- |\n| b.1 | dev | ready |\n"
    active.write_text(before, encoding="utf-8")

    def boom(self: Path, *a: object, **k: object) -> int:
        raise OSError("read-only fs")

    monkeypatch.setattr("pathlib.Path.write_text", boom)
    result = reconcile_active_tables(tmp_path, {"b.1": "closed"}, epic="WRERR")
    # The write raised -> not recorded as changed, file content intact.
    assert result.changed_files == []
    assert active.read_text(encoding="utf-8") == before


def test_reconcile_header_without_separator_is_ignored(tmp_path: Path) -> None:
    # A 'Bead' header NOT followed by a separator row is not a real table.
    active = _features_dir(tmp_path, "NOSEP") / "ACTIVE.md"
    active.write_text(
        "| Bead | Role | Status |\n| b.1 | dev | ready |\n",
        encoding="utf-8",
    )
    result = reconcile_active_tables(tmp_path, {"b.1": "closed"}, epic="NOSEP")
    assert result.changed_files == []
    assert "| b.1 | dev | ready |" in active.read_text(encoding="utf-8")


def test_reconcile_table_without_status_column_ignored(tmp_path: Path) -> None:
    # Header starts with 'Bead' + separator, but has no 'Status' column.
    active = _features_dir(tmp_path, "NOSTAT") / "ACTIVE.md"
    active.write_text(
        "| Bead | Role | Note |\n| --- | --- | --- |\n| b.1 | dev | hi |\n",
        encoding="utf-8",
    )
    result = reconcile_active_tables(tmp_path, {"b.1": "closed"}, epic="NOSTAT")
    assert result.changed_files == []
    assert "| b.1 | dev | hi |" in active.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# set_active_table_status fail-safe branches (S4 primitive)
# ---------------------------------------------------------------------------


def test_set_status_no_matching_row_returns_false(tmp_path: Path) -> None:
    p = tmp_path / "ACTIVE.md"
    p.write_text(
        "| Bead | Role | Status |\n| --- | --- | --- |\n| b.1 | dev | ready |\n",
        encoding="utf-8",
    )
    before = p.read_text(encoding="utf-8")
    assert set_active_table_status(p, "absent.99", "✓ done") is False
    assert p.read_text(encoding="utf-8") == before  # untouched


def test_set_status_unwritable_returns_false(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    p = tmp_path / "ACTIVE.md"
    p.write_text(
        "| Bead | Role | Status |\n| --- | --- | --- |\n| b.1 | dev | ready |\n",
        encoding="utf-8",
    )

    def boom(self: Path, *a: object, **k: object) -> int:
        raise OSError("read-only")

    monkeypatch.setattr("pathlib.Path.write_text", boom)
    assert set_active_table_status(p, "b.1", "✓ done") is False


# ---------------------------------------------------------------------------
# extraction integrity: the moved S4 primitives still back mcp_server
# ---------------------------------------------------------------------------


def test_mcp_server_reexport_aliases_are_the_moved_primitives() -> None:
    import beadloom.services.mcp_server as mcp

    assert mcp._set_active_table_status is set_active_table_status
    assert mcp._split_table_row.__module__ == "beadloom.application.active_table"
    assert mcp._is_separator_cells.__module__ == "beadloom.application.active_table"


def test_mcp_set_status_alias_flips_active_table_row(tmp_path: Path) -> None:
    # Spot-check the alias still mutates an ACTIVE.md table identically.
    import beadloom.services.mcp_server as mcp

    p = tmp_path / "ACTIVE.md"
    p.write_text(
        "| Bead | Role | Status |\n| --- | --- | --- |\n| z.1 | dev | ready |\n",
        encoding="utf-8",
    )
    assert mcp._set_active_table_status(p, "z.1", "✓ done") is True
    assert "| z.1 | dev | ✓ done |" in p.read_text(encoding="utf-8")


def test_bd_status_to_cell_is_total_over_known_tokens() -> None:
    # Guards the documented contract used by both the cli + reconcile.
    for token in ("closed", "in_progress", "blocked", "open", "ready"):
        assert bd_status_to_cell(token) is not None
    assert bd_status_to_cell("") is None
