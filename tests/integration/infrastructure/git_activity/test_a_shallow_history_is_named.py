"""Activity is measured on the history a clone holds, and a shallow one is named.

BDL-078 ``beadloom-btkd.9``, from T's finding F1 (``beadloom-q63p``). A clone one
commit deep shows that commit as adding every file, so before this bead every
node of such a clone read "1 commit", lines equal to the size of its files, and
levels ranked on those sizes. MEASURED on a clone of this repository one commit
deep: 3 levels populated (hot 14, warm 39, cool 77) where its full history
populates 5 (hot 11, warm 28, cool 56, quiet 21, dormant 14).

A shallow clone is told apart by where its first commit lies: inside the 90-day
window the clone cannot say what changed in it, and nothing is recorded; before
the window every change the window needs is there, and it is measured.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

import pytest

from beadloom.infrastructure.git_activity import (
    GitHistory,
    activity_history_note,
    analyze_git_activity,
    read_git_history,
)
from tests.support.dated_history import (
    SOURCES,
    WEB_LINES_30D,
    build_dated_project,
    shallow_clone,
)

if TYPE_CHECKING:
    from pathlib import Path

_NOW = datetime.now(tz=timezone.utc)


@pytest.fixture()
def origin(tmp_path: Path) -> Path:
    return build_dated_project(tmp_path / "origin", now=_NOW)


def _clone(origin: Path, depth: int) -> Path:
    return shallow_clone(origin, origin.parent / f"clone-{depth}", depth)


class TestTheHistoryACloneHolds:
    def test_a_full_history_is_not_shallow(self, origin: Path) -> None:
        history = read_git_history(origin, now=_NOW)
        assert history == GitHistory(shallow=False)
        assert history.measurable

    def test_a_clone_one_commit_deep_does_not_reach_the_window(self, origin: Path) -> None:
        history = read_git_history(_clone(origin, 1), now=_NOW)
        assert history == GitHistory(shallow=True, commits=1, reaches_window=False)
        assert not history.measurable
        assert history.describe() == "history: shallow (1 commit)"

    def test_a_clone_whose_first_commit_is_inside_the_window_does_not_reach_it(
        self, origin: Path
    ) -> None:
        """Depth 2 starts at the commit 45 days old: the window's first 45 days are missing."""
        history = read_git_history(_clone(origin, 2), now=_NOW)
        assert history == GitHistory(shallow=True, commits=2, reaches_window=False)

    def test_a_clone_whose_first_commit_is_before_the_window_reaches_it(
        self, origin: Path
    ) -> None:
        history = read_git_history(_clone(origin, 3), now=_NOW)
        assert history == GitHistory(shallow=True, commits=3, reaches_window=True)
        assert history.measurable
        assert history.describe() == "history: shallow (3 commits)"

    def test_outside_git_nothing_is_said(self, tmp_path: Path) -> None:
        assert read_git_history(tmp_path, now=_NOW) is None


class TestActivityOnAShallowHistory:
    def test_a_clone_one_commit_deep_records_no_activity(self, origin: Path) -> None:
        """Before: web 352 lines (its file's size), api 8 (its file's size), both 1 commit."""
        assert analyze_git_activity(_clone(origin, 1), SOURCES, now=_NOW) == {}

    def test_a_clone_starting_inside_the_window_records_no_activity(self, origin: Path) -> None:
        assert analyze_git_activity(_clone(origin, 2), SOURCES, now=_NOW) == {}

    def test_a_clone_reaching_past_the_window_is_measured_as_the_full_history(
        self, origin: Path
    ) -> None:
        full = analyze_git_activity(origin, SOURCES, now=_NOW)
        assert full["web"].lines_30d == WEB_LINES_30D
        assert full["api"].activity_level == "quiet"
        assert analyze_git_activity(_clone(origin, 3), SOURCES, now=_NOW) == full


class TestTheNote:
    def test_a_full_history_needs_no_note(self) -> None:
        assert activity_history_note(GitHistory(shallow=False)) == ""
        assert activity_history_note(None) == ""

    def test_a_history_that_does_not_reach_the_window_says_activity_was_not_measured(
        self,
    ) -> None:
        note = activity_history_note(GitHistory(shallow=True, commits=1, reaches_window=False))
        assert note == (
            "not measured on history: shallow (1 commit), which does not reach back 90 days; "
            "check out the full history (actions/checkout fetch-depth: 0)"
        )

    def test_a_history_that_reaches_the_window_says_what_it_was_measured_on(self) -> None:
        note = activity_history_note(GitHistory(shallow=True, commits=412, reaches_window=True))
        assert note == "measured on history: shallow (412 commits), which reaches back 90 days"
