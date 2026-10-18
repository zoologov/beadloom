"""A lint result narrowed to the nodes a commit touches, and the sentence that says so.

BDL-083 S1a (``beadloom-7i09``, BDL-UX #326). The pre-commit hook judges the commit, not
the tree (BDL-UX #118), so the architecture lint it now runs is narrowed to the nodes that
own a staged path; what it left out is counted, and a git that could not answer narrows
nothing.
"""

from __future__ import annotations

from beadloom.graph.lint_scope import COMMIT_SCOPE_LEAD, scope_lint_to_commit
from beadloom.graph.linter import LintResult
from beadloom.graph.rule_engine import Violation

_OWNERS = {
    "frontend/src/widgets/panel/ui/Panel.ts": "widgets-panel",
    "frontend/src/widgets/panel/ui/Panel.spec.ts": "widgets-panel",
    "frontend/src/app/styles/base.ts": "app-styles",
}


def _owner_of(path: str) -> str | None:
    return _OWNERS.get(path)


def _violation(
    *, node: str | None, severity: str = "error", file_path: str | None = None
) -> Violation:
    return Violation(
        rule_name="layers",
        rule_description="layers import downward",
        rule_type="layer",
        severity=severity,
        file_path=file_path,
        line_number=None,
        from_ref_id=node,
        to_ref_id="app-styles",
        message="a lower layer depends on an upper one",
    )


def _result(*violations: Violation) -> LintResult:
    return LintResult(violations=list(violations), rules_evaluated=3)


class TestTheResultIsNarrowedToTheNodesTheCommitTouches:
    def test_a_finding_of_a_node_owning_a_staged_path_is_kept(self) -> None:
        kept = _violation(node="widgets-panel")
        scope = scope_lint_to_commit(
            _result(kept, _violation(node="pages-home")),
            frozenset({"frontend/src/widgets/panel/ui/Panel.spec.ts"}),
            _owner_of,
        )
        assert scope.result.violations == [kept]
        assert scope.nodes == ("widgets-panel",)
        assert scope.left_out == 1

    def test_a_finding_located_in_a_staged_file_is_kept_whatever_its_node(self) -> None:
        located = _violation(node=None, file_path="scripts/tool.py")
        scope = scope_lint_to_commit(
            _result(located), frozenset({"scripts/tool.py"}), _owner_of
        )
        assert scope.result.violations == [located]
        assert scope.owned == 0

    def test_a_finding_about_a_rule_rather_than_a_node_is_left_to_the_push_gate(self) -> None:
        advisory = _violation(node=None, severity="warn")
        scope = scope_lint_to_commit(
            _result(advisory),
            frozenset({"frontend/src/widgets/panel/ui/Panel.ts"}),
            _owner_of,
        )
        assert scope.result.violations == []
        assert scope.left_out == 1

    def test_the_rest_of_the_run_is_carried_unchanged(self) -> None:
        whole = _result(_violation(node="pages-home"))
        scope = scope_lint_to_commit(whole, frozenset(), _owner_of)
        assert scope.result.rules_evaluated == whole.rules_evaluated


class TestAGitThatDidNotAnswerNarrowsNothing:
    def test_the_whole_result_is_judged(self) -> None:
        whole = _result(_violation(node="pages-home"))
        scope = scope_lint_to_commit(whole, None, _owner_of)
        assert scope.result.violations == whole.violations
        assert scope.left_out == 0

    def test_the_sentence_says_the_whole_tree_was_judged(self) -> None:
        scope = scope_lint_to_commit(_result(), None, _owner_of)
        assert scope.sentence.startswith(COMMIT_SCOPE_LEAD)
        assert "whole tree" in scope.sentence


class TestTheSentenceCountsWhatItJudgedAndWhatItLeftOut:
    def test_it_names_the_nodes_and_counts_the_staged_paths_they_own(self) -> None:
        scope = scope_lint_to_commit(
            _result(_violation(node="widgets-panel"), _violation(node="pages-home")),
            frozenset({"frontend/src/widgets/panel/ui/Panel.ts", "README.md"}),
            _owner_of,
        )
        assert scope.sentence == (
            f"{COMMIT_SCOPE_LEAD}1 node(s) own 1 of 2 staged path(s) (widgets-panel); "
            "1 error(s), 0 warning(s) on them; 1 finding(s) elsewhere left to the "
            "pre-push Gate"
        )

    def test_a_commit_no_node_owns_says_no_node_was_judged(self) -> None:
        scope = scope_lint_to_commit(_result(), frozenset({"README.md"}), _owner_of)
        assert scope.sentence == (
            f"{COMMIT_SCOPE_LEAD}none of the 1 staged path(s) belongs to a node, so no "
            "node was judged; the pre-push Gate lints the whole tree"
        )

    def test_a_long_list_of_nodes_is_cut_and_says_so(self) -> None:
        owners = {f"src/n{i}.py": f"node-{i}" for i in range(7)}
        scope = scope_lint_to_commit(_result(), frozenset(owners), owners.get)
        assert "(node-0, node-1, node-2, node-3, node-4, and 2 more)" in scope.sentence
