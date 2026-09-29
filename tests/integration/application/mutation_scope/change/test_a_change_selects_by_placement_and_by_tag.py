"""A change's test selection: unplaced files as the fallback, acceptance files by tag.

BDL-074 G1, review finding M2. The plan used to list every test file bound to no
node as the runner's fallback — unplaced files, and the acceptance step and
self-check files that bind to no node BY DESIGN. Those two kinds never become
bound, so the fallback could never empty, while the workflow said it would.

Now each kind is decided by what it is:

- an UNPLACED file (the layout has not reached it) is the fallback, because it may
  exercise the changed node and the binding cannot say;
- an ACCEPTANCE step file is selected when the scenarios it loads carry the
  changed node's ``@node:`` tag, and not otherwise;
- a SELF-CHECK tests the repository's own files, not the changed code, and is
  never selected.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.application.mutation_scope import change_payload, describe_change, plan_change
from tests.support.suite_index import SuiteFile, SuiteIndex, SuiteNode

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path

POSTING = "src/ledger/posting.py"
_POSTING_SOURCE = "def post(amount: int) -> int:\n    return amount\n"
_DIFF = (
    f"diff --git a/{POSTING} b/{POSTING}\n"
    f"--- a/{POSTING}\n+++ b/{POSTING}\n"
    "@@ -2 +2 @@\n-    return amount\n+    return amount + 0\n"
)

POSTING_STEPS = "tests/acceptance/steps/test_posting_steps.py"
VAULT_STEPS = "tests/acceptance/steps/test_vault_steps.py"
SHARED_STEPS = "tests/acceptance/steps/common/test_shared_steps.py"
FLAT = "tests/test_flat.py"
SELF_CHECK = "tests/self_check/docs/test_readme.py"

_FEATURES = {
    "tests/acceptance/features/posting.feature": (
        "@node:posting\nFeature: posting\n\n  Scenario: a post\n    Given a ledger\n"
    ),
    "tests/acceptance/features/vault.feature": (
        "Feature: vault\n\n  @node:vault\n  Scenario: a vault\n    Given a vault\n"
    ),
}
_LOADS = "from pytest_bdd import scenarios\n\nscenarios({!r})\n"
_STEPS = {
    POSTING_STEPS: _LOADS.format("../features/posting.feature"),
    VAULT_STEPS: _LOADS.format("../features/vault.feature"),
    SHARED_STEPS: (
        "import pytest_bdd\n\n"
        'pytest_bdd.scenarios("../../features/vault.feature", "../../features/posting.feature")\n'
    ),
}


def _project(root: Path) -> sqlite3.Connection:
    """A ledger whose ``post`` is the change, and one test file of every placement."""
    for relative, text in {
        POSTING: _POSTING_SOURCE,
        ".beadloom/flow.yml": "mutation:\n  targets:\n  - src/ledger/\n",
        **_FEATURES,
        **_STEPS,
    }.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    conn = SuiteIndex(
        nodes=[SuiteNode("posting"), SuiteNode("vault")],
        files=[
            SuiteFile("tests/unit/ledger/test_posting.py", ref_id="posting"),
            SuiteFile(FLAT, placement="unplaced", kind=None),
            SuiteFile("tests/unit/vault/test_vault.py", placement="unowned"),
            SuiteFile(POSTING_STEPS, placement="other_kind", kind="acceptance"),
            SuiteFile(VAULT_STEPS, placement="other_kind", kind="acceptance"),
            SuiteFile(SHARED_STEPS, placement="other_kind", kind="acceptance"),
            SuiteFile(SELF_CHECK, placement="other_kind", kind="self_check"),
        ],
    ).build(root)
    conn.execute("UPDATE nodes SET source = ? WHERE ref_id = 'posting'", (POSTING,))
    return conn


class TestTheFallbackHoldsUnplacedFilesOnly:
    def test_only_the_unplaced_file_is_the_fallback(self, tmp_path: Path) -> None:
        conn = _project(tmp_path)
        try:
            plan = plan_change(tmp_path, conn, _DIFF, base="main")
        finally:
            conn.close()

        assert plan.unplaced_tests == (FLAT,)

    def test_no_self_check_or_acceptance_file_is_in_the_fallback(self, tmp_path: Path) -> None:
        conn = _project(tmp_path)
        try:
            payload = change_payload(plan_change(tmp_path, conn, _DIFF, base="main"))
        finally:
            conn.close()

        assert payload["unplaced_tests"] == [FLAT]
        assert "unbound_tests" not in payload


class TestAcceptanceFilesAreSelectedByTheirScenariosNodeTags:
    def _selection(self, tmp_path: Path) -> dict[str | None, tuple[str, ...]]:
        conn = _project(tmp_path)
        try:
            plan = plan_change(tmp_path, conn, _DIFF, base="main")
        finally:
            conn.close()
        return {selection.node: selection.acceptance_tests for selection in plan.nodes}

    def test_a_step_file_whose_feature_names_the_node_is_selected(self, tmp_path: Path) -> None:
        assert POSTING_STEPS in self._selection(tmp_path)["posting"]

    def test_a_step_file_whose_features_name_another_node_is_not(self, tmp_path: Path) -> None:
        assert VAULT_STEPS not in self._selection(tmp_path)["posting"]

    def test_a_step_file_loading_several_features_is_selected_by_any_of_them(
        self, tmp_path: Path
    ) -> None:
        assert self._selection(tmp_path)["posting"] == (SHARED_STEPS, POSTING_STEPS)

    def test_the_payload_and_the_statement_carry_the_selection(self, tmp_path: Path) -> None:
        conn = _project(tmp_path)
        try:
            plan = plan_change(tmp_path, conn, _DIFF, base="main")
        finally:
            conn.close()

        nodes = change_payload(plan)["nodes"]
        assert isinstance(nodes, list)
        assert nodes[0]["acceptance_tests"] == [SHARED_STEPS, POSTING_STEPS]
        text = "\n".join(describe_change(plan))
        assert "posting: post; 1 test file(s) bound, 2 acceptance step file(s) by tag" in text
