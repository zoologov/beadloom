"""`config-check` and the Gate's step name what they compared (BDL-083 S2c, RFC D7, #334).

The entry's last clause: on 9.0.0 the verdict over ``.claude/CLAUDE.md`` named
neither the composition it was compared against nor the file it read, so a
red in a ``git worktree`` beside a green in the checkout gave a reader nothing
to compare. Both surfaces now print the sentence
:meth:`~beadloom.onboarding.config_sync.ClaudeComparison.describe` writes, on a
clean run too.
"""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

from click.testing import CliRunner

from beadloom.application.gate import _step_config_check
from beadloom.infrastructure.db import connection
from beadloom.onboarding.agentic_flow_setup import scaffold
from beadloom.onboarding.flow_config import FlowConfig, persist_flow_config
from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path


def _composed(tmp_path: Path) -> Path:
    """A project composed in ``desk-checkout`` that names itself in no file."""
    root = tmp_path / "desk-checkout"
    (root / ".beadloom").mkdir(parents=True)
    config = FlowConfig(tools=("claude",), architecture="ddd", stack=("python",))
    persist_flow_config(root, config)
    scaffold(root, include_agents=True, config=config)
    with connection(root / ".beadloom" / "beadloom.db"):
        pass
    return root


def _room(root: Path) -> Path:
    room = root.parent / "room-desk-ixbd"
    shutil.copytree(root, room)
    return room


class TestTheCommand:
    def test_a_room_of_the_checkout_exits_0_and_names_both_files(self, tmp_path: Path) -> None:
        room = _room(_composed(tmp_path))
        result = CliRunner().invoke(main, ["config-check", "--project", str(room)])
        assert result.exit_code == 0, result.output
        assert (
            "compared .claude/CLAUDE.md against its composition from .beadloom/flow.yml"
            in result.output
        )
        assert "'desk-checkout' from .claude/CLAUDE.md" in result.output


class TestTheGateStep:
    def test_the_summary_names_both_files(self, tmp_path: Path) -> None:
        step = _step_config_check(_room(_composed(tmp_path)))
        assert step.passed, step.findings
        assert "compared .claude/CLAUDE.md against its composition from .beadloom/flow.yml" in (
            step.summary
        )
