"""A full reindex reads the clone's history once, at the instant it measures with.

BDL-078 ``beadloom-btkd.18``, the review's minor m2 (``beadloom-ak1i``). The
reindex asked ``analyze_git_activity`` for the activity, which read the history
to decide whether the clone was measurable, and then read the history again to
return it: three to four more git processes on a shallow clone, and the second
read took its own "now", so the history the reindex reported and the one the
activity was measured on could straddle the edge of the 90-day window.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest

from beadloom.application.reindex import reindex
from beadloom.infrastructure import git_activity
from tests.support.dated_history import build_dated_project, shallow_clone

if TYPE_CHECKING:
    from pathlib import Path

_NOW = datetime.now(tz=timezone.utc)

#: The git question that opens every read of the history.
_SHALLOW_QUESTION = "--is-shallow-repository"


@pytest.fixture()
def origin(tmp_path: Path) -> Path:
    return build_dated_project(tmp_path / "origin", now=_NOW)


def _history_reads(root: Path) -> int:
    """How many times a full reindex of *root* asked git how much history it holds."""
    runner = git_activity._git_output
    asked: list[tuple[str, ...]] = []

    def counting(project_root: Path, *args: str, **kwargs: str) -> str | None:
        asked.append(args)
        return runner(project_root, *args, **kwargs)

    with patch.object(git_activity, "_git_output", counting):
        reindex(root)
    return sum(1 for args in asked if _SHALLOW_QUESTION in args)


class TestOneReadOfTheHistory:
    def test_on_a_full_history(self, origin: Path) -> None:
        assert _history_reads(origin) == 1

    def test_on_a_shallow_history(self, origin: Path) -> None:
        clone = shallow_clone(origin, origin.parent / "clone", 3)
        assert _history_reads(clone) == 1


class TestOneInstant:
    def test_the_history_reported_is_the_one_measured_on(self, origin: Path) -> None:
        """The activity is measured at the instant the reported history was read at."""
        reader = git_activity.read_git_history
        read_at: list[datetime | None] = []

        def recording(project_root: Path, *, now: datetime | None = None) -> object:
            read_at.append(now)
            return reader(project_root, now=now)

        analyzer = git_activity.analyze_git_activity
        measured_at: list[datetime | None] = []

        def measuring(*args: Any, **kwargs: Any) -> Any:
            measured_at.append(kwargs.get("now"))
            return analyzer(*args, **kwargs)

        with (
            patch("beadloom.application.reindex.enrichment.read_git_history", recording),
            patch("beadloom.application.reindex.analyze_git_activity", measuring),
        ):
            reindex(origin)

        assert len(read_at) == 1
        assert read_at[0] is not None
        assert measured_at == read_at
