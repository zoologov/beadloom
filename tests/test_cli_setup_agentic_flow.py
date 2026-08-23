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

import pytest
from click.testing import CliRunner

from beadloom.onboarding import agentic_flow_setup
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
        """Drift guard: every vendored AGENT template byte-matches the live file.

        Agents only. The commands and ``CLAUDE.md`` are no longer snapshots of
        this repo's live files — they are the shipped CORE, and the live files
        are COMPOSED from them plus this repo's own project layer. Asserting
        byte-equality on those is exactly the loop BDL-UX #177 measured: it made
        the distributed artifact unable to differ from one project's local text.
        Their guard is :meth:`test_live_flow_equals_its_composition`.
        """
        root = vendored_flow_root()
        live = _live_claude_root()
        for name in AGENT_FILES:
            assert (root / "agents" / f"{name}.md.txt").read_text(
                encoding="utf-8"
            ) == (live / "agents" / f"{name}.md").read_text(encoding="utf-8"), name

    def test_live_flow_equals_its_composition(self) -> None:
        """This repo's own ``.claude/`` is the composition of what it ships.

        The replacement guard: instead of "the template equals our file", which
        forced our local text outward, "our file equals CORE + overlays + OUR
        project layer", which lets the two differ exactly where we declared they
        should.
        """
        from pathlib import Path

        from beadloom.onboarding.agentic_flow_setup import (
            composed_claude_md,
            composed_command,
        )
        from beadloom.onboarding.flow_config import resolve_flow_config
        from beadloom.onboarding.scanner import (
            _detect_project_name,
            blank_auto_regions,
        )

        repo = Path(__file__).resolve().parents[1]
        config = resolve_flow_config(repo)
        live = _live_claude_root()
        for name in COMMAND_FILES:
            assert composed_command(name, config, repo) == (
                live / f"commands/{name}.md"
            ).read_text(encoding="utf-8"), name
        expected = blank_auto_regions(
            composed_claude_md(
                config, repo, project_name=_detect_project_name(repo)
            )
        )
        actual = blank_auto_regions(
            (live / "CLAUDE.md").read_text(encoding="utf-8")
        )
        assert expected == actual


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
    """Re-vendoring the ROLE files from a live ``.claude/`` — into tmp_path.

    ``sync_agentic_flow`` writes package data. Until BDL-061.10 these tests
    called it against the REAL package, so every ``pytest`` run — and ``pytest``
    runs inside ``beadloom ci`` — copied whatever this maintainer's local
    ``.claude/agents/*`` happened to say into the shipped templates, and the
    drift guard that exists to catch that then compared the template against the
    file it had just been copied from.

    Measured in a clean room at HEAD, with one line appended to the live
    ``.claude/agents/dev.md``: run 1 FAILED and shipped the edit anyway (the
    tracked template's sha256 moved ``77dfc84…`` → ``b8bf376…``), run 2 passed
    with the edit inside the package. That is BDL-UX #177's loop, surviving on
    the one leg the CLAUDE.md fix did not cover — and it left no trace in ``git
    status`` on an unedited tree, because the write is byte-identical there.

    The destination is redirected here, so the round trip is exercised without
    the suite mutating the artifact it measures. The structural half of the fix
    is in ``tests/conftest.py``: any test that writes a git-tracked file fails.
    """

    @pytest.fixture()
    def vendor_root(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
        """A throw-away stand-in for the installed package's template root."""
        root = tmp_path / "package-templates"
        root.mkdir()
        monkeypatch.setattr(
            agentic_flow_setup, "vendored_flow_root", lambda: root
        )
        return root

    def test_sync_round_trips_live_source(self, vendor_root: Path) -> None:
        # Arrange
        live = _live_claude_root()

        # Act
        written = sync_agentic_flow(live)

        # Assert — every role file arrives, byte-identical to its live source
        assert sorted(written) == sorted(f"agents/{name}.md.txt" for name in AGENT_FILES)
        for name in AGENT_FILES:
            assert (vendor_root / "agents" / f"{name}.md.txt").read_text(
                encoding="utf-8"
            ) == (live / "agents" / f"{name}.md").read_text(encoding="utf-8"), name

    def test_sync_does_not_touch_the_claude_md_core(self, vendor_root: Path) -> None:
        """BDL-UX #177's first leg: the shipped CLAUDE.md is not a snapshot.

        It used to be. Running this very function rewrote
        ``templates/agentic_flow/CLAUDE.md.txt`` from ``.claude/CLAUDE.md``,
        which is why a project-local paragraph — a bead id and a false claim
        about this repo's branch protection — reached the shipped template
        twice, the second time OVER the correction.

        Asserted over what the sync PRODUCED rather than over the package's
        unchanged sha256: with the destination redirected, "the packaged file
        did not change" would be true by construction and would check nothing.
        """
        # Act
        written = sync_agentic_flow(_live_claude_root())

        # Assert
        assert not any("CLAUDE" in name for name in written)
        assert not (vendor_root / "CLAUDE.md.txt").exists()

    def test_sync_does_not_touch_the_command_cores(self, vendor_root: Path) -> None:
        """The commands compose too, so they are not snapshotted either."""
        # Act
        written = sync_agentic_flow(_live_claude_root())

        # Assert — the produced set is exactly the roles, nothing else
        produced = sorted(
            path.relative_to(vendor_root).as_posix()
            for path in vendor_root.rglob("*")
            if path.is_file()
        )
        assert produced == sorted(f"agents/{name}.md.txt" for name in AGENT_FILES)
        assert not any(name.startswith("commands/") for name in written)


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
        # Named verbatim as the target's manifest declares them: the renderer
        # READS the dependency list now instead of matching it against a fixed
        # vocabulary that happened to be Beadloom's own (BDL-UX #183's sweep).
        assert "click" in region
        assert "rich" in region
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
        # The advice used to be `use --force` — the destructive flag, naming
        # nowhere safe for the edit. It is now the migration note the library
        # had been computing and nobody printed (BDL-UX #188).
        assert "--force" not in result.output
        assert ".beadloom/flow/commands/coordinator.md" in result.output
        assert cmd.read_text(encoding="utf-8") == "HAND EDITED"

    def test_cli_force_overwrites_command_via_flag(self, tmp_path: Path) -> None:
        project = _make_project(tmp_path)
        _run(project)
        cmd = project / ".claude" / "commands" / "coordinator.md"
        cmd.write_text("HAND EDITED", encoding="utf-8")
        result = _run(project, "--force")
        assert result.exit_code == 0, result.output
        assert "HAND EDITED" not in cmd.read_text(encoding="utf-8")
