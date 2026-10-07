"""Activity is said in one set of words, and one of a thing is singular.

BDL-078 ``beadloom-btkd.18``, the review's minor m3 (``beadloom-ak1i``). The words
for a level with no change were written out twice, in ``ctx``'s markdown and in
the TUI's widget, and both said "1 lines" for one line. The words now live beside
the levels they describe, and each reader takes them from there.
"""

from __future__ import annotations

import pytest

from beadloom.infrastructure.git_activity import (
    ACTIVITY_LEVELS,
    HISTORY_DAYS,
    NO_CHANGE_WORDS,
    RECENT_DAYS,
    count_in_words,
)


@pytest.mark.parametrize(
    ("count", "noun", "words"),
    [
        (0, "line", "0 lines"),
        (1, "line", "1 line"),
        (2, "line", "2 lines"),
        (1, "commit", "1 commit"),
        (340, "commit", "340 commits"),
    ],
)
def test_a_count_is_singular_for_one_only(count: int, noun: str, words: str) -> None:
    assert count_in_words(count, noun) == words


def test_the_levels_without_change_name_their_window() -> None:
    expected = {
        "quiet": f"no change in {RECENT_DAYS} days",
        "dormant": f"no change in {HISTORY_DAYS} days",
    }
    assert expected == NO_CHANGE_WORDS


def test_only_levels_are_worded() -> None:
    assert set(NO_CHANGE_WORDS) <= set(ACTIVITY_LEVELS)
