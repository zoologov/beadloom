"""Steps for `activity_ranks_boxes_apart_and_skips_machine_written_files.feature`.

BDL-078 ``beadloom-btkd.1``. Real git repositories on disk, the real ``git log``
and ``git check-attr``, and for the project's own patterns the real reindex
reading ``.beadloom/config.yml``: nothing between the history and the verdict
is mocked.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.application.reindex import reindex
from beadloom.infrastructure.db import open_db
from beadloom.infrastructure.git_activity import analyze_git_activity
from tests.support.squash_merged_repo import (
    CONTAINERS,
    SOURCES,
    build_squash_merged_repo,
    commit_lines,
    init_repo,
    run_git,
)

if TYPE_CHECKING:
    from pathlib import Path

scenarios(
    "../../../infrastructure/git-activity/"
    "activity_ranks_boxes_apart_and_skips_machine_written_files.feature"
)

#: The real present: the reindex measures its windows from it, so the history does too.
_NOW = datetime.now(tz=timezone.utc)
_NODES = {"web": "web", "gen": "gen"}


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    return {"root": tmp_path / "repo"}


def _seeded(world: dict[str, Any]) -> Path:
    root: Path = world["root"]
    if not (root / ".git").exists():
        init_repo(root)
        commit_lines(root, "seed.txt", 1, when=_NOW - timedelta(days=200))
    return root


def _commit(root: Path, files: dict[str, int]) -> None:
    for rel, lines in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(f"line {i}\n" for i in range(lines)), encoding="utf-8")
    run_git(root, "add", "-A")
    run_git(root, "commit", "-q", "-m", "change", when=_NOW - timedelta(days=2))


@given("a repository whose history reaches main only through squash merges")
def _squashed(world: dict[str, Any]) -> None:
    repo = build_squash_merged_repo(world["root"], now=_NOW)
    world["sources"], world["containers"] = SOURCES, CONTAINERS
    world["root"] = repo.root


@given(
    parsers.parse(
        'a repository where one commit adds {code:d} lines to "{code_path}" '
        'and {lock:d} to "{lock_path}"'
    )
)
def _lock_commit(
    world: dict[str, Any], code: int, code_path: str, lock: int, lock_path: str
) -> None:
    _commit(_seeded(world), {code_path: code, lock_path: lock})


@given(parsers.parse('a repository whose ".gitattributes" marks "{pattern}" linguist-generated'))
def _attributes(world: dict[str, Any], pattern: str) -> None:
    root = _seeded(world)
    (root / ".gitattributes").write_text(f"{pattern} linguist-generated\n", encoding="utf-8")


@given(parsers.parse('one commit adds {lines:d} lines to "{path}" only'))
def _one_file(world: dict[str, Any], lines: int, path: str) -> None:
    _commit(_seeded(world), {path: lines})


@given(parsers.parse('a project whose config excludes "{pattern}" from activity'))
def _project(world: dict[str, Any], pattern: str) -> None:
    root = _seeded(world)
    (root / ".beadloom" / "_graph").mkdir(parents=True)
    (root / "docs").mkdir()
    (root / ".beadloom" / "config.yml").write_text(
        f"scan_paths:\n- src\nactivity:\n  exclude:\n    - '{pattern}'\n", encoding="utf-8"
    )
    (root / ".beadloom" / "_graph" / "nodes.yml").write_text(
        'nodes:\n  - ref_id: proto\n    kind: feature\n    summary: "proto"\n'
        "    source: src/proto\n",
        encoding="utf-8",
    )


@given(
    parsers.parse(
        'one commit adds {first:d} lines to "{first_path}" and {second:d} to "{second_path}"'
    )
)
def _two_files(
    world: dict[str, Any], first: int, first_path: str, second: int, second_path: str
) -> None:
    _commit(_seeded(world), {first_path: first, second_path: second})


@when("its activity is analysed")
def _analyse(world: dict[str, Any]) -> None:
    world["activity"] = analyze_git_activity(
        world["root"],
        world.get("sources", _NODES),
        world.get("containers"),
        now=_NOW,
    )


@when("the project is reindexed")
def _reindex(world: dict[str, Any]) -> None:
    reindex(world["root"])
    conn = open_db(world["root"] / ".beadloom" / "beadloom.db")
    world["stored"] = {
        str(row["ref_id"]): json.loads(row["extra"] or "{}").get("activity")
        for row in conn.execute("SELECT ref_id, extra FROM nodes")
    }
    conn.close()


def _level(world: dict[str, Any], ref: str) -> str:
    return str(world["activity"][ref].activity_level)


@then(parsers.parse('among the boxes "{first}" is {first_level} and "{second}" is {second_level}'))
def _boxes(
    world: dict[str, Any], first: str, first_level: str, second: str, second_level: str
) -> None:
    assert (_level(world, first), _level(world, second)) == (first_level, second_level)


@then(parsers.parse('among the leaves "{a}" is {a_level}, "{b}" {b_level} and "{c}" {c_level}'))
def _leaves(
    world: dict[str, Any], a: str, a_level: str, b: str, b_level: str, c: str, c_level: str
) -> None:
    levels = (_level(world, a), _level(world, b), _level(world, c))
    assert levels == (a_level, b_level, c_level)


@then(parsers.parse('the node "{ref}" has {lines:d} lines changed in 30 days'))
def _lines(world: dict[str, Any], ref: str, lines: int) -> None:
    assert world["activity"][ref].lines_30d == lines


@then(parsers.parse('the node "{ref}" has no change in 90 days'))
def _no_change(world: dict[str, Any], ref: str) -> None:
    activity = world["activity"][ref]
    assert (activity.commits_90d, activity.lines_90d) == (0, 0)
    assert activity.activity_level == "dormant"


@then(parsers.parse('the stored activity of "{ref}" has {lines:d} lines changed in 30 days'))
def _stored(world: dict[str, Any], ref: str, lines: int) -> None:
    assert world["stored"][ref]["lines_30d"] == lines
