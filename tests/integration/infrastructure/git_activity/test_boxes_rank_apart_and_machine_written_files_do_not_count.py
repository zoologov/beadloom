"""Boxes rank among boxes, leaves among leaves; a file a machine wrote is not change.

BDL-078 ``beadloom-btkd.1``, the owner's two rulings after F-activity:

1. A box rolls up its parts, so in one population with the leaves it outranks
   them: on this repository 7 of the 10 ``hot`` nodes were boxes. A box (a node
   that contains another) is ranked among boxes, a leaf among leaves, by the same
   tenths.
2. A dependency lock file, a file git marks ``linguist-generated`` or
   ``binary``, and a file matching a pattern the project declares are not
   change: neither their lines nor their commits count.

Every case runs the real ``git log`` and ``git check-attr`` over a repository
built on disk, except the level rule, which is a pure function over counts.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

import pytest

from beadloom.infrastructure.git_activity import (
    LOCK_FILES,
    analyze_git_activity,
    rank_activity_levels,
)
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

_NOW = datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc)
_RECENT = _NOW - timedelta(days=2)


# ---------------------------------------------------------------------------
# Boxes among boxes, leaves among leaves
# ---------------------------------------------------------------------------


def test_a_box_is_ranked_among_boxes_and_a_leaf_among_leaves() -> None:
    # One population would make both boxes hot or warm and push every leaf down.
    changed = {"big-box": 900, "small-box": 400, "leaf-a": 300, "leaf-b": 20, "leaf-c": 1}
    levels = rank_activity_levels(
        changed, changed_90d=set(changed), boxes={"big-box", "small-box"}
    )
    assert levels == {
        "big-box": "hot",
        "small-box": "cool",
        "leaf-a": "hot",
        "leaf-b": "warm",
        "leaf-c": "cool",
    }


def test_each_population_takes_its_own_tenths() -> None:
    boxes = {f"box{i}": 1000 - i for i in range(10)}
    leaves = {f"leaf{i}": 10 - i for i in range(10)}
    levels = rank_activity_levels(
        {**boxes, **leaves}, changed_90d={*boxes, *leaves}, boxes=set(boxes)
    )
    expected = ["hot"] + ["warm"] * 3 + ["cool"] * 6
    assert [levels[f"box{i}"] for i in range(10)] == expected
    assert [levels[f"leaf{i}"] for i in range(10)] == expected


def test_a_box_with_no_change_is_quiet_or_dormant_like_a_leaf() -> None:
    levels = rank_activity_levels(
        {"leaf": 5},
        changed_90d={"leaf", "old-box"},
        nodes={"gone-box"},
        boxes={"old-box", "gone-box"},
    )
    assert levels == {"leaf": "hot", "old-box": "quiet", "gone-box": "dormant"}


def test_a_leaf_is_not_pushed_down_by_the_boxes_that_hold_it(tmp_path: Path) -> None:
    repo = build_squash_merged_repo(tmp_path / "repo", now=_NOW)
    activity = analyze_git_activity(repo.root, SOURCES, CONTAINERS, now=repo.now)
    levels = {ref: activity[ref].activity_level for ref in SOURCES}
    # Boxes app (312 lines) and core (300); leaves parser 300, api 10, ui 2.
    assert levels == {
        "app": "hot",
        "core": "cool",
        "parser": "hot",
        "api": "warm",
        "ui": "cool",
        "config": "quiet",
        "legacy": "dormant",
    }


# ---------------------------------------------------------------------------
# Files a machine wrote
# ---------------------------------------------------------------------------


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    init_repo(root)
    commit_lines(root, "web/seed.js", 1, when=_NOW - timedelta(days=200))
    commit_lines(root, "deps/seed.py", 1, when=_NOW - timedelta(days=200))
    return root


def _write(root: Path, rel: str, lines: int) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(f"line {i}\n" for i in range(lines)), encoding="utf-8")


def _commit(root: Path, files: dict[str, int], *, when: datetime = _RECENT) -> None:
    for rel, lines in files.items():
        _write(root, rel, lines)
    run_git(root, "add", "-A")
    run_git(root, "commit", "-q", "-m", "change", when=when)


_NODES = {"web": "web", "deps": "deps"}


def test_the_owners_lock_files_are_all_known() -> None:
    named = {
        "package-lock.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        "uv.lock",
        "poetry.lock",
        "Cargo.lock",
        "go.sum",
        "Gemfile.lock",
        "composer.lock",
        "Package.resolved",
        "gradle.lockfile",
    }
    assert named <= LOCK_FILES


def test_a_lock_file_beside_authored_code_adds_no_lines(repo: Path) -> None:
    _commit(repo, {"web/app.js": 5, "web/package-lock.json": 4000})
    activity = analyze_git_activity(repo, _NODES, now=_NOW)
    assert activity["web"].lines_30d == 5
    assert activity["web"].commits_30d == 1


@pytest.mark.parametrize("name", sorted(LOCK_FILES))
def test_a_change_only_to_a_lock_file_is_no_change(repo: Path, name: str) -> None:
    _commit(repo, {f"deps/nested/{name}": 50})
    activity = analyze_git_activity(repo, _NODES, now=_NOW)
    deps = activity["deps"]
    assert (deps.commits_30d, deps.commits_90d, deps.lines_30d) == (0, 0, 0)
    assert deps.activity_level == "dormant"


def test_a_file_named_like_a_lock_file_only_in_part_still_counts(repo: Path) -> None:
    _commit(repo, {"deps/my-yarn.lock.md": 6})
    assert analyze_git_activity(repo, _NODES, now=_NOW)["deps"].lines_30d == 6


def test_a_file_git_marks_linguist_generated_is_no_change(repo: Path) -> None:
    (repo / ".gitattributes").write_text("deps/gen/* linguist-generated\n", encoding="utf-8")
    _commit(repo, {"deps/gen/client.py": 700, "web/app.js": 3})
    activity = analyze_git_activity(repo, _NODES, now=_NOW)
    assert activity["deps"].activity_level == "dormant"
    assert activity["web"].lines_30d == 3


def test_linguist_generated_false_is_change(repo: Path) -> None:
    (repo / ".gitattributes").write_text("deps/gen/* linguist-generated=false\n", encoding="utf-8")
    _commit(repo, {"deps/gen/client.py": 7})
    assert analyze_git_activity(repo, _NODES, now=_NOW)["deps"].lines_30d == 7


def test_a_file_git_marks_binary_is_no_change(repo: Path) -> None:
    (repo / ".gitattributes").write_text("*.dat binary\n", encoding="utf-8")
    run_git(repo, "add", "-A")
    run_git(repo, "commit", "-q", "-m", "attributes", when=_NOW - timedelta(days=150))
    _commit(repo, {"deps/table.dat": 30})
    activity = analyze_git_activity(repo, _NODES, now=_NOW)
    assert activity["deps"].commits_30d == 0
    assert activity["deps"].activity_level == "dormant"


def test_a_file_name_pattern_the_project_declares_is_no_change(repo: Path) -> None:
    _commit(repo, {"deps/api.pb.go": 900, "deps/api.go": 4})
    activity = analyze_git_activity(repo, _NODES, now=_NOW, excluded=("*.pb.go",))
    assert activity["deps"].lines_30d == 4


def test_a_path_pattern_the_project_declares_is_no_change(repo: Path) -> None:
    _commit(repo, {"web/dist/bundle.js": 900, "web/dist/sub/chunk.js": 90, "web/app.js": 2})
    activity = analyze_git_activity(repo, _NODES, now=_NOW, excluded=("web/dist/*",))
    assert activity["web"].lines_30d == 2


def test_a_project_pattern_matches_the_whole_path_not_a_part(repo: Path) -> None:
    _commit(repo, {"web/other/dist/bundle.js": 9})
    activity = analyze_git_activity(repo, _NODES, now=_NOW, excluded=("dist/*",))
    assert activity["web"].lines_30d == 9


def test_a_lock_file_does_not_reach_a_box_through_the_roll_up(repo: Path) -> None:
    _commit(repo, {"web/package-lock.json": 4000, "deps/x.py": 8})
    activity = analyze_git_activity(
        repo, {"top": "top", **_NODES}, {"web": ["top"], "deps": ["top"]}, now=_NOW
    )
    assert activity["top"].lines_30d == 8
