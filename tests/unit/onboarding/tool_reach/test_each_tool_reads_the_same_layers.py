"""Which composed layers each declared tool reads (BDL-083 S2h, RFC D13, BDL-UX #356).

Up to 9.0.0 the core, the project layer, the STACK overlay and the four commands
were composed for Claude Code alone; a project naming Cursor received the role
files and a 17-line pointer. These tests hold the two halves of the repair: the
composition a Cursor agent reads carries the same layers as the one a Claude
agent reads, and a tool whose files carry fewer layers than another declared
tool's is named, with the layers it lacks.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.onboarding.agentic_flow_setup import COMMAND_FILES, scaffold
from beadloom.onboarding.composer import (
    ARTIFACT_KINDS,
    CLAUDE_ARTIFACT_NAME,
    PROJECT_FLOW_DIRNAME,
    compose,
)
from beadloom.onboarding.flow_config import FlowConfig
from beadloom.onboarding.role_adapters import generate_adapters
from beadloom.onboarding.tool_reach import (
    LEGACY_CURSOR_POINTER,
    cursor_command_rule_relpath,
    cursor_core_rule_relpath,
    cursor_rule_text,
    layer_gaps,
    rule_body,
)

if TYPE_CHECKING:
    from pathlib import Path

_DOD = "## Definition of Done\n\nEvery bead runs the full check and quotes each exit code.\n"
_CURSOR_ONLY_NOTE = "## Cursor\n\nSubagents live in `.cursor/agents/`.\n"


def _config(*tools: str) -> FlowConfig:
    return FlowConfig(tools=tools, architecture="ddd", stack=("python",))


def _project(tmp_path: Path, label: str = "acme") -> Path:
    root = tmp_path / label
    root.mkdir()
    (root / "pyproject.toml").write_text(
        '[project]\nname = "acme"\nversion = "0.1.0"\n', encoding="utf-8"
    )
    return root


def _fragment(root: Path, kind: str, text: str) -> None:
    path = root / PROJECT_FLOW_DIRNAME / kind / f"{CLAUDE_ARTIFACT_NAME}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _compose_flow(root: Path, config: FlowConfig) -> None:
    generate_adapters(config, root)
    scaffold(root, include_agents=False, config=config)


class TestTheCursorKindComposesTheCore:
    def test_cursor_is_an_artifact_kind(self) -> None:
        assert "cursor" in ARTIFACT_KINDS

    def test_without_a_project_layer_both_kinds_compose_the_same_text(self) -> None:
        config = _config("claude", "cursor")
        claude = compose("claude", CLAUDE_ARTIFACT_NAME, config=config)
        cursor = compose("cursor", CLAUDE_ARTIFACT_NAME, config=config)
        assert cursor.text == claude.text
        assert [f.source for f in cursor.fragments] == [f.source for f in claude.fragments]

    def test_the_claude_project_fragment_reaches_the_cursor_composition(
        self, tmp_path: Path
    ) -> None:
        root = _project(tmp_path)
        _fragment(root, "claude", _DOD)
        cursor = compose(
            "cursor", CLAUDE_ARTIFACT_NAME, config=_config("cursor"), project_root=root
        )
        assert _DOD in cursor.text

    def test_a_cursor_fragment_reaches_cursor_and_not_claude(self, tmp_path: Path) -> None:
        root = _project(tmp_path)
        _fragment(root, "claude", _DOD)
        _fragment(root, "cursor", _CURSOR_ONLY_NOTE)
        config = _config("claude", "cursor")
        claude = compose("claude", CLAUDE_ARTIFACT_NAME, config=config, project_root=root)
        cursor = compose("cursor", CLAUDE_ARTIFACT_NAME, config=config, project_root=root)
        assert _CURSOR_ONLY_NOTE not in claude.text
        assert cursor.text == claude.text + _CURSOR_ONLY_NOTE
        assert cursor.fragments[-1].layer == "project:cursor"


class TestTheCursorRuleForm:
    def test_the_front_matter_applies_the_rule_to_every_request(self) -> None:
        text = cursor_rule_text("# body\n", description="the core")
        front_matter = text.split("---\n")[1].splitlines()
        assert "alwaysApply: true" in front_matter
        assert "description: the core" in front_matter

    def test_the_body_reads_back_byte_for_byte(self) -> None:
        body = "---\nnot front matter, the body's own rule line\n---\n# x\n"
        assert rule_body(cursor_rule_text(body, description="d")) == body

    def test_a_text_with_no_front_matter_is_its_own_body(self) -> None:
        assert rule_body("# plain\n") == "# plain\n"


class TestTheScaffoldWritesTheCursorRules:
    def test_a_cursor_project_receives_the_core_and_the_four_commands(
        self, tmp_path: Path
    ) -> None:
        root = _project(tmp_path)
        _fragment(root, "claude", _DOD)
        _compose_flow(root, _config("cursor"))
        core = (root / cursor_core_rule_relpath()).read_text(encoding="utf-8")
        assert rule_body(core) == (root / ".claude" / "CLAUDE.md").read_text(encoding="utf-8")
        assert _DOD in core
        for name in COMMAND_FILES:
            rule = (root / cursor_command_rule_relpath(name)).read_text(encoding="utf-8")
            command = (root / ".claude" / "commands" / f"{name}.md").read_text(encoding="utf-8")
            assert rule_body(rule) == command, name

    def test_the_pointer_is_no_longer_written(self, tmp_path: Path) -> None:
        root = _project(tmp_path)
        _compose_flow(root, _config("cursor"))
        assert not (root / LEGACY_CURSOR_POINTER).exists()

    def test_a_claude_project_receives_no_cursor_rule(self, tmp_path: Path) -> None:
        root = _project(tmp_path)
        _compose_flow(root, _config("claude"))
        assert not (root / ".cursor").exists()

    def test_a_pointer_left_by_9_0_0_is_reported_and_kept(self, tmp_path: Path) -> None:
        root = _project(tmp_path)
        pointer = root / LEGACY_CURSOR_POINTER
        pointer.parent.mkdir(parents=True)
        pointer.write_text(
            "# Beadloom agentic flow (Cursor orchestrator mode)\n", encoding="utf-8"
        )
        generate_adapters(_config("cursor"), root)
        result = scaffold(root, include_agents=False, config=_config("cursor"))
        assert pointer.is_file()
        assert any(str(LEGACY_CURSOR_POINTER) in orphan for orphan in result.orphans)

    def test_a_hand_edited_cursor_rule_is_left_alone(self, tmp_path: Path) -> None:
        root = _project(tmp_path)
        _compose_flow(root, _config("cursor"))
        rule = root / cursor_core_rule_relpath()
        edited = rule.read_text(encoding="utf-8") + "\n## OUR RULE\n"
        rule.write_text(edited, encoding="utf-8")
        result = scaffold(root, include_agents=False, config=_config("cursor"))
        assert rule.read_text(encoding="utf-8") == edited
        assert any(str(cursor_core_rule_relpath()) in note for note in result.migration_notes)


class TestALayerOneToolReadsAndAnotherDoesNot:
    def test_a_both_tools_project_composed_by_this_release_has_no_gap(
        self, tmp_path: Path
    ) -> None:
        root = _project(tmp_path)
        _fragment(root, "claude", _DOD)
        config = _config("claude", "cursor")
        _compose_flow(root, config)
        assert layer_gaps(root, config) == ()

    def test_the_cursor_rules_9_0_0_never_wrote_are_a_gap_naming_cursor(
        self, tmp_path: Path
    ) -> None:
        root = _project(tmp_path)
        _fragment(root, "claude", _DOD)
        config = _config("claude", "cursor")
        _compose_flow(root, config)
        for rule in (root / ".cursor" / "rules").glob("*.mdc"):
            rule.unlink()
        gaps = layer_gaps(root, config)
        assert [(gap.tool, gap.against) for gap in gaps] == [("cursor", "claude")]
        labels = {layer.label for layer in gaps[0].layers}
        assert {"core", "stack:python", "project"} <= labels
        assert f"{PROJECT_FLOW_DIRNAME}/claude/{CLAUDE_ARTIFACT_NAME}.md" in gaps[0].why
        assert "`cursor`" in gaps[0].why

    def test_a_cursor_only_project_has_nothing_to_compare(self, tmp_path: Path) -> None:
        root = _project(tmp_path)
        config = _config("cursor")
        _compose_flow(root, config)
        assert layer_gaps(root, config) == ()

    def test_a_layer_declared_for_cursor_alone_is_not_a_gap_for_claude(
        self, tmp_path: Path
    ) -> None:
        root = _project(tmp_path)
        _fragment(root, "cursor", _CURSOR_ONLY_NOTE)
        config = _config("claude", "cursor")
        _compose_flow(root, config)
        assert layer_gaps(root, config) == ()

    @pytest.mark.parametrize("deleted", [".claude/CLAUDE.md", ".claude/agents/dev.md"])
    def test_the_comparison_runs_in_both_directions(self, tmp_path: Path, deleted: str) -> None:
        root = _project(tmp_path)
        config = _config("claude", "cursor")
        _compose_flow(root, config)
        (root / deleted).unlink()
        gaps = layer_gaps(root, config)
        assert [(gap.tool, gap.against) for gap in gaps] == [("claude", "cursor")]
