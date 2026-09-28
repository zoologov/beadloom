"""Self-checks of this repository's agent roles, hooks, tracker and commits (BDL-074 A3).

Moved out of ``tests/test_a_commit_is_judged_against_the_declared_axes.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

import shutil
import subprocess
from functools import cache
from typing import TYPE_CHECKING

import pytest

from beadloom.application.declared_scope import (
    scope_of_branch,
)
from beadloom.application.impact.boundary import open_boundary
from beadloom.doc_sync.axes_section import read_axes_section
from beadloom.doc_sync.scope_check import (
    DeclaredScope,
    ScopeVerdict,
    check_commit_scope,
)
from tests.support.axes_table import (
    HEADER,
    ROWS_THESE_CASES_DEPEND_ON,
)

if TYPE_CHECKING:
    from pathlib import Path

    from beadloom.application.impact.boundary import GraphBoundary
    from beadloom.doc_sync.doc_quality import QualityFinding


#: The ruling each pinned row carries: ``(axis, node, in_scope)``. The guard
#: compares this triple and nothing else, because the triple is what the check
#: reads and the rest of the row is prose.
_PINNED_RULINGS: tuple[tuple[str, str, bool], ...] = (
    ("callers", "ci-gate", True),
    ("callers", "cli-commands", True),
    ("co-writers", "agentic-flow-setup", True),
    ("callers", "graph", False),
    ("co-writers", "doc-generator", False),
    ("co-writers", "agent-prime", False),
)


#: A commit of BDL-067's, landed on this repository's trunk. Judged against
#: BDL-068's axes it is another work item's change, which is the shape the check
#: exists to report.
_A_FOREIGN_COMMIT = "a4738b7c"


#: This epic's own code commits, which its own axes must not condemn.
_THIS_EPICS_COMMITS = ("2f9e343", "3f68442", "c7591a8")


#: The branch whose segment names this epic's work-item folder.
_THIS_EPICS_BRANCH = "features/BDL-068"


def _paths_of(root: Path, commit: str) -> list[str]:
    """What *commit* changed, or a declared skip when it is not in this checkout."""
    result = subprocess.run(  # noqa: S603
        ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", commit],  # noqa: S607
        cwd=root,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        pytest.skip(f"commit {commit} is not in this checkout")
    return result.stdout.split()


@cache
def _boundary_of(index_root: Path) -> GraphBoundary:
    """One connection per index root: the boundary carries no close, and a case
    that opens a fresh one per assertion leaks a handle for every assertion."""
    return open_boundary(index_root)


def _verdict_over(
    index_root: Path, scope: DeclaredScope, commit: str, *, history: Path
) -> ScopeVerdict:
    """*commit*'s real paths, owned by the real index, judged against *scope*.

    *history* is the self-check snapshot, which carries this repository's git
    history (BDL-074 A3), whatever root carries the index: the pinned cases
    below judge real commits through a copy of the index and a document of their
    own, and a git read against that copy would find no history and skip
    silently. A commit the snapshot does not hold skips in :func:`_paths_of`.
    """
    boundary = _boundary_of(index_root)
    paths = _paths_of(history, commit)
    ownership = {
        path: (owner.node, owner.domain)
        for path in paths
        for owner in (boundary.owner_of(path),)
    }
    return check_commit_scope(paths, scope, ownership=ownership)


@pytest.fixture(scope="module")
def pinned_project(tmp_path_factory: pytest.TempPathFactory, self_check_snapshot: Path) -> Path:
    """A project root carrying the pinned table and this repository's index.

    The index is COPIED rather than rebuilt because these cases are about the
    table and not about indexing, and a copy keeps the ownership answers the
    same ones the live cases get. Nothing else of this repository is copied, so
    the only thing the pinned run reads from a document is the six rows.
    """
    root = self_check_snapshot  # the snapshot's index, never the live one (BDL-074 A2)
    project = tmp_path_factory.mktemp("pinned-axes")
    (project / ".beadloom").mkdir()
    shutil.copy2(root / ".beadloom" / "beadloom.db", project / ".beadloom" / "beadloom.db")
    folder = project / ".claude" / "development" / "docs" / "features" / "BDL-068"
    folder.mkdir(parents=True)
    (folder / "RFC.md").write_text(
        "# RFC\n\n## Axes\n\n"
        "> **Derived by:** excerpted from BDL-068's own table, never re-derived here\n"
        "> **Seed:** `none`\n"
        "> **Unresolved:** none\n\n" + HEADER + ROWS_THESE_CASES_DEPEND_ON,
        encoding="utf-8",
    )
    return project


def _message(finding: QualityFinding) -> str:
    """Everything a finding says, for a case that is about the report and not a field."""
    return " ".join((finding.excerpt, finding.why, finding.remediation))


class TestTheCheckOnThisRepositorysOwnCommits:
    """Claims about the approval BDL-068's RFC carries TODAY, on real commits.

    These read the LIVE ``## Axes`` section on purpose, because their whole
    content is a statement about the live approval: that this epic's own commits
    fall inside the scope it declared, and that another work item's commit does
    not. A red here is a FINDING — the epic committed outside its own approval,
    or its approval has grown wide enough to swallow somebody else's work — and
    not a maintenance chore. Nothing here enumerates paths, so appending a
    slice's rows cannot make it red; see :data:`ROWS_THESE_CASES_DEPEND_ON` for
    the split and for what an appender does have to know.

    Skipped where the history is absent — CI's tests job checks out at depth 1 —
    and the skip is declared rather than discovered.
    """

    @pytest.fixture
    def project(self, self_check_snapshot: Path) -> Path:
        # The snapshot's index rather than the live one: read as found, the
        # ownership answers depended on the last reindex (BDL-074 A1, A2).
        return self_check_snapshot

    @pytest.fixture
    def live_scope(self, project: Path) -> DeclaredScope:
        scope, reason = scope_of_branch(project, branch=_THIS_EPICS_BRANCH)
        if scope is None:
            pytest.skip(f"BDL-068 declares no axes in this checkout: {reason}")
        return scope

    @pytest.mark.parametrize("commit", _THIS_EPICS_COMMITS)
    def test_this_epics_own_code_commits_are_silent(
        self, project: Path, live_scope: DeclaredScope, commit: str
    ) -> None:
        verdict = _verdict_over(project, live_scope, commit, history=project)
        assert verdict.findings == (), [f.path for f in verdict.findings]
        assert verdict.judged > 0, "a silent run over nothing has verified nothing"

    def test_a_commit_from_another_work_item_is_still_reported(
        self, project: Path, live_scope: DeclaredScope
    ) -> None:
        # The not-always-green clause, held as a relation rather than a list:
        # WHICH paths fall outside is a property of a table that grows every
        # slice, but THAT this epic's approval does not cover another work
        # item's commit is the claim, and it survives the growth.
        verdict = _verdict_over(project, live_scope, _A_FOREIGN_COMMIT, history=project)
        assert verdict.findings != ()

    def test_it_reports_only_paths_that_commit_changed(
        self, project: Path, live_scope: DeclaredScope
    ) -> None:
        verdict = _verdict_over(project, live_scope, _A_FOREIGN_COMMIT, history=project)
        changed = set(_paths_of(project, _A_FOREIGN_COMMIT))
        assert {f.path for f in verdict.findings} <= changed

    def test_every_finding_names_an_axis_the_document_declares(
        self, project: Path, live_scope: DeclaredScope
    ) -> None:
        # An agreement between the report and the document, checked by a route
        # the check does not take: the axis names are read off the section's
        # rows, and a finding citing an axis nobody declared would fail here.
        section = read_axes_section(
            (project / live_scope.document).read_text(encoding="utf-8")
        )
        assert section is not None
        declared = {axis.axis for axis in section.axes if axis.axis}
        verdict = _verdict_over(project, live_scope, _A_FOREIGN_COMMIT, history=project)
        for finding in verdict.findings:
            assert any(f"`{axis}`" in _message(finding) for axis in declared), finding

    def test_every_finding_sends_the_reader_to_the_document_that_ruled(
        self, project: Path, live_scope: DeclaredScope
    ) -> None:
        verdict = _verdict_over(project, live_scope, _A_FOREIGN_COMMIT, history=project)
        for finding in verdict.findings:
            assert live_scope.document in _message(finding)


class TestTheRowsTheseCasesDependOn:
    """The enumeration, judged against a PINNED excerpt of this epic's table.

    Everything about this run is real except the table: real commit, real paths,
    the real index resolving each path to its owning node and bounded context.
    Only the six rows in :data:`ROWS_THESE_CASES_DEPEND_ON` are frozen, and
    freezing them is what lets a case name the exact paths that fall outside
    without breaking on a document the RFC obliges to grow every slice.

    What is given up, stated rather than hidden: these cases no longer assert
    that the LIVE table produces this list. That claim moved to
    :class:`TestTheCheckOnThisRepositorysOwnCommits`, which holds it as a
    relation, and to
    :meth:`test_every_pinned_row_is_still_the_ruling_the_rfc_carries`, which
    holds the excerpt to the document. Together those are a stronger pair than
    the enumeration was on its own: the enumeration went red when the table
    grew, which is the one event that is guaranteed to happen and is never a
    defect.
    """

    @pytest.fixture
    def pinned_scope(self, pinned_project: Path) -> DeclaredScope:
        scope, reason = scope_of_branch(pinned_project, branch=_THIS_EPICS_BRANCH)
        assert scope is not None, reason
        return scope

    def test_a_commit_from_another_work_item_is_reported(
        self, pinned_project: Path, pinned_scope: DeclaredScope, self_check_snapshot: Path
    ) -> None:
        verdict = _verdict_over(
            pinned_project, pinned_scope, _A_FOREIGN_COMMIT, history=self_check_snapshot
        )
        assert [f.path for f in verdict.findings] == [
            "src/beadloom/graph/linter.py",
            "src/beadloom/onboarding/doc_generator.py",
            "src/beadloom/onboarding/scanner/bootstrap.py",
            "src/beadloom/onboarding/scanner/doc_classify.py",
            "src/beadloom/onboarding/scanner/init_flow.py",
            "src/beadloom/onboarding/scanner/parent_edges.py",
        ]

    def test_a_path_a_kept_row_names_is_not_among_them(
        self, pinned_project: Path, pinned_scope: DeclaredScope, self_check_snapshot: Path
    ) -> None:
        # `ci-gate` and `cli-commands` are kept by name, so three of that
        # commit's source paths are inside the approval. Without this the list
        # above would also pass against a check that reported everything.
        verdict = _verdict_over(
            pinned_project, pinned_scope, _A_FOREIGN_COMMIT, history=self_check_snapshot
        )
        assert "src/beadloom/application/gate.py" not in {f.path for f in verdict.findings}
        assert verdict.judged == 10

    def test_a_sibling_in_a_declared_context_is_not_among_them(
        self, pinned_project: Path, pinned_scope: DeclaredScope, self_check_snapshot: Path
    ) -> None:
        # `graph-files` is named by no row at all. It is inside because a kept
        # row reaches `onboarding`, which is the second clause of the rule on a
        # real path rather than on a fixture.
        verdict = _verdict_over(
            pinned_project, pinned_scope, _A_FOREIGN_COMMIT, history=self_check_snapshot
        )
        assert "src/beadloom/onboarding/graph_files.py" not in {
            f.path for f in verdict.findings
        }

    def test_that_finding_names_the_axis_that_ruled_it_out(
        self, pinned_project: Path, pinned_scope: DeclaredScope, self_check_snapshot: Path
    ) -> None:
        verdict = _verdict_over(
            pinned_project, pinned_scope, _A_FOREIGN_COMMIT, history=self_check_snapshot
        )
        assert "`callers`" in verdict.findings[0].excerpt

    def test_that_finding_names_the_node_the_ruling_is_about(
        self, pinned_project: Path, pinned_scope: DeclaredScope, self_check_snapshot: Path
    ) -> None:
        verdict = _verdict_over(
            pinned_project, pinned_scope, _A_FOREIGN_COMMIT, history=self_check_snapshot
        )
        assert "`graph`" in verdict.findings[0].excerpt

    def test_every_pinned_row_is_still_the_ruling_the_rfc_carries(
        self, self_check_snapshot: Path
    ) -> None:
        """The guard on the excerpt, and the only case an appender can trip.

        Appending S5's or S6's rows leaves this green. It goes red when one of
        the six rows this file depends on is EDITED or REMOVED, because that
        changes what the pinned cases are a test of, and the failure message is
        what tells the next person to come here.
        """
        project = self_check_snapshot  # resolving the branch reads an index (BDL-074 A2)
        scope, reason = scope_of_branch(project, branch=_THIS_EPICS_BRANCH)
        if scope is None:
            pytest.skip(f"BDL-068 declares no axes in this checkout: {reason}")
        section = read_axes_section((project / scope.document).read_text(encoding="utf-8"))
        assert section is not None
        live = {(axis.axis, axis.node, axis.in_scope) for axis in section.axes}
        missing = [ruling for ruling in _PINNED_RULINGS if ruling not in live]
        assert not missing, (
            f"{scope.document} no longer carries these rulings: {missing}. "
            "Appending rows is free and does not reach this case. Changing one "
            "of the rows tests/test_a_commit_is_judged_against_the_declared_axes.py "
            "pins does: update `ROWS_THESE_CASES_DEPEND_ON`, `_PINNED_RULINGS` "
            "and the expected finding list in `TestTheRowsTheseCasesDependOn` "
            "together, and re-measure rather than re-spell."
        )
