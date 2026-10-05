"""Step implementations for `infrastructure/git-activity/activity_by_changed_lines.feature`.

BDL-078 F-activity (`beadloom-lw56`). Against a real git repository built by
:mod:`tests.support.squash_merged_repo` and the real ``git log``: nothing between
the history and the verdict is mocked.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.infrastructure.git_activity import analyze_git_activity
from tests.support.squash_merged_repo import CONTAINERS, SOURCES, build_squash_merged_repo

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../../../infrastructure/git-activity/activity_by_changed_lines.feature")


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    return {"root": tmp_path / "repo"}


@given("a repository whose history reaches main only through squash merges")
def _repo(world: dict[str, Any]) -> None:
    world["repo"] = build_squash_merged_repo(world["root"])


@when("its activity is analysed")
def _analyse(world: dict[str, Any]) -> None:
    repo = world["repo"]
    world["activity"] = analyze_git_activity(repo.root, SOURCES, CONTAINERS, now=repo.now)


@then(parsers.parse('the nodes "{a}", "{b}" and "{c}" each have {count:d} commit in 30 days'))
def _commits(world: dict[str, Any], a: str, b: str, c: str, count: int) -> None:
    for ref in (a, b, c):
        assert world["activity"][ref].commits_30d == count, ref


@then(parsers.parse('the node "{ref}" has {lines:d} lines changed in 30 days'))
def _lines(world: dict[str, Any], ref: str, lines: int) -> None:
    assert world["activity"][ref].lines_30d == lines


@then(
    parsers.parse(
        'the levels are "{hot}" hot, "{warm}" warm, "{cool}" cool, '
        '"{quiet}" quiet and "{dormant}" dormant'
    )
)
def _levels(
    world: dict[str, Any], hot: str, warm: str, cool: str, quiet: str, dormant: str
) -> None:
    levels = {ref: activity.activity_level for ref, activity in world["activity"].items()}
    expected = {hot: "hot", warm: "warm", cool: "cool", quiet: "quiet", dormant: "dormant"}
    assert {ref: levels[ref] for ref in expected} == expected


@then(parsers.parse('the node "{ref}" is {level} although none of its own files changed'))
def _box_level(world: dict[str, Any], ref: str, level: str) -> None:
    assert world["activity"][ref].activity_level == level
