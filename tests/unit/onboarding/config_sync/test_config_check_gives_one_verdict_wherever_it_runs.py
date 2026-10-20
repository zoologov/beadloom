"""`config-check` gives one verdict wherever the same files sit (BDL-083 S2c, RFC D7, #334).

Measured on 9.0.0 at ``f3d6f293`` over a copy of the monorepo fixture, whose root
carries no manifest that names the project: ``config-check`` rc 0 in the main
checkout, rc 1 in a ``git worktree`` of a clean HEAD and rc 1 in the clean room
``room-desk-ixbd``, each time ``.claude/CLAUDE.md: composed body is stale``. The
composition had taken the directory's name. A copy of the composed tree under a
second directory name is the shape all three share, so it is what these tests
build; the acceptance scenarios run the real worktree.
"""

from __future__ import annotations

import shutil
import sqlite3
from typing import TYPE_CHECKING

from beadloom.onboarding.agentic_flow_setup import scaffold
from beadloom.onboarding.composer import CLAUDE_ARTIFACT_NAME, PROJECT_FLOW_DIRNAME
from beadloom.onboarding.config_sync import check_config_drift, claude_md_comparison
from beadloom.onboarding.flow_config import FlowConfig, persist_flow_config
from beadloom.onboarding.project_name import PROJECT_HEADING_PREFIX, PROJECT_NAME_KEY

if TYPE_CHECKING:
    from pathlib import Path

    from beadloom.onboarding.config_sync import ConfigDrift

_CLAUDE = ".claude/CLAUDE.md"


def _composed(tmp_path: Path, directory: str, *, declared: str | None = None) -> Path:
    """A project composed in *directory*, whose root names the project in no manifest."""
    root = tmp_path / directory
    (root / ".beadloom").mkdir(parents=True)
    if declared is not None:
        (root / ".beadloom" / "config.yml").write_text(
            f"{PROJECT_NAME_KEY}: {declared}\n", encoding="utf-8"
        )
    fragment = root / PROJECT_FLOW_DIRNAME / "claude" / f"{CLAUDE_ARTIFACT_NAME}.md"
    fragment.parent.mkdir(parents=True)
    fragment.write_text("## Team rule\n\nTwo reviewers.\n", encoding="utf-8")
    config = FlowConfig(tools=("claude",), architecture="ddd", stack=("python",))
    persist_flow_config(root, config)
    scaffold(root, include_agents=True, config=config)
    return root


def _moved(root: Path, directory: str) -> Path:
    copy = root.parent / directory
    shutil.copytree(root, copy)
    return copy


def _blocking(root: Path) -> list[ConfigDrift]:
    drifts = check_config_drift(root, sqlite3.connect(":memory:"))
    return [d for d in drifts if d.severity == "error"]


def _heading(root: Path) -> str:
    text = (root / _CLAUDE).read_text(encoding="utf-8")
    return next(line for line in text.splitlines() if line.startswith(PROJECT_HEADING_PREFIX))


class TestTheSameFilesUnderAnotherDirectory:
    def test_a_project_that_declares_no_name_is_green_in_the_copy(self, tmp_path: Path) -> None:
        checkout = _composed(tmp_path, "desk-checkout")
        assert _blocking(checkout) == []
        assert _blocking(_moved(checkout, "room-desk-ixbd")) == []

    def test_a_declared_name_is_the_name_the_composition_takes(self, tmp_path: Path) -> None:
        checkout = _composed(tmp_path, "desk-checkout", declared="metrics-desk")
        assert _heading(checkout) == f"{PROJECT_HEADING_PREFIX}metrics-desk"
        assert _blocking(_moved(checkout, "room-desk-ixbd")) == []

    def test_recomposing_in_the_copy_keeps_the_recorded_name(self, tmp_path: Path) -> None:
        room = _moved(_composed(tmp_path, "desk-checkout"), "room-desk-ixbd")
        scaffold(room, include_agents=True)
        assert _heading(room) == f"{PROJECT_HEADING_PREFIX}desk-checkout"


class TestTheFindingNamesBothFiles:
    def test_a_newly_declared_name_is_stale_and_the_reason_names_both_files(
        self, tmp_path: Path
    ) -> None:
        root = _composed(tmp_path, "desk-checkout")
        (root / ".beadloom" / "config.yml").write_text(
            f"{PROJECT_NAME_KEY}: metrics-desk\n", encoding="utf-8"
        )
        [drift] = _blocking(root)
        assert drift.file == _CLAUDE
        assert ".beadloom/flow.yml" in drift.reason
        assert f"compared {_CLAUDE}" in drift.reason
        assert "'metrics-desk' from .beadloom/config.yml (project_name:)" in drift.reason


class TestTheComparisonIsNamedOnACleanRun:
    def test_names_the_compared_file_the_composition_and_the_name(self, tmp_path: Path) -> None:
        root = _composed(tmp_path, "desk-checkout", declared="metrics-desk")
        comparison = claude_md_comparison(root)
        assert comparison is not None
        assert comparison.compared == _CLAUDE
        assert comparison.composed_from == ".beadloom/flow.yml"
        assert comparison.name.value == "metrics-desk"
        text = comparison.describe()
        expected = f"compared {_CLAUDE} against its composition from .beadloom/flow.yml"
        assert text.startswith(expected)
        assert "project (.beadloom/flow/claude/CLAUDE.md)" in text
        assert "not compared" not in text

    def test_an_undeclared_name_is_said_to_be_not_compared(self, tmp_path: Path) -> None:
        room = _moved(_composed(tmp_path, "desk-checkout"), "room-desk-ixbd")
        comparison = claude_md_comparison(room)
        assert comparison is not None
        assert comparison.name.value == "desk-checkout"
        assert "not compared" in comparison.describe()
        assert f"`{PROJECT_NAME_KEY}:`" in comparison.describe()

    def test_a_project_without_a_composed_claude_md_has_no_comparison(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "bare"
        root.mkdir()
        assert claude_md_comparison(root) is None
