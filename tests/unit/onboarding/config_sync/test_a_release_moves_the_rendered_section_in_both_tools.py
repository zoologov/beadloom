"""A version bump on a project composed for both tools (BDL-083 S2R pass 1 Major 1, RFC D13).

Measured at `b7d46e27` on a scratch project composed for Claude and Cursor: the
version went from 1.0.0 to 2.0.0 and a dependency was added. `config-check`
exited 1 with two errors. `.claude/CLAUDE.md` read "auto-managed section(s)
stale: project-info", which names the cause. The Cursor core rule read "composed
body is stale vs CORE + the flow.yml overlays + the project layer", although none
of those had moved: its drift check compared the whole body, the rendered
project-info section included, where the CLAUDE.md check blanks that section.
`setup-rules --refresh` then repaired CLAUDE.md and left the rule stale, so the
two tools carried two texts.

Both files carry one composed core with one rendered section, so both are
compared with that section blanked, both report a moved section by its name, and
one refresh re-renders it in both.
"""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

from click.testing import CliRunner

from beadloom.onboarding.agentic_flow_setup import scaffold
from beadloom.onboarding.config_sync import apply_config_fixes, check_config_drift
from beadloom.onboarding.flow_config import FlowConfig, persist_flow_config
from beadloom.onboarding.role_adapters import generate_adapters
from beadloom.onboarding.tool_reach import cursor_core_rule_relpath, rule_body
from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

    from beadloom.onboarding.config_sync import ConfigDrift

_CLAUDE_MD = ".claude/CLAUDE.md"
_CURSOR_CORE = str(cursor_core_rule_relpath())
_SECTION_STALE = "auto-managed section(s) stale: project-info"


def _manifest(version: str, *dependencies: str) -> str:
    listed = ", ".join(f'"{name}"' for name in dependencies)
    return f'[project]\nname = "acme"\nversion = "{version}"\ndependencies = [{listed}]\n'


def _composed(tmp_path: Path, *tools: str) -> Path:
    root = tmp_path / "acme"
    root.mkdir(parents=True)
    (root / "pyproject.toml").write_text(_manifest("1.0.0", "click"), encoding="utf-8")
    config = FlowConfig(tools=tools, architecture="ddd", stack=("python",))
    persist_flow_config(root, config)
    generate_adapters(config, root)
    scaffold(root, include_agents=False, config=config)
    return root


def _released(root: Path) -> None:
    """The release the finding measured: 1.0.0 -> 2.0.0 and a new dependency."""
    (root / "pyproject.toml").write_text(_manifest("2.0.0", "click", "rich"), encoding="utf-8")


def _blocking(root: Path) -> list[ConfigDrift]:
    drifts = check_config_drift(root, sqlite3.connect(":memory:"))
    return [d for d in drifts if d.severity == "error"]


def _texts(root: Path) -> tuple[str, str]:
    claude_md = (root / _CLAUDE_MD).read_text(encoding="utf-8")
    rule = (root / _CURSOR_CORE).read_text(encoding="utf-8")
    return claude_md, rule_body(rule)


class TestAReleaseOnABothToolsProject:
    def test_each_file_names_the_rendered_section_and_no_layer(self, tmp_path: Path) -> None:
        root = _composed(tmp_path, "claude", "cursor")
        assert _blocking(root) == []
        _released(root)
        found = [(d.file, d.reason) for d in _blocking(root)]
        assert found == [(_CLAUDE_MD, _SECTION_STALE), (_CURSOR_CORE, _SECTION_STALE)]

    def test_reads_what_a_claude_only_project_reads(self, tmp_path: Path) -> None:
        claude_only = _composed(tmp_path / "one", "claude")
        both = _composed(tmp_path / "two", "claude", "cursor")
        _released(claude_only)
        _released(both)
        reasons = {d.reason for d in _blocking(both)}
        assert reasons == {d.reason for d in _blocking(claude_only)} == {_SECTION_STALE}

    def test_setup_rules_refresh_repairs_both_files_into_one_text(self, tmp_path: Path) -> None:
        root = _composed(tmp_path, "claude", "cursor")
        _released(root)
        result = CliRunner().invoke(main, ["setup-rules", "--refresh", "--project", str(root)])
        assert result.exit_code == 0, result.output
        assert f"Updated {_CURSOR_CORE} sections: project-info" in result.output
        assert _blocking(root) == []
        claude_md, cursor_body = _texts(root)
        assert "2.0.0" in claude_md
        assert cursor_body == claude_md

    def test_setup_rules_refresh_dry_run_names_both_and_writes_neither(
        self, tmp_path: Path
    ) -> None:
        root = _composed(tmp_path, "claude", "cursor")
        _released(root)
        before = _texts(root)
        result = CliRunner().invoke(
            main, ["setup-rules", "--refresh", "--dry-run", "--project", str(root)]
        )
        assert result.exit_code == 0, result.output
        assert f"Would update {_CLAUDE_MD} sections: project-info" in result.output
        assert f"Would update {_CURSOR_CORE} sections: project-info" in result.output
        assert _texts(root) == before

    def test_config_check_fix_repairs_both_files_into_one_text(self, tmp_path: Path) -> None:
        root = _composed(tmp_path, "claude", "cursor")
        _released(root)
        apply_config_fixes(root)
        assert _blocking(root) == []
        claude_md, cursor_body = _texts(root)
        assert cursor_body == claude_md

    def test_setup_agentic_flow_rerun_repairs_both_files_into_one_text(
        self, tmp_path: Path
    ) -> None:
        root = _composed(tmp_path, "claude", "cursor")
        _released(root)
        config = FlowConfig(tools=("claude", "cursor"), architecture="ddd", stack=("python",))
        result = scaffold(root, include_agents=False, config=config)
        assert result.migration_notes == []
        assert _blocking(root) == []
        claude_md, cursor_body = _texts(root)
        assert cursor_body == claude_md


class TestAHandEditOfTheRenderedSection:
    """The CLAUDE.md check reports it as the section gone stale; so does the rule's."""

    @staticmethod
    def _edit_section(path: Path) -> None:
        text = path.read_text(encoding="utf-8")
        assert "- **Current version:** 1.0.0" in text
        path.write_text(
            text.replace("- **Current version:** 1.0.0", "- **Current version:** 0.9"),
            encoding="utf-8",
        )

    def test_in_the_cursor_rule_reads_as_in_claude_md(self, tmp_path: Path) -> None:
        claude = _composed(tmp_path / "one", "claude", "cursor")
        cursor = _composed(tmp_path / "two", "claude", "cursor")
        self._edit_section(claude / _CLAUDE_MD)
        self._edit_section(cursor / _CURSOR_CORE)
        assert [(d.file, d.reason) for d in _blocking(claude)] == [(_CLAUDE_MD, _SECTION_STALE)]
        assert [(d.file, d.reason) for d in _blocking(cursor)] == [(_CURSOR_CORE, _SECTION_STALE)]

    def test_in_the_cursor_rule_is_re_rendered_by_the_refresh(self, tmp_path: Path) -> None:
        root = _composed(tmp_path, "claude", "cursor")
        self._edit_section(root / _CURSOR_CORE)
        result = CliRunner().invoke(main, ["setup-rules", "--refresh", "--project", str(root)])
        assert result.exit_code == 0, result.output
        assert _blocking(root) == []
        claude_md, cursor_body = _texts(root)
        assert cursor_body == claude_md

    def test_outside_the_section_is_still_a_hand_edit_of_the_body(self, tmp_path: Path) -> None:
        root = _composed(tmp_path, "claude", "cursor")
        rule = root / _CURSOR_CORE
        rule.write_text(rule.read_text(encoding="utf-8") + "\n## OUR RULE\n", encoding="utf-8")
        blocking = _blocking(root)
        assert [d.file for d in blocking] == [_CURSOR_CORE]
        assert "hand-edited" in blocking[0].reason
