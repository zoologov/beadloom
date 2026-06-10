"""Tests for `beadloom setup-agentic-flow` (BDL-048 / BEAD-01).

The command scaffolds Beadloom's proven multi-agent dev flow into ANY target
repo, preserving the flow 1:1: the ``.claude/agents/*`` + ``.claude/commands/*``
are vendored byte-identical to Beadloom's own live ``.claude/`` (a drift-guard
test keeps them in sync), and the ``.claude/CLAUDE.md`` auto-regions are
generated per-project (never hardcoding Beadloom's facts). The scaffold is
idempotent and never touches user prose outside the auto-regions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from click.testing import CliRunner

from beadloom.onboarding.agentic_flow_setup import (
    AGENT_FILES,
    COMMAND_FILES,
    scaffold,
    sync_agentic_flow,
    vendored_flow_root,
)
from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path


def _live_claude_root() -> Path:
    from pathlib import Path

    return Path(__file__).resolve().parents[1] / ".claude"


def _make_project(tmp_path: Path, name: str = "acme-service") -> Path:
    project = tmp_path / name
    project.mkdir()
    (project / "pyproject.toml").write_text(
        '[project]\nname = "acme-service"\nversion = "9.9.9"\n'
        'dependencies = ["click", "rich"]\n',
        encoding="utf-8",
    )
    return project


def _run(project: Path, *extra: str) -> object:
    runner = CliRunner()
    return runner.invoke(
        main,
        ["setup-agentic-flow", "--project", str(project), *extra],
    )


class TestVendoredFlowAssets:
    def test_vendored_root_exists_and_has_all_assets(self) -> None:
        root = vendored_flow_root()
        assert root.is_dir()
        for name in AGENT_FILES:
            assert (root / "agents" / f"{name}.md.txt").is_file(), name
        for name in COMMAND_FILES:
            assert (root / "commands" / f"{name}.md.txt").is_file(), name

    def test_vendored_flow_matches_live_claude(self) -> None:
        """Drift guard: every vendored template byte-matches the live ``.claude/``
        file (so the scaffold always ships the latest proven flow)."""
        root = vendored_flow_root()
        live = _live_claude_root()
        for name in AGENT_FILES:
            assert (root / "agents" / f"{name}.md.txt").read_text(
                encoding="utf-8"
            ) == (live / "agents" / f"{name}.md").read_text(encoding="utf-8"), name
        for name in COMMAND_FILES:
            assert (root / "commands" / f"{name}.md.txt").read_text(
                encoding="utf-8"
            ) == (live / "commands" / f"{name}.md").read_text(encoding="utf-8"), name


class TestSyncAgenticFlow:
    def test_sync_round_trips_live_source(self) -> None:
        written = sync_agentic_flow(_live_claude_root())
        assert "agents/dev.md.txt" in written
        assert "commands/coordinator.md.txt" in written
        # Re-running is a no-op against the packaged copy (drift guard as code).
        assert TestVendoredFlowAssets().test_vendored_flow_matches_live_claude() is None


class TestScaffoldFiles:
    def test_drops_all_agents_and_commands(self, tmp_path: Path) -> None:
        project = _make_project(tmp_path)
        result = scaffold(project)
        for name in AGENT_FILES:
            assert (project / ".claude" / "agents" / f"{name}.md").is_file(), name
        for name in COMMAND_FILES:
            assert (project / ".claude" / "commands" / f"{name}.md").is_file(), name
        assert result.agents_written
        assert result.commands_written

    def test_vendored_files_byte_identical_after_scaffold(self, tmp_path: Path) -> None:
        project = _make_project(tmp_path)
        scaffold(project)
        live = _live_claude_root()
        for name in AGENT_FILES:
            assert (project / ".claude" / "agents" / f"{name}.md").read_text(
                encoding="utf-8"
            ) == (live / "agents" / f"{name}.md").read_text(encoding="utf-8"), name

    def test_writes_claude_md(self, tmp_path: Path) -> None:
        project = _make_project(tmp_path)
        scaffold(project)
        claude_md = project / ".claude" / "CLAUDE.md"
        assert claude_md.is_file()


class TestClaudeMdRegionsPerProject:
    def test_uses_target_project_facts_not_beadloom(self, tmp_path: Path) -> None:
        project = _make_project(tmp_path)
        scaffold(project)
        text = (project / ".claude" / "CLAUDE.md").read_text(encoding="utf-8")
        # Target project name in the heading, NOT "Beadloom".
        assert "Project: acme-service" in text
        assert "Project: Beadloom" not in text

    def test_stack_auto_region_reflects_target_deps(self, tmp_path: Path) -> None:
        """The CLAUDE.md auto-region is regenerated from the TARGET's deps
        (Click + Rich present in its pyproject), not Beadloom's full stack."""
        project = _make_project(tmp_path)
        scaffold(project)
        text = (project / ".claude" / "CLAUDE.md").read_text(encoding="utf-8")
        start = text.index("<!-- beadloom:auto-start project-info -->")
        end = text.index("<!-- beadloom:auto-end -->")
        region = text[start:end]
        assert "Click" in region
        assert "Rich" in region
        # tree-sitter is in Beadloom's stack but NOT the target's deps.
        assert "tree-sitter" not in region

    def test_honest_boundary_note_present(self, tmp_path: Path) -> None:
        project = _make_project(tmp_path)
        scaffold(project)
        text = (project / ".claude" / "CLAUDE.md").read_text(encoding="utf-8")
        lowered = text.lower()
        assert "mcp" in lowered
        assert "orchestration" in lowered or "coordinator" in lowered


class TestIdempotency:
    def test_rerun_is_stable(self, tmp_path: Path) -> None:
        project = _make_project(tmp_path)
        scaffold(project)
        first = (project / ".claude" / "CLAUDE.md").read_text(encoding="utf-8")
        agent_first = (project / ".claude" / "agents" / "dev.md").read_text(
            encoding="utf-8"
        )
        scaffold(project)
        second = (project / ".claude" / "CLAUDE.md").read_text(encoding="utf-8")
        agent_second = (project / ".claude" / "agents" / "dev.md").read_text(
            encoding="utf-8"
        )
        assert first == second
        assert agent_first == agent_second

    def test_preserves_user_prose_outside_auto_regions(self, tmp_path: Path) -> None:
        project = _make_project(tmp_path)
        scaffold(project)
        claude_md = project / ".claude" / "CLAUDE.md"
        text = claude_md.read_text(encoding="utf-8")
        marker = "\n## My custom team rules\n\nNever deploy on Fridays.\n"
        claude_md.write_text(text + marker, encoding="utf-8")
        scaffold(project)
        after = claude_md.read_text(encoding="utf-8")
        assert "Never deploy on Fridays." in after


class TestForce:
    def test_hand_edited_file_is_skipped_without_force(self, tmp_path: Path) -> None:
        project = _make_project(tmp_path)
        scaffold(project)
        agent = project / ".claude" / "agents" / "dev.md"
        agent.write_text("HAND EDITED", encoding="utf-8")
        result = scaffold(project)  # no force
        assert "dev" in result.agents_skipped
        assert agent.read_text(encoding="utf-8") == "HAND EDITED"

    def test_force_overwrites_user_edited_agent_file(self, tmp_path: Path) -> None:
        project = _make_project(tmp_path)
        scaffold(project)
        agent = project / ".claude" / "agents" / "dev.md"
        agent.write_text("HAND EDITED", encoding="utf-8")
        scaffold(project, force=True)
        assert "HAND EDITED" not in agent.read_text(encoding="utf-8")


class TestCli:
    def test_cli_scaffolds_and_prints_next_steps(self, tmp_path: Path) -> None:
        project = _make_project(tmp_path)
        result = _run(project)
        assert result.exit_code == 0, result.output
        assert (project / ".claude" / "agents" / "dev.md").is_file()
        assert (project / ".claude" / "commands" / "coordinator.md").is_file()
        # Honest boundary note in the printed next steps.
        lowered = result.output.lower()
        assert "mcp" in lowered
        assert "beadloom ci" in lowered

    def test_cli_idempotent(self, tmp_path: Path) -> None:
        project = _make_project(tmp_path)
        assert _run(project).exit_code == 0  # type: ignore[attr-defined]
        result = _run(project)
        assert result.exit_code == 0, result.output

    def test_cli_force_flag(self, tmp_path: Path) -> None:
        project = _make_project(tmp_path)
        _run(project)
        result = _run(project, "--force")
        assert result.exit_code == 0, result.output
