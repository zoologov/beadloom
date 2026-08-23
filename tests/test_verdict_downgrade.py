"""An upgrade that WEAKENS a verdict is a finding (BDL-061 S3b, review `.11` MAJOR 5).

CONTEXT's standing constraint runs one way: *no adopter's green project turns
red on upgrade*. The inverse was never written because nobody expected to need
it — and then review `.11` measured it happening. A repo that hand-edited a role
file before the flow manifest existed used to produce an ``error`` and block;
after the manifest shipped, the same repo has no entry for that file, reads
``unverified``, and warns at exit 0.

**A downgrade is worse than an upgrade-induced red.** A red is loud and the
adopter correlates it with the release. A downgrade is silent: a project that
was correctly failing now passes, nobody is told, and the evidence that it ever
failed is gone. So the decision recorded here is that a severity Beadloom
reduced *for lack of evidence* is itself a finding — the finding carries the
verdict it would have had, and the command says so with a count and the command
that restores it.

The mechanism deliberately does **not** write anything. ``config-check`` must
stay a pure reader (BDL-UX #147, #189); the downgrade is computed from the
finding's own state, not from a recorded history of past verdicts.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.onboarding.config_sync import (
    _flow_manifest_drift,
    _missing_file_drifts,
    _state_drift,
)
from beadloom.onboarding.flow_manifest import ArtifactState

if TYPE_CHECKING:
    from pathlib import Path


def _drift(state: ArtifactState) -> object:
    return _state_drift(
        ".claude/agents/dev.md", state, kind="roles", name="dev"
    )


class TestAWeakenedVerdictSaysSo:
    def test_unverified_carries_the_verdict_it_would_have_had(self) -> None:
        drift = _drift(ArtifactState.UNVERIFIED)

        assert drift is not None
        assert drift.severity == "warn"
        assert drift.weakened_from == "error"

    def test_a_verdict_nobody_weakened_carries_nothing(self) -> None:
        for state in (ArtifactState.STALE, ArtifactState.HAND_EDITED, ArtifactState.MISSING):
            drift = _drift(state)
            assert drift is not None
            assert drift.severity == "error"
            assert drift.weakened_from is None

    def test_a_missing_file_no_manifest_accounts_for_is_a_weakened_error(self) -> None:
        from beadloom.onboarding.config_sync import _FlowScaffold

        scaffold_state = _FlowScaffold((), (".claude/agents/dev.md",), True)

        unaccounted = _missing_file_drifts(scaffold_state, {})
        accounted = _missing_file_drifts(
            scaffold_state, {".claude/agents/dev.md": "deadbeef"}
        )

        assert [d.severity for d in unaccounted] == ["warn"]
        assert [d.weakened_from for d in unaccounted] == ["error"]
        assert [d.severity for d in accounted] == ["error"]
        assert [d.weakened_from for d in accounted] == [None]

    def test_an_absent_manifest_is_a_weakened_verdict_too(self) -> None:
        from beadloom.onboarding.config_sync import _FlowScaffold

        drift = _flow_manifest_drift(
            _FlowScaffold((".claude/agents/dev.md",), (), True), manifest_usable=False
        )

        assert drift is not None
        assert drift.severity == "warn"
        assert drift.weakened_from == "error"


class TestTheCommandReportsTheDowngrade:
    """Exit code unchanged (a warn must not block); the SILENCE is what changes."""

    def test_config_check_names_the_downgrade_and_still_exits_zero(
        self, tmp_path: Path
    ) -> None:
        from click.testing import CliRunner

        from beadloom.services.cli import main
        from tests.adopter_project import python_project

        project = python_project(tmp_path / "invoice-svc")
        runner = CliRunner()
        init = runner.invoke(
            main, ["init", "--yes", "--mode", "bootstrap", "--project", str(project.root)]
        )
        assert init.exit_code == 0, init.output
        scaffold = runner.invoke(
            main, ["setup-agentic-flow", "--project", str(project.root)]
        )
        assert scaffold.exit_code == 0, scaffold.output

        # The pre-manifest population, reproduced: the record of what Beadloom
        # wrote is gone, so every composed artifact drops to `unverified`.
        (project.root / ".beadloom" / "flow-manifest.json").unlink()
        for role in ("dev", "test", "review", "tech-writer"):
            path = project.root / ".claude" / "agents" / f"{role}.md"
            path.write_text(
                path.read_text(encoding="utf-8") + "\n<!-- our own rule -->\n",
                encoding="utf-8",
            )

        result = runner.invoke(
            main, ["config-check", "--project", str(project.root)]
        )

        assert result.exit_code == 0
        assert "weaker" in result.output.lower()
        assert "flow-manifest.json" in result.output


class TestOneRootCauseIsOneFinding:
    """A symptom of a reported cause must not be a second, independent finding."""

    def test_a_malformed_flow_yml_is_not_also_reported_as_a_stale_auto_region(
        self, tmp_path: Path
    ) -> None:
        """The auto-regions are rendered FROM the flow config since BDL-UX #183.

        So a malformed `flow.yml` makes them differ for a reason that is not
        their own, and reporting both double-counts one cause — the reader then
        has two files to look at and one of them is a consequence.
        """
        import sqlite3

        from beadloom.onboarding.config_sync import check_config_drift
        from tests.adopter_project import python_project

        project = python_project(tmp_path / "invoice-svc")
        (project.root / ".beadloom").mkdir()
        (project.root / ".beadloom" / "flow.yml").write_text(
            "tools: [claude]\narchitecture: [ddd]\nstack: [python]\n"
            'overlays:\n  suppress:\n    - rule: "R"\n      reason: "r"\n',
            encoding="utf-8",
        )
        claude = project.root / ".claude"
        claude.mkdir()
        (claude / "CLAUDE.md").write_text(
            "# CLAUDE.md\n\n## 0.1 Project: invoice-svc\n\n"
            "<!-- beadloom:auto-start project-info -->\n"
            "- **Current version:** 0.0.0\n"
            "<!-- beadloom:auto-end -->\n",
            encoding="utf-8",
        )

        conn = sqlite3.connect(":memory:")
        try:
            drifts = check_config_drift(project.root, conn)
        finally:
            conn.close()

        assert [d.file for d in drifts] == [".beadloom/flow.yml"]
