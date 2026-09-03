"""How wide `impact` swept, and from which seat it read the branch axis.

BDL-068 `.15`, from the epic's first CRITICAL verdict. Both findings are false
negatives in a NARROWING tool, which is the one outcome this command can ship
that is worse than not existing: an agent that reads widely because it does not
know the boundary occasionally stumbles onto the neighbouring shape, and an agent
handed a clean list trusts it and stops.

**Why the fixtures here are not the ones in `tests/test_impact_*`.** Every
existing fixture writes a package that carries `__init__.py`, and so does every
package in this repository -- which is exactly why the suite, the Gate and the
author's own dogfooding all read green while `beadloom impact` answered
`callers: none found.` on an adopter's PEP 420 tree. The layouts are the
subject here, so they are built rather than assumed.

The reviewer's reproduction, verbatim, is the first test: `src/mypkg/` with NO
`__init__.py`, `src/mypkg/sub/__init__.py` present, and `src/mypkg/cli/main.py`
calling into `sub/writer.py`. Before the fix, the sweep stopped at
`src/mypkg/sub` and the caller one directory across read as `none found.` with
`resolved=True` and nothing in the unresolved population.
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

import pytest

from beadloom.application.impact import (
    THE_CALLER_SEAT,
    THE_TARGET_SEAT,
    Population,
    impact_of,
    package_root_of,
    render_impact,
    source_root_of,
)

if TYPE_CHECKING:
    from pathlib import Path

_WRITER = '''\
"""The file the change is being made in."""
import yaml


def helper(data, path):
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
'''

_MAIN = '''\
"""The caller, one directory across from the target."""
from mypkg.sub.writer import helper


def run(flag, data, path):
    if flag:
        helper(data, path)
    else:
        helper({}, path)
'''


def _namespace_project(root: Path) -> Path:
    """A PEP 420 tree: `src/mypkg` is a package and carries no `__init__.py`."""
    (root / "src" / "mypkg" / "sub").mkdir(parents=True)
    (root / "src" / "mypkg" / "cli").mkdir(parents=True)
    (root / "src" / "mypkg" / "sub" / "__init__.py").write_text("", encoding="utf-8")
    (root / "src" / "mypkg" / "cli" / "__init__.py").write_text("", encoding="utf-8")
    (root / "src" / "mypkg" / "sub" / "writer.py").write_text(_WRITER, encoding="utf-8")
    (root / "src" / "mypkg" / "cli" / "main.py").write_text(_MAIN, encoding="utf-8")
    return root


@pytest.fixture()
def namespace_tree(tmp_path: Path) -> Path:
    """The reviewer's reproduction, built here rather than described."""
    return _namespace_project(tmp_path / "proj")


class TestTheSweepDoesNotStopAtAMissingInitFile:
    """A namespace package is a package, and the walk must not decide otherwise."""

    def test_package_root_of_walks_past_a_directory_with_no_init(
        self, namespace_tree: Path
    ) -> None:
        target = namespace_tree / "src" / "mypkg" / "sub" / "writer.py"

        assert package_root_of(target, project_root=namespace_tree) == (
            namespace_tree / "src" / "mypkg"
        )

    def test_the_caller_across_the_namespace_package_is_found(
        self, namespace_tree: Path
    ) -> None:
        answer = impact_of(
            "src/mypkg/sub/writer.py", project_root=namespace_tree
        )

        assert answer.root == "src/mypkg"
        assert [site.name for site in answer.callers.sites] == ["run"]
        assert answer.callers.resolved is True

    def test_both_spellings_of_one_target_agree(self, namespace_tree: Path) -> None:
        """The finding's shape: two spellings, one tree, opposite answers."""
        by_path = impact_of("src/mypkg/sub/writer.py", project_root=namespace_tree)
        by_symbol = impact_of("helper", project_root=namespace_tree)

        assert [site.name for site in by_path.callers.sites] == [
            site.name for site in by_symbol.callers.sites
        ]

    def test_the_source_root_counts_a_namespace_package(
        self, namespace_tree: Path
    ) -> None:
        assert source_root_of(namespace_tree) == namespace_tree / "src" / "mypkg"

    def test_a_regular_package_root_is_unchanged(self, tmp_path: Path) -> None:
        """The fix widens a namespace tree and must leave a normal one alone."""
        package = tmp_path / "proj" / "src" / "pkg"
        package.mkdir(parents=True)
        (package / "__init__.py").write_text("", encoding="utf-8")
        (package / "mod.py").write_text("def f():\n    return 1\n", encoding="utf-8")

        assert package_root_of(package / "mod.py", project_root=tmp_path / "proj") == (
            package
        )

    def test_a_file_in_the_project_root_sweeps_no_wider_than_it(
        self, tmp_path: Path
    ) -> None:
        """The walk is bounded by the project root, never above it."""
        (tmp_path / "mod.py").write_text("def f():\n    return 1\n", encoding="utf-8")

        assert package_root_of(tmp_path / "mod.py", project_root=tmp_path) == tmp_path


class TestANarrowedSweepCannotReadAsACompleteOne:
    """`callers.resolved` is a predicate, and a narrowed root says so."""

    def test_a_root_that_does_not_hold_the_target_leaves_the_axis_unresolved(
        self, namespace_tree: Path
    ) -> None:
        answer = impact_of(
            "src/mypkg/sub/writer.py",
            project_root=namespace_tree,
            root=namespace_tree / "src" / "mypkg" / "cli",
        )

        assert answer.callers.resolved is False
        assert answer.callers.reason
        assert "target-outside-the-sweep" in {gap.kind for gap in answer.unresolved}

    def test_the_gap_names_both_the_target_and_the_root(
        self, namespace_tree: Path
    ) -> None:
        answer = impact_of(
            "src/mypkg/sub/writer.py",
            project_root=namespace_tree,
            root=namespace_tree / "src" / "mypkg" / "cli",
        )
        gap = next(
            entry for entry in answer.unresolved if entry.kind == "target-outside-the-sweep"
        )

        assert "src/mypkg/sub/writer.py" in gap.detail
        assert "src/mypkg/cli" in gap.where

    def test_a_sweep_narrower_than_the_project_is_declared(
        self, namespace_tree: Path
    ) -> None:
        answer = impact_of(
            "src/mypkg/cli/main.py",
            project_root=namespace_tree,
            root=namespace_tree / "src" / "mypkg" / "cli",
        )
        gap = next(
            entry
            for entry in answer.unresolved
            if entry.kind == "sweep-narrower-than-the-project"
        )

        assert "src/mypkg/cli" in gap.detail
        assert "src/mypkg" in gap.where

    def test_a_sweep_that_is_the_source_root_declares_no_narrowing(
        self, namespace_tree: Path
    ) -> None:
        answer = impact_of("src/mypkg/sub/writer.py", project_root=namespace_tree)

        assert "sweep-narrower-than-the-project" not in {
            gap.kind for gap in answer.unresolved
        }

    def test_an_unresolved_axis_still_shows_the_sites_it_did_find(
        self, namespace_tree: Path
    ) -> None:
        """A caveat must not empty a partial answer, or the fix trades one silence for another."""
        complete = impact_of("src/mypkg/sub/writer.py", project_root=namespace_tree)
        partial = replace(
            complete,
            callers=Population(
                resolved=False, sites=complete.callers.sites, reason="a stated reason"
            ),
        )

        text = render_impact(partial)

        site = complete.callers.sites[0]
        assert "- unresolved: a stated reason" in text
        assert f"{site.name} — {site.path}:{site.lineno}" in text


class TestTheBranchAxisAnswersFromTheCallersSeat:
    """MAJOR 2: the number BDL-067 got wrong must come from the seat it sat in."""

    def test_the_callers_branches_are_read_and_named(
        self, namespace_tree: Path
    ) -> None:
        answer = impact_of("src/mypkg/sub/writer.py", project_root=namespace_tree)
        by_name = {command.name: command for command in answer.commands}

        assert "run" in by_name
        assert by_name["run"].seat == THE_CALLER_SEAT
        assert len(by_name["run"].branches) == 2

    def test_the_targets_own_commands_keep_the_target_seat(
        self, namespace_tree: Path
    ) -> None:
        answer = impact_of("src/mypkg/sub/writer.py", project_root=namespace_tree)
        by_name = {command.name: command for command in answer.commands}

        assert by_name["helper"].seat == THE_TARGET_SEAT

    def test_the_text_says_which_seat_a_count_came_from(
        self, namespace_tree: Path
    ) -> None:
        text = render_impact(
            impact_of("src/mypkg/sub/writer.py", project_root=namespace_tree)
        )

        assert "run" in text
        assert "caller" in text.split("## branches and exit forms")[1]
