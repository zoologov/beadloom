"""Activity counts changed lines, ranks nodes relative to the project, rolls boxes up.

BDL-078 F-activity (`beadloom-lw56`), owner's ruling 6. Every case below runs the
real ``git log`` over a repository built on disk, except the level rule itself,
which is a pure function over counts and is read directly.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

import pytest

from beadloom.infrastructure.git_activity import (
    ACTIVITY_LEVELS,
    GitActivity,
    analyze_git_activity,
    rank_activity_levels,
)
from tests.support.squash_merged_repo import (
    API_BRANCH_COMMITS,
    CONTAINERS,
    PARSER_LINES,
    SOURCES,
    UI_LINES,
    build_squash_merged_repo,
    commit_lines,
    init_repo,
    run_git,
)

if TYPE_CHECKING:
    from pathlib import Path

_NOW = datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# The squash-merged history
# ---------------------------------------------------------------------------


@pytest.fixture()
def squashed(tmp_path: Path) -> dict[str, GitActivity]:
    repo = build_squash_merged_repo(tmp_path / "repo", now=_NOW)
    return dict(analyze_git_activity(repo.root, SOURCES, CONTAINERS, now=repo.now))


def test_a_squash_counts_the_lines_of_every_commit_it_folded(
    squashed: dict[str, GitActivity],
) -> None:
    api = squashed["api"]
    assert api.commits_30d == 1
    assert api.lines_30d == API_BRANCH_COMMITS


def test_lines_tell_apart_what_one_commit_each_cannot(squashed: dict[str, GitActivity]) -> None:
    parser, ui = squashed["parser"], squashed["ui"]
    assert (parser.commits_30d, ui.commits_30d) == (1, 1)
    assert (parser.lines_30d, ui.lines_30d) == (PARSER_LINES, UI_LINES)
    assert parser.activity_level == "warm"
    assert ui.activity_level == "cool"


def test_a_box_rolls_up_lines_commits_and_dates_of_its_descendants(
    squashed: dict[str, GitActivity],
) -> None:
    app = squashed["app"]
    # parser 300 + api 10 + ui 2 in 30 days; config's 4 lines are 45 days old.
    assert app.lines_30d == PARSER_LINES + API_BRANCH_COMMITS + UI_LINES
    assert app.lines_90d == app.lines_30d + 4
    # Two squashes in 30 days, the config commit in 90; one commit touching two
    # descendants is one commit of the box.
    assert (app.commits_30d, app.commits_90d) == (2, 3)
    assert app.last_commit_date == (_NOW - timedelta(days=5)).date().isoformat()


def test_a_box_with_no_change_of_its_own_takes_its_parts_level(
    squashed: dict[str, GitActivity],
) -> None:
    core = squashed["core"]
    assert core.lines_30d == PARSER_LINES
    assert core.activity_level == "warm"


def test_no_change_in_30_days_is_quiet_and_none_in_90_is_dormant(
    squashed: dict[str, GitActivity],
) -> None:
    assert squashed["config"].activity_level == "quiet"
    assert squashed["config"].lines_90d == 4
    assert squashed["legacy"].activity_level == "dormant"


def test_without_containers_a_box_counts_only_its_own_files(tmp_path: Path) -> None:
    repo = build_squash_merged_repo(tmp_path / "repo", now=_NOW)
    flat = analyze_git_activity(repo.root, SOURCES, now=repo.now)
    assert flat["core"].lines_30d == 0
    assert flat["core"].activity_level == "dormant"


# ---------------------------------------------------------------------------
# The window, binary files and renames
# ---------------------------------------------------------------------------


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    init_repo(root)
    commit_lines(root, "a/seed.py", 1, when=_NOW - timedelta(days=200))
    return root


def test_the_30_day_window_is_exact(repo: Path) -> None:
    # 30 days and one hour ago is outside the window, though its whole-day delta is 30.
    commit_lines(repo, "a/x.py", 3, when=_NOW - timedelta(days=30, hours=1))
    commit_lines(repo, "b/x.py", 3, when=_NOW - timedelta(days=29, hours=23))
    activity = analyze_git_activity(repo, {"a": "a", "b": "b"}, now=_NOW)
    assert (activity["a"].commits_30d, activity["a"].lines_30d) == (0, 0)
    assert activity["a"].activity_level == "quiet"
    assert (activity["b"].commits_30d, activity["b"].lines_30d) == (1, 3)


def test_the_90_day_window_is_exact(repo: Path) -> None:
    commit_lines(repo, "a/x.py", 3, when=_NOW - timedelta(days=90, hours=1))
    commit_lines(repo, "b/x.py", 3, when=_NOW - timedelta(days=89, hours=23))
    activity = analyze_git_activity(repo, {"a": "a", "b": "b"}, now=_NOW)
    assert activity["a"].activity_level == "dormant"
    assert activity["b"].activity_level == "quiet"


def test_a_binary_file_is_a_change_of_zero_lines(repo: Path) -> None:
    blob = repo / "a" / "image.bin"
    blob.write_bytes(bytes(range(256)))
    run_git(repo, "add", "-A")
    run_git(repo, "commit", "-q", "-m", "binary", when=_NOW - timedelta(days=2))
    commit_lines(repo, "b/x.py", 7, when=_NOW - timedelta(days=2))

    activity = analyze_git_activity(repo, {"a": "a", "b": "b"}, now=_NOW)

    assert (activity["a"].commits_30d, activity["a"].lines_30d) == (1, 0)
    # A change of zero lines is a change, so not quiet, and ranks no higher than cool.
    assert activity["a"].activity_level == "cool"


def test_a_rename_counts_its_edits_at_the_new_path_and_its_commit_at_both(
    repo: Path,
) -> None:
    commit_lines(repo, "a/moved.py", 40, when=_NOW - timedelta(days=100))
    (repo / "b").mkdir()
    run_git(repo, "mv", "a/moved.py", "b/moved.py")
    with (repo / "b" / "moved.py").open("a", encoding="utf-8") as handle:
        handle.write("one more line\n")
    run_git(repo, "add", "-A")
    run_git(repo, "commit", "-q", "-m", "move", when=_NOW - timedelta(days=3))

    activity = analyze_git_activity(repo, {"a": "a", "b": "b"}, now=_NOW)

    # The move's 40 untouched lines are not changed lines; the one edit is, at b.
    assert activity["b"].lines_30d == 1
    assert activity["a"].lines_30d == 0
    assert activity["a"].commits_30d == activity["b"].commits_30d == 1


def test_a_container_without_a_source_passes_the_roll_up_through(repo: Path) -> None:
    commit_lines(repo, "top/mid/leaf/x.py", 9, when=_NOW - timedelta(days=1))
    activity = analyze_git_activity(
        repo,
        {"top": "top", "leaf": "top/mid/leaf"},
        {"leaf": ["mid"], "mid": ["top"]},
        now=_NOW,
    )
    assert "mid" not in activity
    assert activity["top"].lines_30d == 9


def test_a_containment_cycle_does_not_count_twice(repo: Path) -> None:
    commit_lines(repo, "a/x.py", 5, when=_NOW - timedelta(days=1))
    activity = analyze_git_activity(repo, {"a": "a", "b": "b"}, {"a": ["b"], "b": ["a"]}, now=_NOW)
    assert activity["a"].lines_30d == 5
    assert activity["b"].lines_30d == 5


# ---------------------------------------------------------------------------
# The level rule
# ---------------------------------------------------------------------------


def _ten_changed() -> dict[str, int]:
    return {f"n{i}": 100 - i for i in range(10)}


def test_the_levels_are_the_five_named() -> None:
    assert ACTIVITY_LEVELS == ("hot", "warm", "cool", "quiet", "dormant")


def test_the_top_tenth_is_hot_the_next_three_tenths_warm_the_rest_cool() -> None:
    changed = _ten_changed()
    levels = rank_activity_levels(changed, changed_90d=set(changed))
    assert [levels[f"n{i}"] for i in range(10)] == ["hot"] + ["warm"] * 3 + ["cool"] * 6


def test_quiet_and_dormant_come_from_the_90_day_window() -> None:
    levels = rank_activity_levels({"busy": 5}, changed_90d={"busy", "old"}, nodes={"old", "gone"})
    assert levels == {"busy": "hot", "old": "quiet", "gone": "dormant"}


def test_a_tie_shares_the_higher_level() -> None:
    changed = _ten_changed()
    changed["n1"] = changed["n0"]  # two nodes tie for first
    levels = rank_activity_levels(changed, changed_90d=set(changed))
    assert levels["n0"] == levels["n1"] == "hot"
    assert levels["n2"] == "warm"


@pytest.mark.parametrize(
    ("lines", "expected"),
    [
        ([7], ["hot"]),
        ([7, 3], ["hot", "cool"]),
        ([7, 3, 1], ["hot", "warm", "cool"]),
        ([9, 8, 7, 6, 5, 4, 3, 2, 1, 1, 1], ["hot", "hot"] + ["warm"] * 3 + ["cool"] * 6),
    ],
)
def test_the_cut_offs_round_up_so_the_busiest_node_is_always_hot(
    lines: list[int], expected: list[str]
) -> None:
    changed = {f"n{i}": count for i, count in enumerate(lines)}
    levels = rank_activity_levels(changed, changed_90d=set(changed))
    assert [levels[f"n{i}"] for i in range(len(lines))] == expected


def test_a_change_of_zero_lines_is_never_above_cool() -> None:
    levels = rank_activity_levels({"bin": 0, "other": 0}, changed_90d={"bin", "other"})
    assert levels == {"bin": "cool", "other": "cool"}
