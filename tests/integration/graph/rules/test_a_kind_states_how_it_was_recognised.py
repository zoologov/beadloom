"""`test_binding` states how each kind it does not judge was recognised (BDL-074 G2).

Review ``beadloom-b9ll`` m4: every file under ``tests/self_check/`` or
``tests/acceptance/`` was left out of the file leg by its folder, and nothing said
where that folder came from or that a unit test dropped into it would be reported
as "a sanctioned outcome". The kind folders are now configuration
(``tests.kinds`` in ``.beadloom/config.yml``), the reindex records the layout it
recognised kinds by, and the population line states it — including the limit: the
folder is trusted, what a file holds is not checked against its kind.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.graph.rules import (
    SUITE_POPULATION_RULE_TYPE,
    TestBindingRule,
    evaluate_test_binding_rules,
)
from beadloom.infrastructure.db import set_meta
from beadloom.infrastructure.repository import TEST_LAYOUT_KEY, RecordedTestLayout
from tests.support.suite_index import SuiteFile, SuiteIndex, SuiteNode

if TYPE_CHECKING:
    from pathlib import Path

_TRUSTED = "the folder is trusted, not verified: what a file holds is not checked against its kind"


def _suite() -> SuiteIndex:
    return SuiteIndex(
        nodes=[SuiteNode("ledger", kind="domain")],
        files=[
            SuiteFile("tests/unit/test_ledger.py", ref_id="ledger"),
            SuiteFile("tests/e2e/steps/test_story.py", placement="other_kind", kind="acceptance"),
            SuiteFile(
                "tests/self_check/test_readme.py", placement="other_kind", kind="self_check"
            ),
        ],
    )


def _population(tmp_path: Path, layout: RecordedTestLayout | None) -> str:
    conn = _suite().build(tmp_path)
    try:
        if layout is not None:
            set_meta(conn, TEST_LAYOUT_KEY, layout.encode())
        violations = evaluate_test_binding_rules(
            conn, [TestBindingRule(name="bind", description="d", files="tests/**")]
        )
    finally:
        conn.close()
    return "\n".join(v.message for v in violations if v.rule_type == SUITE_POPULATION_RULE_TYPE)


_LAYOUT = RecordedTestLayout(
    kind_prefixes={
        "unit": ("tests/unit/",),
        "integration": ("tests/integration/",),
        "acceptance": ("tests/e2e/",),
        "self_check": ("tests/self_check/",),
    },
    declared_kinds=frozenset({"acceptance"}),
    beside_code=False,
    roots=("tests",),
    frameworks=("pytest",),
)


class TestTheRecognitionIsStated:
    def test_a_declared_kind_names_its_folder_and_where_it_was_declared(
        self, tmp_path: Path
    ) -> None:
        population = _population(tmp_path, _LAYOUT)
        assert (
            "recognised by the folder `tests/e2e/` declared in .beadloom/config.yml "
            f"(`tests.kinds`) ({_TRUSTED})"
        ) in population

    def test_a_default_kind_names_its_folder_as_the_default(self, tmp_path: Path) -> None:
        population = _population(tmp_path, _LAYOUT)
        assert (
            "recognised by the folder `tests/self_check/`, Beadloom's default, which no "
            f"`tests.kinds` entry replaces ({_TRUSTED})"
        ) in population

    def test_an_index_that_recorded_no_layout_says_so(self, tmp_path: Path) -> None:
        population = _population(tmp_path, None)
        assert (
            "recognised by its folder alone (the index records no test layout, so where "
            "that folder was declared is not stated: reindex to record it)"
        ) in population
