"""What the scaffold FINDS must reach the terminal, not just the caller (BDL-UX #188).

``orphaned_flow_files()`` and ``ScaffoldResult.migration_notes`` were computed on
every ``beadloom setup-agentic-flow`` run and read by nothing outside the
library. BDL-UX #137 was recorded closed *by the orphan report*, and BDL-061 S3's
criterion "a hand-edited vendored file is reported with migration guidance" was
recorded as met — both true of ``scaffold()`` and false of the command. The
standing rule is NO CALLER, NO CAPABILITY: a function nothing calls reads as
"the feature exists".
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from click.testing import CliRunner

from beadloom.services.cli import main
from tests.adopter_project import typescript_project

if TYPE_CHECKING:
    from pathlib import Path


def _init_and_scaffold(project_root: Path) -> CliRunner:
    runner = CliRunner()
    assert (
        runner.invoke(
            main,
            ["init", "--yes", "--mode", "bootstrap", "--project", str(project_root)],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            main, ["setup-agentic-flow", "--project", str(project_root)]
        ).exit_code
        == 0
    )
    return runner


class TestTheScaffoldPrintsWhatItFound:
    def test_a_prior_layouts_orphans_are_named_with_their_cleanup_command(
        self, tmp_path: Path
    ) -> None:
        project = typescript_project(tmp_path / "orders-web")
        runner = _init_and_scaffold(project.root)
        commands = project.root / ".claude" / "commands"
        commands.mkdir(parents=True, exist_ok=True)
        for stale in ("dev", "test", "review", "tech-writer", "epic-init"):
            (commands / f"{stale}.md").write_text("# old layout\n", encoding="utf-8")

        result = runner.invoke(
            main, ["setup-agentic-flow", "--project", str(project.root)]
        )

        assert result.exit_code == 0
        assert ".claude/commands/epic-init.md" in result.output
        assert "rm -f .claude/commands/dev.md" in result.output

    def test_a_hand_edit_is_told_where_the_edit_belongs_not_to_use_force(
        self, tmp_path: Path
    ) -> None:
        project = typescript_project(tmp_path / "orders-web")
        runner = _init_and_scaffold(project.root)
        coordinator = project.root / ".claude" / "commands" / "coordinator.md"
        coordinator.write_text(
            coordinator.read_text(encoding="utf-8") + "\n## Our standing practice\n",
            encoding="utf-8",
        )

        result = runner.invoke(
            main, ["setup-agentic-flow", "--project", str(project.root)]
        )

        assert result.exit_code == 0
        assert ".beadloom/flow/commands/coordinator.md" in result.output
        # The old message advised the destructive flag and named nowhere safe.
        assert "use --force" not in result.output
