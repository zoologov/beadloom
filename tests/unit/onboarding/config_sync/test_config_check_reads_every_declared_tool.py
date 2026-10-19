"""`config-check` over the tools a flow declares (BDL-083 S2h, RFC D13, BDL-UX #356).

Measured on 9.0.0 at `0f2fa2ec`: on a project composed for Cursor alone,
`config-check` warned five times that `.claude/agents/<role>.md` was missing, a
file `setup-agentic-flow` never writes for Cursor, and on a project composed for
both tools it compared no layer across them. The canonical file set now follows
`tools:`, and a tool whose files carry fewer layers than another declared tool's
is an error that names the tool and the layers.
"""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

from beadloom.onboarding.agentic_flow_setup import scaffold
from beadloom.onboarding.composer import CLAUDE_ARTIFACT_NAME, PROJECT_FLOW_DIRNAME
from beadloom.onboarding.config_sync import apply_config_fixes, check_config_drift
from beadloom.onboarding.flow_config import FlowConfig, persist_flow_config
from beadloom.onboarding.role_adapters import generate_adapters
from beadloom.onboarding.tool_reach import cursor_command_rule_relpath, cursor_core_rule_relpath

if TYPE_CHECKING:
    from pathlib import Path

    from beadloom.onboarding.config_sync import ConfigDrift

_DOD = "## Definition of Done\n\nEvery bead runs the full check and quotes each exit code.\n"


def _composed(tmp_path: Path, *tools: str) -> Path:
    root = tmp_path / "acme"
    root.mkdir()
    (root / "pyproject.toml").write_text(
        '[project]\nname = "acme"\nversion = "0.1.0"\n', encoding="utf-8"
    )
    fragment = root / PROJECT_FLOW_DIRNAME / "claude" / f"{CLAUDE_ARTIFACT_NAME}.md"
    fragment.parent.mkdir(parents=True)
    fragment.write_text(_DOD, encoding="utf-8")
    config = FlowConfig(tools=tools, architecture="ddd", stack=("python",))
    persist_flow_config(root, config)
    generate_adapters(config, root)
    scaffold(root, include_agents=False, config=config)
    return root


def _drifts(root: Path) -> list[ConfigDrift]:
    return check_config_drift(root, sqlite3.connect(":memory:"))


def _blocking(root: Path) -> list[ConfigDrift]:
    return [d for d in _drifts(root) if d.severity == "error"]


class TestACursorOnlyProject:
    def test_is_not_told_to_restore_claude_role_files(self, tmp_path: Path) -> None:
        root = _composed(tmp_path, "cursor")
        assert [d for d in _drifts(root) if ".claude/agents/" in d.file] == []

    def test_composed_by_this_release_has_no_blocking_drift(self, tmp_path: Path) -> None:
        root = _composed(tmp_path, "cursor")
        assert _blocking(root) == []

    def test_a_deleted_cursor_rule_is_reported_missing(self, tmp_path: Path) -> None:
        root = _composed(tmp_path, "cursor")
        (root / cursor_command_rule_relpath("task-init")).unlink()
        assert [d.file for d in _blocking(root)] == [str(cursor_command_rule_relpath("task-init"))]

    def test_a_hand_edited_cursor_rule_is_reported_and_not_fixed(self, tmp_path: Path) -> None:
        root = _composed(tmp_path, "cursor")
        rule = root / cursor_core_rule_relpath()
        edited = rule.read_text(encoding="utf-8") + "\n## OUR RULE\n"
        rule.write_text(edited, encoding="utf-8")
        blocking = _blocking(root)
        assert [d.file for d in blocking] == [str(cursor_core_rule_relpath())]
        assert "hand-edited" in blocking[0].reason
        apply_config_fixes(root)
        assert rule.read_text(encoding="utf-8") == edited


class TestAProjectDeclaringBothTools:
    def test_composed_by_this_release_has_no_blocking_drift(self, tmp_path: Path) -> None:
        root = _composed(tmp_path, "claude", "cursor")
        assert _blocking(root) == []

    def test_cursor_rules_missing_is_red_naming_the_tool_and_the_layer(
        self, tmp_path: Path
    ) -> None:
        root = _composed(tmp_path, "claude", "cursor")
        for rule in (root / ".cursor" / "rules").glob("*.mdc"):
            rule.unlink()
        gaps = [d for d in _blocking(root) if "lacks" in d.reason]
        assert len(gaps) == 1
        assert "`cursor`" in gaps[0].reason
        assert "project" in gaps[0].reason
        assert gaps[0].fixable

    def test_fix_composes_the_missing_rules(self, tmp_path: Path) -> None:
        root = _composed(tmp_path, "claude", "cursor")
        for rule in (root / ".cursor" / "rules").glob("*.mdc"):
            rule.unlink()
        apply_config_fixes(root)
        assert (root / cursor_core_rule_relpath()).is_file()
        assert _blocking(root) == []
