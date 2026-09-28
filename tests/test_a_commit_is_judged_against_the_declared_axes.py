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
silently. :data:`ROWS_THESE_CASES_DEPEND_ON` states what that means for the
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

import subprocess
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
from tests.support.axes_table import HEADER

if TYPE_CHECKING:
    from pathlib import Path

    from beadloom.doc_sync.axes_section import AxesSection


def _section(rows: str, *, derived_by: str = "`beadloom impact` over `a/b.py`") -> AxesSection:
    text = (
        "## Axes\n\n"
        f"> **Derived by:** {derived_by}\n"
        "> **Seed:** `none`\n"
        "> **Unresolved:** none\n\n" + HEADER + rows
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


