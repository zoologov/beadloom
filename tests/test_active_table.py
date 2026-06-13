"""Tests for the shared ACTIVE.md bead-status table module (BDL-053 BEAD-01).

Covers the extracted S4 primitives (``split_table_row`` / ``is_separator_cells``
/ ``set_active_table_status`` — behaviour byte-identical to mcp_server's S4) plus
the new pure ``reconcile_active_tables`` core that rewrites a table's Status
cells from injected bd statuses.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.application.active_table import (
    bd_status_to_cell,
    is_separator_cells,
    reconcile_active_tables,
    set_active_table_status,
    split_table_row,
)

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Extracted primitives (S4, behaviour-preserving)
# ---------------------------------------------------------------------------


def test_split_table_row_parses_cells() -> None:
    assert split_table_row("| a | b | c |") == ["a", "b", "c"]


def test_split_table_row_non_table_returns_none() -> None:
    assert split_table_row("not a table") is None
    assert split_table_row("| dangling") is None


def test_is_separator_cells() -> None:
    assert is_separator_cells(["---", ":---:", "---"]) is True
    assert is_separator_cells(["Bead", "Role"]) is False
    assert is_separator_cells([]) is False


def test_set_active_table_status_whole_token_match(tmp_path: Path) -> None:
    p = tmp_path / "ACTIVE.md"
    p.write_text(
        "| Bead | Role | Status |\n"
        "| --- | --- | --- |\n"
        "| beadloom-x.1 | dev | ready |\n"
        "| beadloom-x.10 | dev | ready |\n",
        encoding="utf-8",
    )
    assert set_active_table_status(p, "beadloom-x.1", "✓ done") is True
    text = p.read_text(encoding="utf-8")
    assert "| beadloom-x.1 | dev | ✓ done |" in text
    # x.10 must be untouched (whole-token match, not prefix).
    assert "| beadloom-x.10 | dev | ready |" in text


def test_set_active_table_status_sanitizes_pipes_and_whitespace(tmp_path: Path) -> None:
    p = tmp_path / "ACTIVE.md"
    p.write_text(
        "| Bead | Status |\n| --- | --- |\n| b.1 | ready |\n", encoding="utf-8"
    )
    assert set_active_table_status(p, "b.1", "in\nprogress | now") is True
    assert "| b.1 | in progress / now |" in p.read_text(encoding="utf-8")


def test_set_active_table_status_missing_file_returns_false(tmp_path: Path) -> None:
    assert set_active_table_status(tmp_path / "nope.md", "b.1", "x") is False


# ---------------------------------------------------------------------------
# bd status -> cell map
# ---------------------------------------------------------------------------


def test_bd_status_to_cell_map() -> None:
    assert bd_status_to_cell("closed") == "✓ done"
    assert bd_status_to_cell("in_progress") == "in progress"
    assert bd_status_to_cell("blocked") == "blocked"
    assert bd_status_to_cell("open") == "ready"
    assert bd_status_to_cell("ready") == "ready"


def test_bd_status_to_cell_unknown_returns_none() -> None:
    assert bd_status_to_cell("weird-status") is None


# ---------------------------------------------------------------------------
# reconcile_active_tables — discovery + rewrite
# ---------------------------------------------------------------------------


def _features_dir(root: Path, epic: str) -> Path:
    d = root / ".claude" / "development" / "docs" / "features" / epic
    d.mkdir(parents=True, exist_ok=True)
    return d


def test_reconcile_rewrites_drift_3col(tmp_path: Path) -> None:
    active = _features_dir(tmp_path, "BDL-001") / "ACTIVE.md"
    active.write_text(
        "# Epic\n\n"
        "| Bead | Role | Status |\n"
        "| --- | --- | --- |\n"
        "| b.1 | dev | ready |\n"
        "| b.2 | test | ready |\n",
        encoding="utf-8",
    )
    result = reconcile_active_tables(
        tmp_path, {"b.1": "closed", "b.2": "in_progress"}, epic="BDL-001"
    )
    assert active in result.changed_files
    text = active.read_text(encoding="utf-8")
    assert "| b.1 | dev | ✓ done |" in text
    assert "| b.2 | test | in progress |" in text
    assert len(result.drifted_rows) == 2


def test_reconcile_4col_status_by_header_index(tmp_path: Path) -> None:
    active = _features_dir(tmp_path, "BDL-002") / "ACTIVE.md"
    active.write_text(
        "| Bead | Role | Status | Depends |\n"
        "| --- | --- | --- | --- |\n"
        "| b.1 | dev | ready | - |\n",
        encoding="utf-8",
    )
    result = reconcile_active_tables(tmp_path, {"b.1": "closed"}, epic="BDL-002")
    text = active.read_text(encoding="utf-8")
    # Status column (index 2) rewritten; Depends (index 3) preserved.
    assert "| b.1 | dev | ✓ done | - |" in text
    assert active in result.changed_files


def test_reconcile_preserves_rich_note_when_state_agrees(tmp_path: Path) -> None:
    active = _features_dir(tmp_path, "BDL-003") / "ACTIVE.md"
    active.write_text(
        "| Bead | Role | Status |\n"
        "| --- | --- | --- |\n"
        "| b.1 | review | ✓ done (PASS-WITH-FIXES) |\n",
        encoding="utf-8",
    )
    result = reconcile_active_tables(tmp_path, {"b.1": "closed"}, epic="BDL-003")
    text = active.read_text(encoding="utf-8")
    assert "| b.1 | review | ✓ done (PASS-WITH-FIXES) |" in text
    assert result.changed_files == []
    assert result.drifted_rows == []


def test_reconcile_rewrites_when_state_differs_even_with_note(tmp_path: Path) -> None:
    active = _features_dir(tmp_path, "BDL-004") / "ACTIVE.md"
    active.write_text(
        "| Bead | Role | Status |\n"
        "| --- | --- | --- |\n"
        "| b.1 | dev | in progress (S2 wip) |\n",
        encoding="utf-8",
    )
    reconcile_active_tables(tmp_path, {"b.1": "closed"}, epic="BDL-004")
    text = active.read_text(encoding="utf-8")
    assert "| b.1 | dev | ✓ done |" in text


def test_reconcile_bead_not_in_dict_untouched(tmp_path: Path) -> None:
    active = _features_dir(tmp_path, "BDL-005") / "ACTIVE.md"
    active.write_text(
        "| Bead | Role | Status |\n"
        "| --- | --- | --- |\n"
        "| b.1 | dev | ready |\n"
        "| b.9 | dev | ready |\n",
        encoding="utf-8",
    )
    result = reconcile_active_tables(tmp_path, {"b.1": "closed"}, epic="BDL-005")
    text = active.read_text(encoding="utf-8")
    assert "| b.1 | dev | ✓ done |" in text
    assert "| b.9 | dev | ready |" in text  # untouched
    assert len(result.drifted_rows) == 1


def test_reconcile_unknown_bd_status_leaves_row(tmp_path: Path) -> None:
    active = _features_dir(tmp_path, "BDL-006") / "ACTIVE.md"
    active.write_text(
        "| Bead | Role | Status |\n| --- | --- | --- |\n| b.1 | dev | ready |\n",
        encoding="utf-8",
    )
    result = reconcile_active_tables(tmp_path, {"b.1": "frobnicated"}, epic="BDL-006")
    assert result.changed_files == []
    assert "| b.1 | dev | ready |" in active.read_text(encoding="utf-8")


def test_reconcile_preserves_prose_and_progress_log(tmp_path: Path) -> None:
    active = _features_dir(tmp_path, "BDL-007") / "ACTIVE.md"
    original_tail = (
        "\n## Progress Log\n\n- 2026-06-14 — kicked off\n\n"
        "Some **prose** with a | pipe in it.\n"
    )
    active.write_text(
        "# Title\n\nIntro paragraph.\n\n"
        "| Bead | Role | Status |\n"
        "| --- | --- | --- |\n"
        "| b.1 | dev | ready |\n"
        + original_tail,
        encoding="utf-8",
    )
    reconcile_active_tables(tmp_path, {"b.1": "in_progress"}, epic="BDL-007")
    text = active.read_text(encoding="utf-8")
    assert text.startswith("# Title\n\nIntro paragraph.\n\n")
    assert text.endswith(original_tail)
    assert "| b.1 | dev | in progress |" in text


def test_reconcile_no_table_no_change_no_raise(tmp_path: Path) -> None:
    active = _features_dir(tmp_path, "BDL-008") / "ACTIVE.md"
    active.write_text("# Just prose, no table here.\n", encoding="utf-8")
    result = reconcile_active_tables(tmp_path, {"b.1": "closed"}, epic="BDL-008")
    assert result.changed_files == []
    assert result.drifted_rows == []


def test_reconcile_missing_active_empty_result(tmp_path: Path) -> None:
    _features_dir(tmp_path, "BDL-009")  # dir exists, no ACTIVE.md
    result = reconcile_active_tables(tmp_path, {"b.1": "closed"}, epic="BDL-009")
    assert result.changed_files == []
    assert result.drifted_rows == []


def test_reconcile_scans_all_features_when_no_epic(tmp_path: Path) -> None:
    a1 = _features_dir(tmp_path, "BDL-010") / "ACTIVE.md"
    a2 = _features_dir(tmp_path, "BDL-011") / "ACTIVE.md"
    for a in (a1, a2):
        a.write_text(
            "| Bead | Role | Status |\n| --- | --- | --- |\n| b.1 | dev | ready |\n",
            encoding="utf-8",
        )
    result = reconcile_active_tables(tmp_path, {"b.1": "closed"})
    assert a1 in result.changed_files
    assert a2 in result.changed_files


def test_reconcile_idempotent(tmp_path: Path) -> None:
    active = _features_dir(tmp_path, "BDL-012") / "ACTIVE.md"
    active.write_text(
        "| Bead | Role | Status |\n| --- | --- | --- |\n| b.1 | dev | ready |\n",
        encoding="utf-8",
    )
    statuses = {"b.1": "closed"}
    reconcile_active_tables(tmp_path, statuses, epic="BDL-012")
    second = reconcile_active_tables(tmp_path, statuses, epic="BDL-012")
    assert second.changed_files == []
    assert second.drifted_rows == []
