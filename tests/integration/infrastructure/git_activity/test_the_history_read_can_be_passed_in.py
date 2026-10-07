"""``analyze_git_activity`` measures on the history its caller already read.

BDL-078 ``beadloom-btkd.18``, the review's minor m2 (``beadloom-ak1i``). A caller
that reports the history, as the full reindex does, reads it once and passes it
in, and the analysis judges the clone by that answer rather than asking git again.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from beadloom.infrastructure import git_activity
from beadloom.infrastructure.git_activity import GitHistory, Unread, analyze_git_activity
from tests.support.dated_history import (
    SOURCES,
    WEB_LINES_30D,
    build_dated_project,
    shallow_clone,
)

if TYPE_CHECKING:
    from pathlib import Path

_NOW = datetime.now(tz=timezone.utc)

#: The git question that opens every read of the history.
_SHALLOW_QUESTION = "--is-shallow-repository"


@pytest.fixture()
def origin(tmp_path: Path) -> Path:
    return build_dated_project(tmp_path / "origin", now=_NOW)


def test_a_history_that_does_not_reach_the_window_is_not_measured(origin: Path) -> None:
    told = GitHistory(shallow=True, commits=1, reaches_window=False)
    assert analyze_git_activity(origin, SOURCES, now=_NOW, history=told) == {}


def test_a_measurable_history_is_measured(origin: Path) -> None:
    told = GitHistory(shallow=False)
    activity = analyze_git_activity(origin, SOURCES, now=_NOW, history=told)
    assert activity["web"].lines_30d == WEB_LINES_30D


def _measured_asking(root: Path, history: GitHistory | Unread | None) -> tuple[bool, int]:
    """Whether *root* was measured with *history* passed in, and how often git was asked."""
    runner = git_activity._git_output
    asked: list[tuple[str, ...]] = []

    def counting(project_root: Path, *args: str, **kwargs: str) -> str | None:
        asked.append(args)
        return runner(project_root, *args, **kwargs)

    with patch.object(git_activity, "_git_output", counting):
        activity = analyze_git_activity(root, SOURCES, now=_NOW, history=history)
    return bool(activity), sum(1 for args in asked if _SHALLOW_QUESTION in args)


def test_git_saying_nothing_is_an_answer_too(origin: Path) -> None:
    """``None`` is what the read returns when git cannot say; it is not re-asked.

    The clone holds one commit, so asking again would answer that it does not reach
    the window and nothing would be measured: the activity is measured only when
    ``None`` is taken as the answer it is.
    """
    clone = shallow_clone(origin, origin.parent / "clone", 1)
    assert _measured_asking(clone, None) == (True, 0)


def test_a_caller_can_say_it_did_not_read_the_history(origin: Path) -> None:
    """``Unread.UNREAD``, the default, has the analysis read the history itself."""
    clone = shallow_clone(origin, origin.parent / "clone", 1)
    assert _measured_asking(clone, Unread.UNREAD) == (False, 1)
