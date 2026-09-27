"""Self-checks of this repository's agent roles, hooks, tracker and commits (BDL-074 A3).

Moved out of ``tests/test_cli_setup_agentic_flow.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.onboarding.agentic_flow_setup import (
    AGENT_FILES,
    COMMAND_FILES,
)

if TYPE_CHECKING:
    from pathlib import Path


def _live_claude_root() -> Path:
    from pathlib import Path

    return Path(__file__).resolve().parents[3] / ".claude"


class TestShippedFlowAssets:
    """What the package ships, and the one direction the guard runs in.

    Every asset here is AUTHORED package data. The live ``.claude/`` files are
    composed from it plus this repo's own project layer, so the guard asserts
    that direction and never the reverse. Asserting "the template equals our
    file" is the loop BDL-UX #177 measured: it makes the distributed artifact
    unable to differ from one project's local text. The commands and CLAUDE.md
    left that loop in BDL-061 S3; the role assets left it by being deleted in
    BDL-068 ``beadloom-iur5``, which is why no ``agents/`` assertion remains.
    """

    def test_live_flow_equals_its_composition(self) -> None:
        """This repo's own ``.claude/`` is the composition of what it ships.

        The replacement guard: instead of "the template equals our file", which
        forced our local text outward, "our file equals CORE + overlays + OUR
        project layer", which lets the two differ exactly where we declared they
        should. The roles are in it since ``beadloom-iur5``, and they are the
        reason it is the only guard: with the snapshot gone, this is what would
        catch a live role file that stopped matching what an adopter receives.
        """
        from pathlib import Path

        from beadloom.onboarding.agentic_flow_setup import (
            composed_claude_md,
            composed_command,
        )
        from beadloom.onboarding.flow_config import resolve_flow_config
        from beadloom.onboarding.role_composer import compose_all_roles
        from beadloom.onboarding.scanner import (
            _detect_project_name,
            blank_auto_regions,
        )

        repo = Path(__file__).resolve().parents[3]
        config = resolve_flow_config(repo)
        live = _live_claude_root()
        for name in COMMAND_FILES:
            assert composed_command(name, config, repo) == (
                live / f"commands/{name}.md"
            ).read_text(encoding="utf-8"), name
        composed_roles = compose_all_roles(config, repo)
        for name in AGENT_FILES:
            assert composed_roles[name] == (
                live / f"agents/{name}.md"
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
            Path(__file__).resolve().parents[3]
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
