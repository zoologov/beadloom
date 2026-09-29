"""A mutation run covers a change or a sample, and says what it covered (BDL-074 D1).

Unit and integration tests of the product half of `beadloom-vr0b`: which functions
a diff touched, the population of a change over nodes and the binding, survivors
by node, and the interval of a score measured on a sample. The runner half — the
mutmut glue under `.github/scripts/` — is tested beside the workflow it serves,
in `tests/self_check/config/test_mutation_adapter.py`.
"""

from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING

import pytest
import yaml

from beadloom.application.mutation_scope import (
    ChangedFunction,
    ChangePlan,
    MutationCounters,
    NodeSelection,
    Survivor,
    changed_lines,
    describe_change,
    describe_sample,
    describe_survivors,
    plan_change,
    read_survivors,
    sample_interval,
    survivors_by_node,
    touched_functions,
    wilson_interval,
)
from beadloom.application.mutation_scope.change import MutationChangeError, diff_since
from beadloom.infrastructure.db import open_db

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path


# --------------------------------------------------------------------------- diff


_DIFF = """\
diff --git a/src/pkg/a.py b/src/pkg/a.py
index 1111111..2222222 100644
--- a/src/pkg/a.py
+++ b/src/pkg/a.py
@@ -3,0 +4,2 @@ def f():
+    x = 1
+    y = 2
@@ -10 +12 @@ def g():
-    return 1
+    return 2
@@ -20,3 +21,0 @@ class C:
-    a
-    b
-    c
diff --git a/src/pkg/gone.py b/src/pkg/gone.py
deleted file mode 100644
--- a/src/pkg/gone.py
+++ /dev/null
@@ -1,2 +0,0 @@
-x = 1
-y = 2
diff --git a/src/pkg/new.py b/src/pkg/new.py
new file mode 100644
--- /dev/null
+++ b/src/pkg/new.py
@@ -0,0 +1,2 @@
+def h():
+    pass
"""


class TestChangedLines:
    def test_added_lines_are_the_new_side_range(self) -> None:
        assert {4, 5} <= changed_lines(_DIFF)["src/pkg/a.py"]

    def test_a_replaced_line_is_its_new_position(self) -> None:
        assert 12 in changed_lines(_DIFF)["src/pkg/a.py"]

    def test_a_pure_deletion_touches_the_line_it_happened_after(self) -> None:
        """`+21,0` says the lines went after new line 21, which is inside what held them."""
        assert 21 in changed_lines(_DIFF)["src/pkg/a.py"]

    def test_the_file_set_is_exactly_the_touched_lines(self) -> None:
        assert changed_lines(_DIFF)["src/pkg/a.py"] == frozenset({4, 5, 12, 21})

    def test_a_deleted_file_names_no_lines_to_mutate(self) -> None:
        assert "src/pkg/gone.py" not in changed_lines(_DIFF)

    def test_a_new_file_is_every_line_it_holds(self) -> None:
        assert changed_lines(_DIFF)["src/pkg/new.py"] == frozenset({1, 2})

    def test_an_empty_diff_touches_nothing(self) -> None:
        assert changed_lines("") == {}


# ---------------------------------------------------------------------- functions


_SOURCE = '''\
"""A module."""

LIMIT = 3


@decorated
def top(a):
    def inner():
        return a
    return inner()


class Account:
    rate = 2

    def deposit(self, amount):
        return amount * self.rate

    async def audit(self):
        return None


async def later():
    return 1
'''


class TestTouchedFunctions:
    def test_a_line_in_a_top_level_function_names_it(self) -> None:
        touched = touched_functions(_SOURCE, [10])
        assert touched.functions == ("top",)

    def test_a_nested_function_belongs_to_the_function_that_holds_it(self) -> None:
        """A runner mutates the outer body; the inner function has no mutants of its own."""
        assert touched_functions(_SOURCE, [9]).functions == ("top",)

    def test_a_decorator_line_belongs_to_the_function_it_decorates(self) -> None:
        assert touched_functions(_SOURCE, [6]).functions == ("top",)

    def test_a_method_is_named_by_its_class(self) -> None:
        assert touched_functions(_SOURCE, [17]).functions == ("Account.deposit",)

    def test_an_async_method_and_function_count(self) -> None:
        assert touched_functions(_SOURCE, [20, 24]).functions == ("Account.audit", "later")

    def test_lines_outside_any_function_are_counted_not_named(self) -> None:
        touched = touched_functions(_SOURCE, [3, 14])
        assert touched.functions == ()
        assert touched.outside == 2

    def test_functions_are_named_once_in_source_order(self) -> None:
        touched = touched_functions(_SOURCE, [24, 9, 10, 17])
        assert touched.functions == ("top", "Account.deposit", "later")

    def test_a_file_that_does_not_parse_is_an_error(self) -> None:
        with pytest.raises(SyntaxError):
            touched_functions("def broken(:\n", [1])


# ---------------------------------------------------------------------- the plan


_GRAPH = {
    "nodes": [
        {"ref_id": "ledger", "kind": "domain", "summary": "Ledger", "source": "src/ledger/"},
        {
            "ref_id": "posting",
            "kind": "feature",
            "summary": "Posting",
            "source": "src/ledger/posting.py",
        },
    ],
    "edges": [{"src": "posting", "dst": "ledger", "kind": "part_of"}],
}

_POSTING = "def post(amount):\n    return amount\n\n\ndef reverse(amount):\n    return -amount\n"
_BALANCE = "def balance():\n    return 0\n"


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _git(project: Path, *args: str) -> str:
    result = subprocess.run(  # noqa: S603 - a fixed git argv in a temporary repository
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],  # noqa: S607
        cwd=project,
        check=True,
        capture_output=True,
        encoding="utf-8",
    )
    return result.stdout


def _reindex(project: Path) -> sqlite3.Connection:
    from beadloom.application.reindex import reindex

    reindex(project)
    return open_db(project / ".beadloom" / "beadloom.db")


@pytest.fixture()
def ledger(tmp_path: Path) -> Path:
    project = tmp_path / "ledger"
    _write(project, "src/ledger/__init__.py", "")
    _write(project, "src/ledger/posting.py", _POSTING)
    _write(project, "src/ledger/balance.py", _BALANCE)
    _write(project, "src/other/tool.py", "def tool():\n    return 1\n")
    _write(project, ".beadloom/config.yml", "languages:\n- .py\nscan_paths:\n- src\n")
    _write(project, ".beadloom/flow.yml", "mutation:\n  targets:\n  - src/ledger/\n")
    _write(project, ".beadloom/_graph/ledger.yml", yaml.safe_dump(_GRAPH, sort_keys=False))
    _write(project, "tests/unit/ledger/test_posting.py", "def test_a():\n    pass\n")
    _write(project, "tests/unit/ledger/test_balance.py", "def test_b():\n    pass\n")
    _write(project, "tests/test_flat.py", "def test_c():\n    pass\n")
    _git(project, "init", "-q", "-b", "main")
    _git(project, "add", "-A")
    _git(project, "commit", "-q", "-m", "base")
    return project


class TestPlanChange:
    def _plan(self, project: Path) -> ChangePlan:
        conn = _reindex(project)
        try:
            return plan_change(project, conn, diff_since(project, "HEAD"), base="HEAD")
        finally:
            conn.close()

    def test_a_changed_function_is_named_with_its_owning_node(self, ledger: Path) -> None:
        _write(ledger, "src/ledger/posting.py", _POSTING.replace("-amount", "0 - amount"))
        plan = self._plan(ledger)
        assert plan.functions == (ChangedFunction("src/ledger/posting.py", "reverse", "posting"),)
        assert not plan.empty

    def test_each_node_carries_only_the_tests_bound_to_it(self, ledger: Path) -> None:
        _write(ledger, "src/ledger/posting.py", _POSTING.replace("-amount", "0 - amount"))
        _write(ledger, "src/ledger/balance.py", _BALANCE.replace("0", "1"))
        plan = self._plan(ledger)
        by_node = {selection.node: selection for selection in plan.nodes}
        assert by_node["posting"].bound_tests == ("tests/unit/ledger/test_posting.py",)
        assert by_node["ledger"].bound_tests == ("tests/unit/ledger/test_balance.py",)
        assert by_node["ledger"].functions == ("balance",)

    def test_a_file_outside_the_declared_scope_is_counted_and_not_mutated(
        self, ledger: Path
    ) -> None:
        _write(ledger, "src/other/tool.py", "def tool():\n    return 2\n")
        plan = self._plan(ledger)
        assert plan.files_changed == 1
        assert plan.files_in_scope == ()
        assert plan.empty

    def test_the_files_the_binding_places_under_no_node_are_listed(self, ledger: Path) -> None:
        plan = self._plan(ledger)
        assert plan.unplaced_tests == ("tests/test_flat.py",)
        assert plan.test_files == 3

    def test_a_committed_change_on_a_branch_is_measured_from_the_merge_base(
        self, ledger: Path
    ) -> None:
        _git(ledger, "switch", "-q", "-c", "feature")
        _write(ledger, "src/ledger/balance.py", _BALANCE.replace("0", "1"))
        _git(ledger, "commit", "-q", "-am", "change")
        plan = self._plan_against(ledger, "main")
        assert [function.name for function in plan.functions] == ["balance"]

    def _plan_against(self, project: Path, base: str) -> ChangePlan:
        conn = _reindex(project)
        try:
            return plan_change(project, conn, diff_since(project, base), base=base)
        finally:
            conn.close()

    def test_a_file_that_does_not_parse_is_named_and_not_guessed(self, ledger: Path) -> None:
        _write(ledger, "src/ledger/balance.py", "def balance(:\n")
        plan = self._plan(ledger)
        assert plan.unread == ("src/ledger/balance.py",)
        assert plan.empty

    def test_an_unknown_base_is_an_error_that_names_it(self, ledger: Path) -> None:
        with pytest.raises(MutationChangeError, match="no-such-ref"):
            diff_since(ledger, "no-such-ref")


class TestDescribeChange:
    def _plan(self, **overrides: object) -> ChangePlan:
        fields: dict[str, object] = {
            "base": "main",
            "files_changed": 2,
            "files_in_scope": ("src/ledger/posting.py",),
            "unread": (),
            "functions": (ChangedFunction("src/ledger/posting.py", "post", "posting"),),
            "outside_lines": 0,
            "nodes": (
                NodeSelection("posting", ("post",), ("tests/unit/ledger/test_posting.py",)),
            ),
            "unplaced_tests": (),
            "test_files": 4,
        }
        fields.update(overrides)
        return ChangePlan(**fields)  # type: ignore[arg-type]  # the fields are the dataclass's

    def test_the_population_is_stated_in_functions_files_and_nodes(self) -> None:
        text = "\n".join(describe_change(self._plan()))
        assert (
            "Population: 1 function(s) in 1 file(s) of the declared scope, over 1 node(s): posting"
            in text
        )

    def test_an_empty_population_says_so_and_says_why(self) -> None:
        text = "\n".join(describe_change(self._plan(functions=(), files_in_scope=())))
        assert "Population: empty" in text
        assert "2 file(s) changed, 0 of them in the declared scope" in text

    def test_unplaced_tests_are_stated_as_a_share(self) -> None:
        """The share is counted by placement, as `ctx` counts it (BDL-074 F1)."""
        plan = self._plan(
            unplaced_tests=("a", "b", "c"), test_placements={"mirror": 1, "unplaced": 3}
        )
        text = "\n".join(describe_change(plan))
        assert "3 of 4 test file(s) are unplaced" in text

    def test_changed_lines_outside_any_function_are_stated(self) -> None:
        text = "\n".join(describe_change(self._plan(outside_lines=3)))
        assert "3 changed line(s)" in text


# --------------------------------------------------------------------- survivors


class TestSurvivors:
    def test_a_survivor_list_is_read(self, tmp_path: Path) -> None:
        path = tmp_path / "s.json"
        path.write_text(
            json.dumps([{"path": "src/a.py", "mutant": "a.x_f__mutmut_1"}]), encoding="utf-8"
        )
        assert read_survivors(path) == (Survivor("src/a.py", "a.x_f__mutmut_1"),)

    @pytest.mark.parametrize(
        "text",
        ["not json", "{}", '[{"path": "src/a.py"}]', '[{"path": 1, "mutant": "m"}]'],
    )
    def test_a_file_that_holds_no_survivor_list_is_unreadable(
        self, tmp_path: Path, text: str
    ) -> None:
        path = tmp_path / "s.json"
        path.write_text(text, encoding="utf-8")
        assert read_survivors(path) is None

    def test_an_absent_file_is_unreadable(self, tmp_path: Path) -> None:
        assert read_survivors(tmp_path / "absent.json") is None

    def test_survivors_are_grouped_by_the_most_specific_owner(self, ledger: Path) -> None:
        conn = _reindex(ledger)
        try:
            grouped = survivors_by_node(
                conn,
                (
                    Survivor("src/ledger/posting.py", "m1"),
                    Survivor("src/ledger/balance.py", "m2"),
                    Survivor("src/nowhere.py", "m3"),
                ),
            )
        finally:
            conn.close()
        assert grouped == {
            "posting": (Survivor("src/ledger/posting.py", "m1"),),
            "ledger": (Survivor("src/ledger/balance.py", "m2"),),
            None: (Survivor("src/nowhere.py", "m3"),),
        }

    def test_the_description_names_each_node_and_its_count(self) -> None:
        lines = describe_survivors(
            {"posting": (Survivor("src/p.py", "m1"), Survivor("src/p.py", "m2"))}
        )
        assert lines[0] == "Survivors: 2 over 1 node(s)"
        assert "posting: 2 survivor(s)" in lines[1]

    def test_no_survivors_is_stated(self) -> None:
        assert describe_survivors({}) == ["Survivors: none"]


# ------------------------------------------------------------------------ sample


class TestSampleInterval:
    def test_the_wilson_interval_of_a_known_case(self) -> None:
        low, high = wilson_interval(180, 200)
        assert round(low, 4) == 0.8506
        assert round(high, 4) == 0.9343

    def test_a_perfect_sample_still_has_a_lower_bound_under_one(self) -> None:
        low, high = wilson_interval(50, 50)
        assert high == 1.0
        assert low < 0.95

    def test_no_scored_mutant_has_no_interval(self) -> None:
        counters = MutationCounters(values={"killed": 0, "survived": 0})
        assert sample_interval(counters, population=100) is None

    def test_timeouts_count_as_killed_as_in_the_score(self) -> None:
        counters = MutationCounters(values={"killed": 170, "timeout": 10, "survived": 20})
        interval = sample_interval(counters, population=7000)
        assert interval is not None
        assert (interval.low, interval.high) == wilson_interval(180, 200)
        assert interval.sample == 200

    def test_a_sample_larger_than_its_population_is_refused(self) -> None:
        counters = MutationCounters(values={"killed": 9, "survived": 1})
        with pytest.raises(ValueError, match="population"):
            sample_interval(counters, population=5)

    def test_the_description_states_the_sample_and_the_interval(self) -> None:
        counters = MutationCounters(values={"killed": 180, "survived": 20})
        interval = sample_interval(counters, population=7000)
        assert interval is not None
        text = describe_sample(interval)
        assert "a random sample of 200 of 7000 mutants" in text
        assert "95% interval 85.1% to 93.4%" in text


class TestASampledScoreIsHeldToItsFloorByItsInterval:
    """A sample of 150 from a scope at 0.89 reads under 0.88 about a third of the
    time, so the floor fails a sample only when its whole interval lies under it."""

    def _run(self, tmp_path: Path, killed: int, survived: int, *extra: str) -> tuple[int, str]:
        from click.testing import CliRunner

        from beadloom.services.cli import main

        project = tmp_path / "p"
        _write(project, "src/ledger/posting.py", _POSTING)
        _write(project, ".beadloom/config.yml", "languages:\n- .py\nscan_paths:\n- src\n")
        _write(project, ".beadloom/flow.yml", "mutation:\n  targets:\n  - src/ledger/\n")
        stats = project / "stats.json"
        stats.write_text(json.dumps({"killed": killed, "survived": survived}), encoding="utf-8")
        result = CliRunner().invoke(
            main,
            [
                "mutation",
                "--project",
                str(project),
                "--stats",
                str(stats),
                "--target",
                "src/ledger/",
                "--min-score",
                "0.88",
                *extra,
            ],
        )
        return result.exit_code, result.output

    def test_a_point_estimate_under_the_floor_whose_interval_reaches_it_passes(
        self, tmp_path: Path
    ) -> None:
        code, output = self._run(tmp_path, 172, 28, "--sample-of", "7000")
        assert code == 0, output
        assert "interval reaches it" in output

    def test_an_interval_wholly_under_the_floor_fails(self, tmp_path: Path) -> None:
        code, output = self._run(tmp_path, 150, 50, "--sample-of", "7000")
        assert code == 1, output
        assert "interval lies wholly under it" in output

    def test_without_a_sample_the_point_estimate_is_held_to_the_floor(
        self, tmp_path: Path
    ) -> None:
        code, output = self._run(tmp_path, 172, 28)
        assert code == 1, output
