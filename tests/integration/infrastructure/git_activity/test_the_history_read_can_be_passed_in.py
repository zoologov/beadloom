"""``analyze_git_activity`` measures on the history its caller already read.

BDL-078 ``beadloom-btkd.18``, the review's minor m2 (``beadloom-ak1i``). A caller
that reports the history, as the full reindex does, reads it once and passes it
in, and the analysis judges the clone by that answer rather than asking git again.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

import pytest

from beadloom.infrastructure.git_activity import GitHistory, analyze_git_activity
from tests.support.dated_history import SOURCES, WEB_LINES_30D, build_dated_project

if TYPE_CHECKING:
    from pathlib import Path

_NOW = datetime.now(tz=timezone.utc)


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


def test_git_saying_nothing_is_an_answer_too(origin: Path) -> None:
    """``None`` is what the read returns when git cannot say; it is not re-asked."""
    activity = analyze_git_activity(origin, SOURCES, now=_NOW, history=None)
    assert activity["web"].lines_30d == WEB_LINES_30D
