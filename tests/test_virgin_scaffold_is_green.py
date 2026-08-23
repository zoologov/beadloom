"""A first `setup-agentic-flow` must not hand the adopter four errors (BDL-UX #187).

Measured on a fresh TypeScript project: `beadloom setup-agentic-flow` with no
flags composed the four role adapters from an auto-detected config it never
wrote down, and the very next command the scaffold's own closing advice
recommends — `beadloom config-check` — exited 1 with one error per role, each
advising the reader to "add a flow.yml (`beadloom setup-agentic-flow`)". That is
the command they had just run.

It is also the shape this slice exists to prevent, arrived at from the other
end: an untouched repository that is red on first contact.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from click.testing import CliRunner

from beadloom.onboarding.flow_config import FLOW_CONFIG_RELPATH, load_flow_config
from beadloom.services.cli import main
from tests.adopter_project import typescript_project

if TYPE_CHECKING:
    from pathlib import Path


def _scaffolded(project_root: Path, *extra: str) -> CliRunner:
    runner = CliRunner()
    init = runner.invoke(
        main, ["init", "--yes", "--mode", "bootstrap", "--project", str(project_root)]
    )
    assert init.exit_code == 0, init.output
    result = runner.invoke(
        main, ["setup-agentic-flow", "--project", str(project_root), *extra]
    )
    assert result.exit_code == 0, result.output
    return runner


class TestAVirginScaffoldIsGreen:
    def test_config_check_is_clean_straight_after_the_first_scaffold(
        self, tmp_path: Path
    ) -> None:
        project = typescript_project(tmp_path / "orders-web")
        runner = _scaffolded(project.root)

        result = runner.invoke(main, ["config-check", "--project", str(project.root)])

        assert result.exit_code == 0, result.output

    def test_the_scaffold_writes_down_the_configuration_it_resolved(
        self, tmp_path: Path
    ) -> None:
        """The selection was real; it was simply never recorded anywhere."""
        project = typescript_project(tmp_path / "orders-web")
        _scaffolded(project.root)

        assert (project.root / FLOW_CONFIG_RELPATH).is_file()
        config = load_flow_config(project.root)
        assert config.stack == ("typescript",)

    def test_an_explicit_flag_reaches_the_composed_claude_md_too(
        self, tmp_path: Path
    ) -> None:
        """`--architecture fsd` used to reach the roles and not `CLAUDE.md`.

        `scaffold()` re-resolved the config from disk without the flags, so a
        flagged run composed the role adapters for one architecture and the
        commands + `CLAUDE.md` for another.
        """
        project = typescript_project(tmp_path / "shop-front")
        _scaffolded(project.root, "--architecture", "fsd")

        assert load_flow_config(project.root).architecture == "fsd"
        dev = (project.root / ".claude" / "agents" / "dev.md").read_text(
            encoding="utf-8"
        )
        assert "Feature-Sliced Design" in dev or "FSD" in dev

    def test_an_existing_flow_yml_is_never_overwritten(self, tmp_path: Path) -> None:
        """It is the adopter's policy file — language and suppressions live there."""
        project = typescript_project(tmp_path / "orders-web")
        (project.root / ".beadloom").mkdir(parents=True, exist_ok=True)
        declared = "tools: [claude]\narchitecture: [ddd]\nstack: [typescript]\nlanguage: de\n"
        (project.root / FLOW_CONFIG_RELPATH).write_text(declared, encoding="utf-8")

        _scaffolded(project.root)

        assert (project.root / FLOW_CONFIG_RELPATH).read_text(encoding="utf-8") == declared
