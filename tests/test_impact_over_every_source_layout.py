"""One case per source layout, because the sweep had only ever been tried on one.

BDL-068 `.16`, from MAJOR 3 of the epic's first CRITICAL verdict, and the
reviewer's sentence is why it blocks with the critical rather than after it:
"Finding 3 blocks with them because it is why 1 is invisible."

**What was measured, not argued.** Before `.15`, `package_root_of` and
`source_root_of` appeared NOWHERE under `tests/` -- grep, zero hits -- no test
asserted anything about `callers.resolved`, and every fixture wrote flat `*.py`
into one `tmp_path` directory. That is the one shape in which the swept-root
derivation is trivially correct. Fifty-five cases were green over a false
negative in a narrowing tool. The suite was not weak in general: the happy path
is covered well and the seed derivation is covered better. ONE AXIS HAD NO
FIXTURE THAT COULD DISAGREE WITH THE CODE.

So this module is a MATRIX rather than more cases. Five layouts are built here,
and this repository can show only two of them: every package under
`src/beadloom` carries an `__init__.py`, which is exactly the shape the old walk
was right about. A defect that fires on adopter trees and on none of ours is
invisible to a suite that only ever builds ours.

Each layout answers the same three questions -- which root does `impact` sweep,
is a caller outside the target's own directory FOUND or DECLARED, and does the
same function reached as a PATH and as a SYMBOL give one answer -- because the
shape of the defect was the disagreement between two spellings, not any one of
its instances. A test that checked one spelling would have passed over it.

**Where the sweeps legitimately differ**, the narrower answer must say so. Two
of these layouts have no single source root to fall back on, so the path
spelling sweeps a subtree while the symbol spelling sweeps the project. That is
not a defect and it is not silenced: the narrower answer carries
`sweep-narrower-than-the-project`, which is the whole difference between a
partial answer and a clean wrong one.

**Verified red.** Every assertion here was re-run against the pre-`9db8e5a`
package in a detached worktree, on PYTHONPATH so this working tree was never
reverted under a concurrent agent. Which cases go red, and which cannot, is
recorded in this bead's comments per class -- a control that passes on both
trees is declared as a control rather than counted as a proof.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

import pytest

from beadloom.application.impact import (
    impact_of,
    package_root_of,
    render_impact,
    source_root_of,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from beadloom.application.impact import ImpactAnswer

#: The target: the file a change is being made in, reaching a declared sink so
#: the answer has a seed and the axes below it are populated rather than absent.
_TARGET = '''\
"""The file the change is being made in."""
import yaml


def helper(data, path):
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
'''

#: The caller, which never sits in the target's own directory in any layout
#: here. Two branches, so the branch axis has something to read from its seat.
_CALLER = '''\
"""The caller, in a directory the target's own does not contain."""
IMPORT_LINE


def run(flag, data, path):
    if flag:
        helper(data, path)
    else:
        helper({}, path)
'''


@dataclass(frozen=True)
class Layout:
    """One source layout, and what every derivation must answer about it.

    The expectations travel with the tree that produces them: a matrix whose
    expected values live in the test bodies is a matrix that grows a sixth
    layout with no expectations attached.
    """

    #: The project root, which is what `impact` is given as `project_root`.
    root: Path
    #: The target spelled as a path, relative to the project root.
    target: str
    #: The same function spelled as a symbol.
    symbol: str
    #: The root `impact` must sweep for the path spelling, project-relative.
    swept: str
    #: What `source_root_of` must answer for this project, project-relative.
    source_root: str
    #: The function that calls the target, and where it lives.
    caller: str
    caller_at: str
    #: A subtree that holds neither the target nor the target's directory, for
    #: the explicit `--root` probe the verdict ran against `src/beadloom/graph`.
    elsewhere: str


def _write(path: Path, text: str) -> None:
    """Create *path* and everything above it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _project(root: Path) -> Path:
    """A project root, marked the way `package_root_of` reads one."""
    _write(root / "pyproject.toml", '[project]\nname = "layout"\n')
    return root


def _caller(import_line: str) -> str:
    """The caller module, importing the target the way its layout spells it."""
    return _CALLER.replace("IMPORT_LINE", import_line)


def a_regular_package(root: Path) -> Layout:
    """Every directory on the way up carries `__init__.py`.

    This repository's own shape, and the only one the pre-`9db8e5a` walk was
    right about. It is here as the control: the fix widens a namespace tree and
    must leave this one exactly where it was.
    """
    _project(root)
    for package in ("src/pkg", "src/pkg/sub", "src/pkg/cli"):
        _write(root / package / "__init__.py", "")
    _write(root / "src/pkg/sub/writer.py", _TARGET)
    _write(root / "src/pkg/cli/main.py", _caller("from pkg.sub.writer import helper"))
    return Layout(
        root=root,
        target="src/pkg/sub/writer.py",
        symbol="helper",
        swept="src/pkg",
        source_root="src/pkg",
        caller="run",
        caller_at="src/pkg/cli/main.py",
        elsewhere="src/pkg/cli",
    )


def a_pep_420_namespace_package(root: Path) -> Layout:
    """The verdict's reproduction: `src/mypkg/` carries no `__init__.py`.

    `src/mypkg/sub/__init__.py` and `src/mypkg/cli/__init__.py` are present, so
    the walk up from the target meets a missing `__init__.py` exactly once --
    which is all it took for the sweep to stop at `src/mypkg/sub` and report the
    caller one directory across as "none found.", resolved and empty.
    """
    _project(root)
    for package in ("src/mypkg/sub", "src/mypkg/cli"):
        _write(root / package / "__init__.py", "")
    _write(root / "src/mypkg/sub/writer.py", _TARGET)
    _write(root / "src/mypkg/cli/main.py", _caller("from mypkg.sub.writer import helper"))
    return Layout(
        root=root,
        target="src/mypkg/sub/writer.py",
        symbol="helper",
        swept="src/mypkg",
        source_root="src/mypkg",
        caller="run",
        caller_at="src/mypkg/cli/main.py",
        elsewhere="src/mypkg/cli",
    )


def a_single_file_outside_any_package(root: Path) -> Layout:
    """A loose script at the project root, with no `src/` and no package anywhere.

    Named by `.15`'s close as a layout it did not build. The sweep has nowhere
    to walk up to, so it must be the project root itself -- and a caller in a
    plain sibling directory is inside it.
    """
    _project(root)
    _write(root / "writer.py", _TARGET)
    _write(root / "scripts/main.py", _caller("from writer import helper"))
    return Layout(
        root=root,
        target="writer.py",
        symbol="helper",
        swept=".",
        source_root=".",
        caller="run",
        caller_at="scripts/main.py",
        elsewhere="scripts",
    )


def a_directory_that_is_not_a_package(root: Path) -> Layout:
    """Two plain directories, no `__init__.py` and no `src/` to bound the walk.

    The walk stops at the target's own directory because there is no marker
    above it but the project root, so the caller in the sibling directory falls
    OUTSIDE the sweep. That is a legitimately narrow answer, and the only thing
    separating it from the verdict's finding is that it says so.
    """
    _project(root)
    _write(root / "tools/writer.py", _TARGET)
    _write(root / "app/main.py", _caller("from tools.writer import helper"))
    return Layout(
        root=root,
        target="tools/writer.py",
        symbol="helper",
        swept="tools",
        source_root=".",
        caller="run",
        caller_at="app/main.py",
        elsewhere="app",
    )


def two_packages_under_src(root: Path) -> Layout:
    """`src/` holds two top-level packages, so there is no single source root.

    The second layout `.15`'s close named as unbuilt. `source_root_of` falls
    back to the project root, the path spelling sweeps one package and the
    symbol spelling sweeps the project -- so the two spellings give DIFFERENT
    answers here, correctly, and the narrower one has to declare it.
    """
    _project(root)
    for package in ("src/one", "src/two"):
        _write(root / package / "__init__.py", "")
    _write(root / "src/one/writer.py", _TARGET)
    _write(root / "src/two/main.py", _caller("from one.writer import helper"))
    return Layout(
        root=root,
        target="src/one/writer.py",
        symbol="helper",
        swept="src/one",
        source_root=".",
        caller="run",
        caller_at="src/two/main.py",
        elsewhere="src/two",
    )


#: Every layout, for the questions each one must answer the same way.
EVERY_LAYOUT = (
    a_regular_package,
    a_pep_420_namespace_package,
    a_single_file_outside_any_package,
    a_directory_that_is_not_a_package,
    two_packages_under_src,
)

#: The layouts whose swept root holds the caller, so the axis is complete.
THE_SWEEP_HOLDS_THE_CALLER = (
    a_regular_package,
    a_pep_420_namespace_package,
    a_single_file_outside_any_package,
)

#: The layouts with no single source root, where the sweep is narrower than the
#: project and the caller therefore sits outside it.
THE_SWEEP_EXCLUDES_THE_CALLER = (
    a_directory_that_is_not_a_package,
    two_packages_under_src,
)

#: The layouts whose target sits in a subdirectory, so the target has a third
#: spelling: the directory that holds it.
THE_TARGET_SITS_IN_A_SUBDIRECTORY = (
    a_regular_package,
    a_pep_420_namespace_package,
    a_directory_that_is_not_a_package,
    two_packages_under_src,
)

_NARROWED = "sweep-narrower-than-the-project"
_OUTSIDE = "target-outside-the-sweep"


def _ids(builders: tuple[Callable[[Path], Layout], ...]) -> list[str]:
    """Read the parametrize ids off the builders, so a sixth layout names itself."""
    return [builder.__name__ for builder in builders]


def _under(root: Path, relative: str) -> Path:
    """A project-relative path as an absolute one, since the project root spells itself `.`."""
    return root if relative == "." else root / relative


def _kinds(answer: ImpactAnswer) -> set[str]:
    """The kinds in the unresolved population, which is what a consumer switches on."""
    return {gap.kind for gap in answer.unresolved}


def _caller_names(answer: ImpactAnswer) -> list[str]:
    """The caller axis, by name."""
    return sorted(site.name for site in answer.callers.sites)


def _section(text: str, heading: str) -> str:
    """One section of the rendered answer, so an assertion cannot pass on another's text."""
    return text.split(heading)[1].split("\n## ")[0]


class TestEverySourceLayoutSweepsTheRootItsShapeImplies:
    """The swept root, asserted per layout rather than assumed from one."""

    @pytest.mark.parametrize("build", EVERY_LAYOUT, ids=_ids(EVERY_LAYOUT))
    def test_impact_sweeps_the_root_the_layout_implies(
        self, build: Callable[[Path], Layout], tmp_path: Path
    ) -> None:
        layout = build(tmp_path / "proj")

        answer = impact_of(layout.target, project_root=layout.root)

        assert answer.root == layout.swept

    @pytest.mark.parametrize("build", EVERY_LAYOUT, ids=_ids(EVERY_LAYOUT))
    def test_package_root_of_alone_agrees_with_the_answer(
        self, build: Callable[[Path], Layout], tmp_path: Path
    ) -> None:
        """Called without `project_root`, which is `.15`'s defaulted parameter.

        The default falls back to the nearest ancestor carrying `pyproject.toml`,
        so the derivation used on its own must reach the same root the command
        reaches. Two ways to ask one question are two things that can disagree.
        """
        layout = build(tmp_path / "proj")

        assert package_root_of(layout.root / layout.target) == _under(layout.root, layout.swept)

    @pytest.mark.parametrize("build", EVERY_LAYOUT, ids=_ids(EVERY_LAYOUT))
    def test_source_root_of_names_this_projects_source_root(
        self, build: Callable[[Path], Layout], tmp_path: Path
    ) -> None:
        layout = build(tmp_path / "proj")

        assert source_root_of(layout.root) == _under(layout.root, layout.source_root)


class TestACallerOutsideTheTargetsOwnDirectory:
    """Found, or declared. The verdict's finding was the third option: neither."""

    @pytest.mark.parametrize(
        "build", THE_SWEEP_HOLDS_THE_CALLER, ids=_ids(THE_SWEEP_HOLDS_THE_CALLER)
    )
    def test_the_caller_is_found_where_the_sweep_holds_it(
        self, build: Callable[[Path], Layout], tmp_path: Path
    ) -> None:
        layout = build(tmp_path / "proj")

        answer = impact_of(layout.target, project_root=layout.root)

        assert _caller_names(answer) == [layout.caller]
        assert answer.callers.resolved is True

    @pytest.mark.parametrize(
        "build", THE_SWEEP_HOLDS_THE_CALLER, ids=_ids(THE_SWEEP_HOLDS_THE_CALLER)
    )
    def test_a_complete_sweep_declares_no_narrowing(
        self, build: Callable[[Path], Layout], tmp_path: Path
    ) -> None:
        """A caveat on every answer is a caveat nobody reads."""
        layout = build(tmp_path / "proj")

        answer = impact_of(layout.target, project_root=layout.root)

        assert _NARROWED not in _kinds(answer)

    @pytest.mark.parametrize(
        "build", THE_SWEEP_EXCLUDES_THE_CALLER, ids=_ids(THE_SWEEP_EXCLUDES_THE_CALLER)
    )
    def test_a_caller_the_sweep_cannot_see_is_declared_rather_than_omitted(
        self, build: Callable[[Path], Layout], tmp_path: Path
    ) -> None:
        layout = build(tmp_path / "proj")

        answer = impact_of(layout.target, project_root=layout.root)

        assert _caller_names(answer) == []
        assert _NARROWED in _kinds(answer)

    @pytest.mark.parametrize(
        "build", THE_SWEEP_EXCLUDES_THE_CALLER, ids=_ids(THE_SWEEP_EXCLUDES_THE_CALLER)
    )
    def test_the_narrowing_names_both_the_sweep_and_the_project(
        self, build: Callable[[Path], Layout], tmp_path: Path
    ) -> None:
        """A gap a reader cannot act on is a gap that reads as noise."""
        layout = build(tmp_path / "proj")

        answer = impact_of(layout.target, project_root=layout.root)
        gap = next(entry for entry in answer.unresolved if entry.kind == _NARROWED)

        assert layout.swept in gap.detail
        assert layout.source_root in gap.detail


class TestOneTargetSpelledMoreThanOneWay:
    """The shape of the defect, not one of its instances.

    One tree, one derivation, two spellings of one function, opposite answers,
    and the wrong one was the clean one. A case that checked either spelling on
    its own would have been green.
    """

    @pytest.mark.parametrize(
        "build", THE_SWEEP_HOLDS_THE_CALLER, ids=_ids(THE_SWEEP_HOLDS_THE_CALLER)
    )
    def test_the_path_and_the_symbol_give_one_answer(
        self, build: Callable[[Path], Layout], tmp_path: Path
    ) -> None:
        layout = build(tmp_path / "proj")

        by_path = impact_of(layout.target, project_root=layout.root)
        by_symbol = impact_of(layout.symbol, project_root=layout.root)

        assert by_path.root == by_symbol.root
        assert _caller_names(by_path) == _caller_names(by_symbol) == [layout.caller]

    @pytest.mark.parametrize(
        "build", THE_SWEEP_EXCLUDES_THE_CALLER, ids=_ids(THE_SWEEP_EXCLUDES_THE_CALLER)
    )
    def test_where_the_sweeps_differ_the_narrower_one_says_so(
        self, build: Callable[[Path], Layout], tmp_path: Path
    ) -> None:
        """These layouts have no single source root, so the spellings differ by design.

        What must not happen is the difference going unstated: the answer that
        swept less carries the narrowing, the one that swept the project does
        not, and a reader comparing them can tell which is which.
        """
        layout = build(tmp_path / "proj")

        by_path = impact_of(layout.target, project_root=layout.root)
        by_symbol = impact_of(layout.symbol, project_root=layout.root)

        assert by_path.root == layout.swept
        assert by_symbol.root == layout.source_root
        assert _caller_names(by_path) == []
        assert _caller_names(by_symbol) == [layout.caller]
        assert _NARROWED in _kinds(by_path)
        assert _NARROWED not in _kinds(by_symbol)

    @pytest.mark.parametrize(
        "build",
        THE_TARGET_SITS_IN_A_SUBDIRECTORY,
        ids=_ids(THE_TARGET_SITS_IN_A_SUBDIRECTORY),
    )
    def test_the_directory_that_holds_the_target_answers_the_same_as_the_file(
        self, build: Callable[[Path], Layout], tmp_path: Path
    ) -> None:
        """The third spelling, and the arm of `_targets_for` no case had reached.

        `impact` accepts a directory and answers about every file under it. The
        branch was partially covered before this module: an arm with no fixture
        that could disagree with it, which is the hole MAJOR 3 named rather than
        a second instance of it.
        """
        layout = build(tmp_path / "proj")
        directory = PurePosixPath(layout.target).parent.as_posix()

        by_directory = impact_of(directory, project_root=layout.root)
        by_path = impact_of(layout.target, project_root=layout.root)

        assert by_directory.root == by_path.root == layout.swept
        assert _caller_names(by_directory) == _caller_names(by_path)


class TestARootPointedAtAnUnrelatedSubtree:
    """The verdict's second probe: `--root src/beadloom/graph` against `bootstrap.py`.

    It printed "who else calls this: none found." with no gap entry -- an answer
    derived over a tree holding nothing the question was about, rendered as a
    complete one.
    """

    @staticmethod
    def _answer(layout: Layout) -> ImpactAnswer:
        return impact_of(
            layout.target,
            project_root=layout.root,
            root=layout.root / layout.elsewhere,
        )

    @pytest.mark.parametrize("build", EVERY_LAYOUT, ids=_ids(EVERY_LAYOUT))
    def test_the_caller_axis_refuses_to_answer(
        self, build: Callable[[Path], Layout], tmp_path: Path
    ) -> None:
        layout = build(tmp_path / "proj")

        answer = self._answer(layout)

        assert answer.callers.resolved is False
        assert layout.target in answer.callers.reason
        assert layout.elsewhere in answer.callers.reason

    @pytest.mark.parametrize("build", EVERY_LAYOUT, ids=_ids(EVERY_LAYOUT))
    def test_the_gap_names_the_target_and_the_root_that_excluded_it(
        self, build: Callable[[Path], Layout], tmp_path: Path
    ) -> None:
        layout = build(tmp_path / "proj")

        answer = self._answer(layout)
        gap = next(entry for entry in answer.unresolved if entry.kind == _OUTSIDE)

        assert layout.target in gap.detail
        assert gap.where == layout.elsewhere

    @pytest.mark.parametrize("build", EVERY_LAYOUT, ids=_ids(EVERY_LAYOUT))
    def test_the_rendered_caller_axis_does_not_read_as_none_found(
        self, build: Callable[[Path], Layout], tmp_path: Path
    ) -> None:
        """The exact string the verdict quoted, in the exact section it read it from."""
        layout = build(tmp_path / "proj")

        callers = _section(render_impact(self._answer(layout)), "## who else calls this")

        assert "- none found." not in callers
        assert "- unresolved: " in callers

    def test_a_root_outside_the_project_is_named_in_full_and_still_refuses(
        self, tmp_path: Path
    ) -> None:
        """The probe taken to its limit: a subtree in a different project.

        The swept root has no project-relative spelling at all, so the answer
        names it absolutely instead of silently rendering something shorter.
        """
        layout = a_regular_package(tmp_path / "proj")
        outside = tmp_path / "another"
        _write(outside / "mod.py", "def unrelated():\n    return 1\n")

        answer = impact_of(layout.target, project_root=layout.root, root=outside)

        assert answer.root == outside.as_posix()
        assert answer.callers.resolved is False
        assert _OUTSIDE in _kinds(answer)

    def test_a_project_root_that_does_not_hold_the_target_does_not_bound_the_walk(
        self, tmp_path: Path
    ) -> None:
        """`project_root` is a ceiling for a target beneath it, and nothing otherwise.

        Handed an unrelated directory, the walk must fall back to the nearest
        ancestor carrying `pyproject.toml` rather than stop where it stands --
        which is the one arm of `_ceiling_for` no case reached.
        """
        layout = a_regular_package(tmp_path / "proj")
        unrelated = tmp_path / "elsewhere"
        unrelated.mkdir()

        swept = package_root_of(layout.root / layout.target, project_root=unrelated)

        assert swept == layout.root / layout.swept


class TestTheCeilingsTheseLayoutsExpose:
    """What is still narrow after `9db8e5a`, pinned so closing it is a decision."""

    def test_a_two_package_src_tree_declares_a_narrowing_on_every_run(
        self, tmp_path: Path
    ) -> None:
        """`.15`'s close left this open: honest, and possibly noisy.

        With no single source root, EVERY path-spelled run on such a tree
        carries the narrowing, including one whose caller it did find. Nobody
        has met this tree yet, so the behaviour is recorded rather than judged
        -- and a later decision to quieten it goes red here instead of silently.
        """
        layout = two_packages_under_src(tmp_path / "proj")

        for target in (layout.target, layout.caller_at):
            answer = impact_of(target, project_root=layout.root)

            assert _NARROWED in _kinds(answer), target

    def test_a_narrowed_sweep_still_prints_none_found_and_the_gap_is_what_says_otherwise(
        self, tmp_path: Path
    ) -> None:
        """`callers.resolved` is the reviewer's stated minimum, not "anything narrower".

        The target IS under the sweep here, so the axis is resolved and the
        caller section reads "none found." while a caller exists one directory
        across. What stops that being the verdict's finding again is the
        narrowing gap, and nothing else -- so this records precisely how much
        `9db8e5a` closed, and how much it did not.
        """
        layout = a_directory_that_is_not_a_package(tmp_path / "proj")

        answer = impact_of(layout.target, project_root=layout.root)
        text = render_impact(answer)

        assert answer.callers.resolved is True
        assert "- none found." in _section(text, "## who else calls this")
        assert _NARROWED in _kinds(answer)
        assert f"[{_NARROWED}]" in _section(text, "## unresolved")
