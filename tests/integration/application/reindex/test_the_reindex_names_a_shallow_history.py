"""The reindex and the Gate say what history activity was measured on.

BDL-078 ``beadloom-btkd.9``, from T's finding F1 (``beadloom-q63p``). The
portal this repository publishes was indexed from a clone one commit deep, and
nothing in the reindex's or the Gate's output said so: the levels it recorded
were ranked on the size of each node's files. A full reindex now carries the
history it read, the command line prints it when the history is shallow, and the
Gate's reindex step warns when activity could not be measured on it.
"""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner

from beadloom.application.gate import run_ci_gate
from beadloom.application.reindex import reindex
from beadloom.infrastructure.git_activity import GitHistory
from beadloom.services.cli import main
from tests.support.dated_history import build_dated_project, shallow_clone

if TYPE_CHECKING:
    from pathlib import Path

_NOW = datetime.now(tz=timezone.utc)


@pytest.fixture()
def origin(tmp_path: Path) -> Path:
    return build_dated_project(tmp_path / "origin", now=_NOW)


def _reindex_step(root: Path) -> tuple[str, str]:
    result = run_ci_gate(root, fail_on=None, hub_exports=[], no_reindex=False)
    step = next(step for step in result.steps if step.name == "reindex")
    return step.status, step.summary


class TestTheFullReindexCarriesTheHistory:
    def test_on_a_full_history(self, origin: Path) -> None:
        assert reindex(origin).activity_history == GitHistory(shallow=False)

    def test_on_a_clone_one_commit_deep(self, origin: Path) -> None:
        clone = shallow_clone(origin, origin.parent / "clone", 1)
        assert reindex(clone).activity_history == GitHistory(
            shallow=True, commits=1, reaches_window=False
        )

    def test_outside_git_it_carries_none(self, origin: Path, tmp_path: Path) -> None:
        plain = tmp_path / "plain"
        shutil.copytree(origin, plain, ignore=shutil.ignore_patterns(".git"))
        assert reindex(plain).activity_history is None


class TestTheCommandLine:
    def test_a_full_history_prints_no_activity_line(self, origin: Path) -> None:
        output = CliRunner().invoke(main, ["reindex", "--project", str(origin)]).output
        assert "Activity:" not in output, output


class TestTheGate:
    def test_a_full_history_keeps_the_step_as_it_was(self, origin: Path) -> None:
        assert _reindex_step(origin) == ("PASS", "reindexed")

    def test_a_shallow_history_that_reaches_the_window_passes_and_says_so(
        self, origin: Path
    ) -> None:
        clone = shallow_clone(origin, origin.parent / "clone", 3)
        assert _reindex_step(clone) == (
            "PASS",
            "reindexed; activity measured on history: shallow (3 commits), "
            "which reaches back 90 days",
        )
