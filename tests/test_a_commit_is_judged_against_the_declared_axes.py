"""BDL-068 S1.6 — a commit judged against the axes its work item declared.

The rule these cases hold was MEASURED before it was written, on this epic's own
``## Axes`` table: judging a staged path's owning NODE against the nodes the
kept rows name is red on all three of this branch's code commits, and judging at
the bounded context those axes reach is silent on all three and outside for 115
of the 155 commits before the branch that touch an owned path. The cases below
pin both clauses, the ruling clause between them, and every reason a run has to
report that it checked nothing.

**Two kinds of case run against this epic's own ``## Axes`` table, and they are
kept apart on purpose.** The table is a document the RFC's per-slice rule
obliges to GROW at the start of every slice, so a case that spells out what the
table produces today is a case that goes red on schedule for no defect — which
is what happened when S4's twenty-eight rows landed. So:

* a claim ABOUT the live approval — this epic's own commits are inside it,
  another work item's commit is not — reads the live section and asserts a
  RELATION. A red there is a finding about the epic;
* a claim about the CHECK's behaviour — exactly which paths fall outside, and
  what the finding says — is judged against a pinned six-row excerpt of that
  table, with the commit, the paths and the index all still real. A red there is
  a defect in the check.

One further case holds the excerpt to the document, so the pin cannot rot
silently. :data:`_ROWS_THESE_CASES_DEPEND_ON` states what that means for the
next person to append a slice's rows.

**The rejected shape, recorded because it is the cheap one.** Deriving the
expected finding list from the same table the check reads would never go red on
growth, and would assert nothing: the derivation would have to classify each
path by kept-node, ruling and reached-context, which is
:func:`~beadloom.doc_sync.scope_check.check_commit_scope`'s body written a second
time. It passes while both copies are wrong the same way, and it breaks on every
refactor of the one that ships. The distinction that matters is WHICH half is
derived — deriving the check's INPUT from the document is exactly what the
pinned excerpt does not have to do by hand, while deriving its OUTPUT is the
tautology.
"""

from __future__ import annotations

import shutil
import subprocess
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from beadloom.application.declared_scope import (
    NO_BRANCH,
    ScopeRun,
    scope_check,
    scope_of_branch,
    trunk_ref,
    work_item_of_branch,
)
from beadloom.application.impact.boundary import open_boundary
from beadloom.doc_sync.axes_section import derived_targets, read_axes_section
from beadloom.doc_sync.git_baseline import (
    current_branch,
    paths_changed_since,
    ref_exists,
)
from beadloom.doc_sync.scope_check import (
    NO_CONTEXT,
    OUTSIDE_THE_DECLARED_AXES,
    DeclaredScope,
    ScopeVerdict,
    check_commit_scope,
    declared_scope,
)

if TYPE_CHECKING:
    from beadloom.application.impact.boundary import GraphBoundary
    from beadloom.doc_sync.axes_section import AxesSection
    from beadloom.doc_sync.doc_quality import QualityFinding

_HEADER = "| Axis | Node | Sites | In scope | Why |\n|---|---|---|---|---|\n"


def _section(rows: str, *, derived_by: str = "`beadloom impact` over `a/b.py`") -> AxesSection:
    text = (
        "## Axes\n\n"
        f"> **Derived by:** {derived_by}\n"
        "> **Seed:** `none`\n"
        "> **Unresolved:** none\n\n" + _HEADER + rows
    )
    section = read_axes_section(text)
    assert section is not None
    return section


def _scope(
    rows: str,
    *,
    targets: tuple[str, ...] = (),
    contexts: dict[str, str] | None = None,
) -> DeclaredScope:
    return declared_scope(
        _section(rows),
        document=".claude/development/docs/features/KEY-1/RFC.md",
        target_nodes=targets,
        node_contexts=contexts if contexts is not None else _CONTEXTS,
    )


_CONTEXTS = {
    "sync-check": "doc-sync",
    "scanner": "doc-sync",
    "rule-engine": "graph",
    "ci-gate": "application",
}

_KEPT = "| callers | sync-check | 1 — `a:1` | yes | the surface |\n"
_RULED_OUT = "| co-writers | scanner | 2 — `b:2` | no | not this one |\n"
_UNDECIDED = "| callers | rule-engine | 1 — `c:3` | ? |  |\n"


class TestTheScopeADeclaredSectionPutsInsideTheApproval:
    def test_a_kept_row_puts_its_node_inside(self) -> None:
        assert _scope(_KEPT).kept == frozenset({"sync-check"})

    def test_a_kept_row_puts_its_bounded_context_inside(self) -> None:
        assert _scope(_KEPT).contexts == frozenset({"doc-sync"})

    def test_a_ruled_out_row_puts_neither_its_node_nor_its_context_inside(self) -> None:
        scope = _scope(_KEPT + _RULED_OUT)
        assert "scanner" not in scope.inside
        assert scope.ruled_out == {"scanner": ("co-writers",)}

    def test_a_node_kept_by_one_row_and_ruled_out_by_another_is_kept(self) -> None:
        # The person took it somewhere. A ruling elsewhere narrows that row's
        # axis rather than refusing the node.
        rows = _KEPT + "| co-writers | sync-check | 2 — `b:2` | no | not here |\n"
        scope = _scope(rows)
        assert "sync-check" in scope.inside
        assert scope.ruled_out == {}

    def test_an_undecided_row_is_not_a_kept_row(self) -> None:
        # Pinned on the grammar's own property rather than only on its effect:
        # `AxesSection.kept` is what `refs_line` and `work-item-type` also read.
        assert _section(_KEPT + _UNDECIDED).kept == _section(_KEPT).kept

    def test_an_undecided_row_widens_nothing(self) -> None:
        scope = _scope(_KEPT + _UNDECIDED)
        assert scope.inside == frozenset({"sync-check"})
        assert scope.contexts == frozenset({"doc-sync"})

    def test_an_undecided_row_narrows_nothing(self) -> None:
        assert _scope(_KEPT + _UNDECIDED).ruled_out == {}

    def test_the_undecided_rows_are_counted(self) -> None:
        assert _scope(_KEPT + _UNDECIDED).undecided == 1

    def test_a_derivation_target_is_inside_without_a_row(self) -> None:
        scope = _scope(_KEPT, targets=("rule-engine",))
        assert "rule-engine" in scope.inside

    def test_a_target_carries_its_bounded_context_in_with_it(self) -> None:
        scope = _scope(_KEPT, targets=("rule-engine",))
        assert scope.contexts == frozenset({"doc-sync", "graph"})

    def test_the_declared_axes_are_named_with_the_contexts_they_reach(self) -> None:
        assert _scope(_KEPT).declared() == "`callers` (doc-sync)"

    def test_a_section_keeping_nothing_says_so_rather_than_naming_an_empty_axis(self) -> None:
        assert "no axis keeps a node in scope" in _scope(_RULED_OUT).declared()


class TestAStagedPathJudgedAgainstThatScope:
    def test_a_path_a_kept_row_names_is_silent(self) -> None:
        verdict = check_commit_scope(
            ["src/a.py"], _scope(_KEPT), ownership={"src/a.py": ("sync-check", "doc-sync")}
        )
        assert verdict.findings == ()
        assert verdict.judged == 1

    def test_a_kept_node_is_inside_even_where_the_index_places_it_elsewhere(self) -> None:
        # The clause that survives no other. A kept node normally carries its
        # own context into `scope.contexts`, so the context clause below would
        # acquit its paths anyway — except that the two contexts come from
        # different reads: the section's map is `boundary.context_of(node)` and
        # a path's is `owner.domain`. Where they disagree, only the by-NAME
        # clause keeps the approval's own node inside. Added after deleting
        # `if node in scope.inside` left every other case in this file green.
        verdict = check_commit_scope(
            ["src/a.py"], _scope(_KEPT), ownership={"src/a.py": ("sync-check", "graph")}
        )
        assert verdict.findings == ()

    def test_a_derivation_target_is_inside_on_the_same_terms(self) -> None:
        verdict = check_commit_scope(
            ["src/f.py"],
            _scope(_KEPT, targets=("engine",), contexts=_CONTEXTS),
            ownership={"src/f.py": ("engine", "graph")},
        )
        assert verdict.findings == ()

    def test_a_path_in_a_declared_context_that_no_row_names_is_silent(self) -> None:
        # The second clause, and the one that keeps the check from being always
        # red: a sibling module in a context the work item already works in.
        verdict = check_commit_scope(
            ["src/b.py"], _scope(_KEPT), ownership={"src/b.py": ("engine", "doc-sync")}
        )
        assert verdict.findings == ()

    def test_a_path_in_a_context_no_declared_axis_reaches_is_reported(self) -> None:
        verdict = check_commit_scope(
            ["src/c.py"], _scope(_KEPT), ownership={"src/c.py": ("rule-engine", "graph")}
        )
        assert [f.check for f in verdict.findings] == [OUTSIDE_THE_DECLARED_AXES]

    def test_a_path_an_axis_rules_out_of_scope_is_reported(self) -> None:
        # Its context IS declared. The ruling wins, because the person wrote
        # "not this one" about the node itself.
        verdict = check_commit_scope(
            ["src/d.py"],
            _scope(_KEPT + _RULED_OUT),
            ownership={"src/d.py": ("scanner", "doc-sync")},
        )
        assert len(verdict.findings) == 1

    def test_the_ruling_finding_names_the_axis_that_ruled_it_out(self) -> None:
        verdict = check_commit_scope(
            ["src/d.py"],
            _scope(_KEPT + _RULED_OUT),
            ownership={"src/d.py": ("scanner", "doc-sync")},
        )
        assert "`co-writers`" in verdict.findings[0].excerpt

    def test_the_context_finding_names_every_declared_axis(self) -> None:
        verdict = check_commit_scope(
            ["src/c.py"], _scope(_KEPT), ownership={"src/c.py": ("rule-engine", "graph")}
        )
        assert "`callers` (doc-sync)" in verdict.findings[0].why

    def test_the_context_finding_names_the_context_the_path_is_in(self) -> None:
        verdict = check_commit_scope(
            ["src/c.py"], _scope(_KEPT), ownership={"src/c.py": ("rule-engine", "graph")}
        )
        assert "`graph`" in verdict.findings[0].excerpt

    def test_a_node_the_graph_places_in_no_context_says_so_rather_than_blank(self) -> None:
        verdict = check_commit_scope(
            ["src/e.py"], _scope(_KEPT), ownership={"src/e.py": ("loose", None)}
        )
        assert NO_CONTEXT in verdict.findings[0].excerpt

    def test_a_path_no_node_owns_is_counted_and_not_reported(self) -> None:
        verdict = check_commit_scope(
            ["README.md"], _scope(_KEPT), ownership={"README.md": (None, None)}
        )
        assert verdict.findings == ()
        assert (verdict.judged, verdict.unowned) == (0, 1)

    def test_a_path_the_ownership_map_never_saw_is_unowned_rather_than_outside(self) -> None:
        verdict = check_commit_scope(["nowhere.md"], _scope(_KEPT), ownership={})
        assert verdict.findings == ()
        assert verdict.unowned == 1

    def test_a_path_staged_twice_is_judged_once(self) -> None:
        verdict = check_commit_scope(
            ["src/c.py", "src/c.py"],
            _scope(_KEPT),
            ownership={"src/c.py": ("rule-engine", "graph")},
        )
        assert len(verdict.findings) == 1

    def test_the_undecided_count_travels_to_the_verdict(self) -> None:
        verdict = check_commit_scope(
            ["src/a.py"],
            _scope(_KEPT + _UNDECIDED),
            ownership={"src/a.py": ("sync-check", "doc-sync")},
        )
        assert verdict.undecided == 1

    def test_the_verdict_states_what_it_judged_and_what_it_could_not(self) -> None:
        verdict = check_commit_scope(
            ["src/a.py", "README.md"],
            _scope(_KEPT),
            ownership={"src/a.py": ("sync-check", "doc-sync"), "README.md": (None, None)},
        )
        assert "1 staged path(s) a node owns, 1 no node owns" in verdict.describe()

    def test_an_undecided_row_is_named_in_the_verdict_line(self) -> None:
        verdict = ScopeVerdict(undecided=2)
        assert "2 declared row(s) nobody decided" in verdict.describe()


class TestTheTargetsTheDerivationRanOver:
    def test_a_word_carrying_a_path_separator_is_a_target(self) -> None:
        section = _section(_KEPT, derived_by="`beadloom impact` over `doc_sync/x.py`")
        assert derived_targets(section) == ("doc_sync/x.py",)

    def test_the_rendered_field_names_both_the_target_and_the_sweep_root(self) -> None:
        section = _section(
            _KEPT, derived_by="`beadloom impact src/beadloom/x.py` over `src/beadloom`"
        )
        assert derived_targets(section) == ("src/beadloom/x.py", "src/beadloom")

    def test_a_word_outside_a_code_span_is_prose_rather_than_a_path(self) -> None:
        section = _section(_KEPT, derived_by="run over doc_sync/x.py by hand")
        assert derived_targets(section) == ()

    def test_a_symbol_target_carries_no_separator_and_is_not_returned(self) -> None:
        section = _section(_KEPT, derived_by="`beadloom impact write_yaml_atomic`")
        assert derived_targets(section) == ()

    def test_a_target_named_twice_is_one_target(self) -> None:
        section = _section(_KEPT, derived_by="`a/b.py` and `a/b.py`")
        assert derived_targets(section) == ("a/b.py",)


class TestWhichWorkItemABranchNames:
    @pytest.fixture
    def project(self, tmp_path: Path) -> Path:
        folder = tmp_path / ".claude" / "development" / "docs" / "features" / "KEY-1"
        folder.mkdir(parents=True)
        (folder / "RFC.md").write_text("# RFC\n", encoding="utf-8")
        return tmp_path

    def test_a_segment_of_the_branch_names_the_work_item(self, project: Path) -> None:
        found = work_item_of_branch(project, "features/KEY-1")
        assert found is not None
        assert found.name == "KEY-1"

    def test_the_bare_key_names_it_too(self, project: Path) -> None:
        assert work_item_of_branch(project, "KEY-1") is not None

    def test_a_segment_that_merely_contains_the_key_names_nothing(self, project: Path) -> None:
        # A segment match, not a substring one: `KEY-10` is a different item.
        assert work_item_of_branch(project, "features/KEY-10") is None

    def test_a_branch_naming_no_work_item_names_nothing(self, project: Path) -> None:
        assert work_item_of_branch(project, "main") is None


class TestEveryReasonToHaveCheckedNothing:
    def test_no_branch_is_a_reason_rather_than_a_pass(self, tmp_path: Path) -> None:
        scope, reason = scope_of_branch(tmp_path, branch=None)
        assert scope is None
        assert reason == NO_BRANCH

    def test_a_branch_naming_no_work_item_is_a_reason(self, tmp_path: Path) -> None:
        scope, reason = scope_of_branch(tmp_path, branch="features/NOPE")
        assert scope is None
        assert reason is not None
        assert "names no work item" in reason

    def test_a_work_item_with_no_axes_section_is_a_reason(self, tmp_path: Path) -> None:
        folder = tmp_path / ".claude" / "development" / "docs" / "features" / "KEY-1"
        folder.mkdir(parents=True)
        (folder / "BRIEF.md").write_text("# BRIEF\n\n## Problem\n\nnone.\n", encoding="utf-8")
        (tmp_path / ".beadloom").mkdir(exist_ok=True)
        scope, reason = scope_of_branch(tmp_path, branch="features/KEY-1")
        assert scope is None
        assert reason is not None
        assert "carries no `## Axes` section" in reason

    def test_a_run_that_checked_nothing_says_so(self, tmp_path: Path) -> None:
        run = scope_check(tmp_path, branch="main")
        assert not run.checked
        assert "NOT CHECKED" in run.describe()

    def test_a_run_that_checked_something_states_no_reason(self) -> None:
        assert ScopeRun().checked


class TestTheGitReadsTheComparisonIsBuiltOn:
    """Real git, in a real repository, because the ref form is the whole point."""

    @pytest.fixture
    def repo(self, tmp_path: Path) -> Path:
        def git(*args: str) -> None:
            subprocess.run(  # noqa: S603
                ["git", *args], cwd=tmp_path, check=True, capture_output=True  # noqa: S607
            )

        git("init", "-b", "main")
        git("config", "user.email", "t@example.com")
        git("config", "user.name", "t")
        (tmp_path / "base.txt").write_text("base\n", encoding="utf-8")
        (tmp_path / "shared.txt").write_text("one\n", encoding="utf-8")
        git("add", "base.txt", "shared.txt")
        git("commit", "-m", "base")
        git("switch", "-c", "features/KEY-1")
        (tmp_path / "mine.txt").write_text("mine\n", encoding="utf-8")
        git("add", "mine.txt")
        git("commit", "-m", "mine")
        return tmp_path

    def test_the_checked_out_branch_is_read(self, repo: Path) -> None:
        assert current_branch(repo) == "features/KEY-1"

    def test_a_detached_head_names_no_branch(self, repo: Path) -> None:
        subprocess.run(
            ["git", "checkout", "--detach", "HEAD"],  # noqa: S607
            cwd=repo,
            check=True,
            capture_output=True,
        )
        assert current_branch(repo) is None

    def test_the_branch_reports_what_it_changed_against_the_ref(self, repo: Path) -> None:
        assert paths_changed_since(repo, "main") == frozenset({"mine.txt"})

    def test_a_change_that_landed_on_the_ref_afterwards_is_not_this_branch_s(
        self, repo: Path
    ) -> None:
        """The three-dot form, on the shape that distinguishes it.

        Measured on this repository: with a local ``main`` two commits behind
        the remote, ``--since main`` reported ``src/beadloom/graph/linter.py``
        — another work item's LANDED change — as this branch's work, and
        ``--since origin/main`` did not. The trunk MODIFIES a file this branch
        never touched, which is the case ``--diff-filter=ACMR`` does not mask:
        an added file would read as a deletion from the branch's side and be
        filtered out, so a test built on one proves nothing about the form.
        """
        def git(*args: str) -> None:
            subprocess.run(  # noqa: S603
                ["git", *args], cwd=repo, check=True, capture_output=True  # noqa: S607
            )

        git("switch", "main")
        (repo / "shared.txt").write_text("two\n", encoding="utf-8")
        git("add", "shared.txt")
        git("commit", "-m", "theirs")
        git("switch", "features/KEY-1")
        assert paths_changed_since(repo, "main") == frozenset({"mine.txt"})

    def test_an_unknown_ref_is_not_an_empty_answer(self, repo: Path) -> None:
        assert paths_changed_since(repo, "no-such-ref") is None

    def test_a_directory_that_is_not_a_repository_answers_nothing(self, tmp_path: Path) -> None:
        assert current_branch(tmp_path) is None

    def test_an_existing_ref_is_reported_as_existing(self, repo: Path) -> None:
        assert ref_exists(repo, "main")
        assert not ref_exists(repo, "origin/main")

    def test_the_local_trunk_is_used_when_no_remote_tracking_ref_exists(
        self, repo: Path
    ) -> None:
        assert trunk_ref(repo) == "main"

    def test_the_remote_tracking_ref_is_preferred_when_it_exists(self, repo: Path) -> None:
        # What the pull request is compared against, and what a local trunk two
        # commits behind the remote gets wrong.
        subprocess.run(
            ["git", "update-ref", "refs/remotes/origin/main", "main"],  # noqa: S607
            cwd=repo,
            check=True,
            capture_output=True,
        )
        assert trunk_ref(repo) == "origin/main"


#: The rows of BDL-068's own ``## Axes`` table that the cases below have an
#: opinion about, excerpted from
#: ``.claude/development/docs/features/BDL-068/RFC.md``. Axis, node and decision
#: are the document's; the ``Why`` prose is abridged to fit a line, and the
#: guard below compares neither it nor the site count.
#:
#: **READ THIS BEFORE YOU APPEND S5's OR S6's ROWS.** The RFC's per-slice rule
#: obliges that table to GROW at the start of every slice, and appending to it
#: is expected and free: nothing here reads the live table for an enumeration,
#: so an append cannot make these cases red. What is NOT free is editing or
#: removing one of the six rows below —
#: :meth:`TestTheRowsTheseCasesDependOn.test_every_pinned_row_is_still_the_ruling_the_rfc_carries`
#: goes red on that, and it is the case that will tell you so. If a slice takes
#: `graph`, `doc-generator` or `agent-prime` back INTO scope, the excerpt and
#: the expected finding list here both move, and they move together.
#:
#: Six rows and not fifty: each one is here because a case below depends on the
#: ruling it carries. Three ``yes`` rows put a node inside by name and carry the
#: three bounded contexts the commit's other paths sit in; three ``no`` rows are
#: the rulings the commit is reported for. ``Sites`` and ``Why`` are carried for
#: readability and are deliberately NOT compared by the guard — a site line
#: number is re-derived every slice, so comparing it would rebuild the very
#: coupling this shape removes.
_ROWS_THESE_CASES_DEPEND_ON = (
    "| callers | `ci-gate` | 1, `_step_doc_spaces` (`application/gate.py:590`) | yes "
    "| The `## Axes` checks report through the Gate step |\n"
    "| callers | `cli-commands` | 1, `axes` (`services/commands/impact.py:88`) | yes "
    "| The command surface |\n"
    "| co-writers | `agentic-flow-setup` | 1, `scaffold` "
    "(`onboarding/agentic_flow_setup.py:360`) | yes | written by this epic |\n"
    "| callers | `graph` | 2, first `lint` (`graph/linter.py:103`) | no "
    "| read by this change and not written by it |\n"
    "| co-writers | `doc-generator` | 2, first `_load_graph_from_yaml` "
    "(`onboarding/doc_generator.py:28`) | no | read by this change and not written by it |\n"
    "| co-writers | `agent-prime` | 4, first `bootstrap_project` "
    "(`onboarding/scanner/bootstrap.py:36`) | no "
    "| read by this change and not written by it |\n"
)

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


def _repository_root() -> Path:
    """This checkout, or the reason it cannot answer an ownership question."""
    root = Path(__file__).resolve().parent.parent
    if not (root / ".beadloom" / "beadloom.db").is_file():
        pytest.skip("no index in this checkout, so no path can be resolved to a node")
    return root


def _paths_of(root: Path, commit: str) -> list[str]:
    """What *commit* changed, or a declared skip when it is not in this checkout."""
    result = subprocess.run(  # noqa: S603
        ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", commit],  # noqa: S607
        cwd=root,
        capture_output=True,
        text=True,
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


def _verdict_over(index_root: Path, scope: DeclaredScope, commit: str) -> ScopeVerdict:
    """*commit*'s real paths, owned by the real index, judged against *scope*.

    The history is always this repository's, whatever root carries the index:
    the pinned cases below judge real commits through a copy of the index and a
    document of their own, and a git read against that copy would find no
    history and skip silently.
    """
    boundary = _boundary_of(index_root)
    paths = _paths_of(_repository_root(), commit)
    ownership = {
        path: (owner.node, owner.domain)
        for path in paths
        for owner in (boundary.owner_of(path),)
    }
    return check_commit_scope(paths, scope, ownership=ownership)


@pytest.fixture(scope="module")
def pinned_project(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A project root carrying the pinned table and this repository's index.

    The index is COPIED rather than rebuilt because these cases are about the
    table and not about indexing, and a copy keeps the ownership answers the
    same ones the live cases get. Nothing else of this repository is copied, so
    the only thing the pinned run reads from a document is the six rows.
    """
    root = _repository_root()
    project = tmp_path_factory.mktemp("pinned-axes")
    (project / ".beadloom").mkdir()
    shutil.copy2(root / ".beadloom" / "beadloom.db", project / ".beadloom" / "beadloom.db")
    folder = project / ".claude" / "development" / "docs" / "features" / "BDL-068"
    folder.mkdir(parents=True)
    (folder / "RFC.md").write_text(
        "# RFC\n\n## Axes\n\n"
        "> **Derived by:** excerpted from BDL-068's own table, never re-derived here\n"
        "> **Seed:** `none`\n"
        "> **Unresolved:** none\n\n" + _HEADER + _ROWS_THESE_CASES_DEPEND_ON,
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
    slice's rows cannot make it red; see :data:`_ROWS_THESE_CASES_DEPEND_ON` for
    the split and for what an appender does have to know.

    Skipped where the history is absent — CI's tests job checks out at depth 1 —
    and the skip is declared rather than discovered.
    """

    @pytest.fixture
    def project(self) -> Path:
        return _repository_root()

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
        verdict = _verdict_over(project, live_scope, commit)
        assert verdict.findings == (), [f.path for f in verdict.findings]
        assert verdict.judged > 0, "a silent run over nothing has verified nothing"

    def test_a_commit_from_another_work_item_is_still_reported(
        self, project: Path, live_scope: DeclaredScope
    ) -> None:
        # The not-always-green clause, held as a relation rather than a list:
        # WHICH paths fall outside is a property of a table that grows every
        # slice, but THAT this epic's approval does not cover another work
        # item's commit is the claim, and it survives the growth.
        verdict = _verdict_over(project, live_scope, _A_FOREIGN_COMMIT)
        assert verdict.findings != ()

    def test_it_reports_only_paths_that_commit_changed(
        self, project: Path, live_scope: DeclaredScope
    ) -> None:
        verdict = _verdict_over(project, live_scope, _A_FOREIGN_COMMIT)
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
        verdict = _verdict_over(project, live_scope, _A_FOREIGN_COMMIT)
        for finding in verdict.findings:
            assert any(f"`{axis}`" in _message(finding) for axis in declared), finding

    def test_every_finding_sends_the_reader_to_the_document_that_ruled(
        self, project: Path, live_scope: DeclaredScope
    ) -> None:
        verdict = _verdict_over(project, live_scope, _A_FOREIGN_COMMIT)
        for finding in verdict.findings:
            assert live_scope.document in _message(finding)


class TestTheRowsTheseCasesDependOn:
    """The enumeration, judged against a PINNED excerpt of this epic's table.

    Everything about this run is real except the table: real commit, real paths,
    the real index resolving each path to its owning node and bounded context.
    Only the six rows in :data:`_ROWS_THESE_CASES_DEPEND_ON` are frozen, and
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
        self, pinned_project: Path, pinned_scope: DeclaredScope
    ) -> None:
        verdict = _verdict_over(pinned_project, pinned_scope, _A_FOREIGN_COMMIT)
        assert [f.path for f in verdict.findings] == [
            "src/beadloom/graph/linter.py",
            "src/beadloom/onboarding/doc_generator.py",
            "src/beadloom/onboarding/scanner/bootstrap.py",
            "src/beadloom/onboarding/scanner/doc_classify.py",
            "src/beadloom/onboarding/scanner/init_flow.py",
            "src/beadloom/onboarding/scanner/parent_edges.py",
        ]

    def test_a_path_a_kept_row_names_is_not_among_them(
        self, pinned_project: Path, pinned_scope: DeclaredScope
    ) -> None:
        # `ci-gate` and `cli-commands` are kept by name, so three of that
        # commit's source paths are inside the approval. Without this the list
        # above would also pass against a check that reported everything.
        verdict = _verdict_over(pinned_project, pinned_scope, _A_FOREIGN_COMMIT)
        assert "src/beadloom/application/gate.py" not in {f.path for f in verdict.findings}
        assert verdict.judged == 10

    def test_a_sibling_in_a_declared_context_is_not_among_them(
        self, pinned_project: Path, pinned_scope: DeclaredScope
    ) -> None:
        # `graph-files` is named by no row at all. It is inside because a kept
        # row reaches `onboarding`, which is the second clause of the rule on a
        # real path rather than on a fixture.
        verdict = _verdict_over(pinned_project, pinned_scope, _A_FOREIGN_COMMIT)
        assert "src/beadloom/onboarding/graph_files.py" not in {
            f.path for f in verdict.findings
        }

    def test_that_finding_names_the_axis_that_ruled_it_out(
        self, pinned_project: Path, pinned_scope: DeclaredScope
    ) -> None:
        verdict = _verdict_over(pinned_project, pinned_scope, _A_FOREIGN_COMMIT)
        assert "`callers`" in verdict.findings[0].excerpt

    def test_that_finding_names_the_node_the_ruling_is_about(
        self, pinned_project: Path, pinned_scope: DeclaredScope
    ) -> None:
        verdict = _verdict_over(pinned_project, pinned_scope, _A_FOREIGN_COMMIT)
        assert "`graph`" in verdict.findings[0].excerpt

    def test_every_pinned_row_is_still_the_ruling_the_rfc_carries(self) -> None:
        """The guard on the excerpt, and the only case an appender can trip.

        Appending S5's or S6's rows leaves this green. It goes red when one of
        the six rows this file depends on is EDITED or REMOVED, because that
        changes what the pinned cases are a test of, and the failure message is
        what tells the next person to come here.
        """
        project = _repository_root()
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
            "pins does: update `_ROWS_THESE_CASES_DEPEND_ON`, `_PINNED_RULINGS` "
            "and the expected finding list in `TestTheRowsTheseCasesDependOn` "
            "together, and re-measure rather than re-spell."
        )
