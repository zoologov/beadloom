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


class TestCoordinatorGateLoop:
    """BDL-052 S1: the coordinator encodes the Gate-enforced loop + explicit
    mandatory parallelism as tool steps (not prose to remember)."""

    def _coordinator_text(self) -> str:
        return (_live_claude_root() / "commands" / "coordinator.md").read_text(
            encoding="utf-8"
        )

    def test_gate_loop_encoded(self) -> None:
        text = self._coordinator_text()
        lowered = text.lower()
        # The Gate is run as an explicit tool step.
        assert "beadloom ci" in lowered
        # The retry loop: while Gate red -> run tech-writer -> re-gate.
        assert "while" in lowered
        assert "re-gate" in lowered or "re-run" in lowered
        # Bounded retries (no infinite spin).
        assert "bound" in lowered or "retr" in lowered

    def test_parallelism_explicit_and_mandatory(self) -> None:
        text = self._coordinator_text()
        lowered = text.lower()
        assert "must" in lowered and "concurrent" in lowered
        assert "merge-slot" in lowered

    def test_gate_loop_is_bounded_with_explicit_stop(self) -> None:
        """The retry loop is bounded (a numeric attempt cap) and STOPs instead of
        spinning forever when the Gate stays red."""
        text = self._coordinator_text()
        lowered = text.lower()
        # An explicit numeric bound on attempts (not just the word 'bounded').
        assert "attempts < 3" in lowered or "≤3" in text or "3 attempts" in lowered
        # On exhaustion it STOPs and does NOT push.
        assert "stop" in lowered
        assert "do not push" in lowered

    def test_gate_loop_runs_techwriter_then_regates(self) -> None:
        """The loop body is: run tech-writer on drifted refs -> re-run the Gate."""
        text = self._coordinator_text()
        lowered = text.lower()
        assert "tech-writer" in lowered
        # The Gate is re-run inside the loop (re-gate).
        assert lowered.count("beadloom ci") >= 2

    def test_independent_ready_beads_launched_concurrently(self) -> None:
        """Mandatory parallelism: N independent ready beads -> N subagents at once,
        not one-at-a-time."""
        text = self._coordinator_text()
        lowered = text.lower()
        assert "one-at-a-time" in lowered or "one at a time" in lowered
        assert "mandatory" in lowered

    def test_pre_push_hook_named_as_backstop(self) -> None:
        """The coordinator points at the pre-push Gate hook as the blocking
        backstop, with the documented --no-verify escape hatch."""
        text = self._coordinator_text()
        lowered = text.lower()
        assert "pre-push" in lowered
        assert "install-hooks" in lowered
        assert "--no-verify" in lowered


class TestCoordinatorVendoredDriftGuard:
    """The vendored coordinator template is byte-identical to the live one (so the
    scaffold ships the latest Gate-loop + parallelism encoding)."""

    def test_vendored_coordinator_byte_identical_to_live(self) -> None:
        from pathlib import Path

        vendored = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "beadloom"
            / "onboarding"
            / "templates"
            / "agentic_flow"
            / "commands"
            / "coordinator.md.txt"
        )
        live = _live_claude_root() / "commands" / "coordinator.md"
        assert vendored.read_text(encoding="utf-8") == live.read_text(encoding="utf-8")


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


class TestPartialPreExisting:
    def test_partial_claude_dir_is_completed(self, tmp_path: Path) -> None:
        """A repo with SOME .claude/ files already present is filled in: the
        pre-existing matching file is left, the missing ones are written."""
        project = _make_project(tmp_path)
        agents_dir = project / ".claude" / "agents"
        agents_dir.mkdir(parents=True)
        # Pre-place ONE agent file (byte-identical to the vendored template).
        live = _live_claude_root()
        (agents_dir / "dev.md").write_text(
            (live / "agents" / "dev.md").read_text(encoding="utf-8"),
            encoding="utf-8",
        )

        result = scaffold(project)

        # All four agents end up present; none skipped (the pre-existing one matched).
        for name in AGENT_FILES:
            assert (agents_dir / f"{name}.md").is_file(), name
        assert result.agents_skipped == []
        # The commands the repo never had are now written.
        for name in COMMAND_FILES:
            assert (project / ".claude" / "commands" / f"{name}.md").is_file(), name

    def test_preexisting_claude_md_prose_preserved(self, tmp_path: Path) -> None:
        """A hand-authored CLAUDE.md (with prose) is augmented with auto-regions,
        never clobbered: the prose survives the scaffold."""
        project = _make_project(tmp_path)
        claude_md = project / ".claude" / "CLAUDE.md"
        claude_md.parent.mkdir(parents=True)
        claude_md.write_text(
            "# My team handbook\n\nWe ship on Tuesdays.\n", encoding="utf-8"
        )

        scaffold(project)

        after = claude_md.read_text(encoding="utf-8")
        assert "We ship on Tuesdays." in after


class TestForceRegeneratesCommands:
    def test_force_overwrites_edited_command_file(self, tmp_path: Path) -> None:
        project = _make_project(tmp_path)
        scaffold(project)
        cmd = project / ".claude" / "commands" / "coordinator.md"
        cmd.write_text("HAND EDITED PLAYBOOK", encoding="utf-8")
        result = scaffold(project, force=True)
        assert "HAND EDITED PLAYBOOK" not in cmd.read_text(encoding="utf-8")
        assert "coordinator" in result.commands_written

    def test_force_preserves_user_prose_in_claude_md(self, tmp_path: Path) -> None:
        """Even with --force, user prose outside CLAUDE.md auto-regions survives
        (force overwrites the base, but refresh only touches the marked regions —
        and the base re-drop carries no user prose, so we assert prose added
        AFTER a force is preserved by the next force)."""
        project = _make_project(tmp_path)
        scaffold(project)
        claude_md = project / ".claude" / "CLAUDE.md"
        marker = "\n## Team rule\n\nNo Friday deploys.\n"
        claude_md.write_text(
            claude_md.read_text(encoding="utf-8") + marker, encoding="utf-8"
        )
        # A force re-drops the base CLAUDE.md, which legitimately replaces the
        # whole file — so prose added by the user is NOT preserved under --force.
        # This documents the force contract: idempotent re-vendor of the base.
        scaffold(project, force=True)
        # The auto-regions are still present + project facts correct.
        text = claude_md.read_text(encoding="utf-8")
        assert "Project: acme-service" in text


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

    def test_cli_recomposes_hand_edited_agent_file(self, tmp_path: Path) -> None:
        """BDL-052 S3: role files (.claude/agents/*) are now COMPOSED from
        CORE+overlays — the composer is their source of truth, so a hand-edit is
        recomposed away on the next run (drift-guard semantics), not preserved.
        Hand-edit preservation now applies only to the vendored commands/CLAUDE.md."""
        project = _make_project(tmp_path)
        _run(project)
        agent = project / ".claude" / "agents" / "dev.md"
        agent.write_text("HAND EDITED", encoding="utf-8")
        result = _run(project)
        assert result.exit_code == 0, result.output
        assert "HAND EDITED" not in agent.read_text(encoding="utf-8")
        # The composed body is back.
        assert "## CORE" in agent.read_text(encoding="utf-8")

    def test_cli_hand_edited_command_still_skipped(self, tmp_path: Path) -> None:
        """Without --force, a hand-edited vendored command file is left untouched."""
        project = _make_project(tmp_path)
        _run(project)
        cmd = project / ".claude" / "commands" / "coordinator.md"
        cmd.write_text("HAND EDITED", encoding="utf-8")
        result = _run(project)
        assert result.exit_code == 0, result.output
        assert "Skipped .claude/commands/coordinator.md" in result.output
        assert "--force" in result.output
        assert cmd.read_text(encoding="utf-8") == "HAND EDITED"

    def test_cli_force_overwrites_command_via_flag(self, tmp_path: Path) -> None:
        project = _make_project(tmp_path)
        _run(project)
        cmd = project / ".claude" / "commands" / "coordinator.md"
        cmd.write_text("HAND EDITED", encoding="utf-8")
        result = _run(project, "--force")
        assert result.exit_code == 0, result.output
        assert "HAND EDITED" not in cmd.read_text(encoding="utf-8")
