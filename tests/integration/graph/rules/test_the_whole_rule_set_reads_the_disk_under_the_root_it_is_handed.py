"""``evaluate_all`` hands its project root to every rule that reads the disk.

A ``module_coverage`` rule enumerates the modules under ``project_root / source_root``,
and the liveness pass asks the same folder whether the rule has anything to judge. Both
must read the root the caller named: the working directory is somewhere else (the suite
starts every test in an empty one), so a rule that fell back to it would judge nothing and
call the rule inert.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.graph.rules import (
    LIVENESS_RULE_TYPE,
    ModuleCoverageRule,
    ScenarioBindingRule,
    evaluate_all,
    inert_rule_names,
)
from tests.support.in_memory_graph import add_node, open_graph
from tests.support.suite_index import write_feature

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Iterator
    from pathlib import Path

RULE = ModuleCoverageRule(
    name="every-module-is-classified",
    description="every module is a node or exempt",
    source_root="src/app",
)


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    """A project whose one module exists on disk only: the index holds no symbol of it."""
    module = tmp_path / "src" / "app" / "orphan.py"
    module.parent.mkdir(parents=True)
    module.write_text("VALUE = 1\n", encoding="utf-8")
    return tmp_path


@pytest.fixture()
def conn() -> Iterator[sqlite3.Connection]:
    db = open_graph()
    add_node(db, "app", "service")
    yield db
    db.close()


def test_a_module_found_only_on_disk_under_the_root_is_reported(
    conn: sqlite3.Connection, project: Path
) -> None:
    violations = evaluate_all(conn, [RULE], project_root=project)

    assert [v.file_path for v in violations if v.rule_type == "module_coverage"] == [
        "src/app/orphan.py"
    ]


def test_the_finding_for_that_module_carries_a_hint_naming_its_file(
    conn: sqlite3.Connection, project: Path
) -> None:
    violations = evaluate_all(conn, [RULE], project_root=project)

    (finding,) = [v for v in violations if v.rule_type == "module_coverage"]
    assert finding.remediation is not None
    assert finding.remediation.startswith("classify `src/app/orphan.py`")


def test_a_rule_whose_modules_exist_only_on_disk_is_not_reported_inert(
    conn: sqlite3.Connection, project: Path
) -> None:
    violations = evaluate_all(conn, [RULE], project_root=project)

    assert [v for v in violations if v.rule_type == LIVENESS_RULE_TYPE] == []


def test_a_rule_whose_modules_exist_only_on_disk_is_not_counted_inert(
    conn: sqlite3.Connection, project: Path
) -> None:
    inert = inert_rule_names(conn, [RULE], project_root=project)

    assert inert == set()


def test_a_finding_with_no_file_sorts_before_the_findings_of_its_rule_that_have_one(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    """The population statement carries no file, so only an empty sort key puts it first.

    The path is capitalised on purpose: ``Specs/`` sorts before most strings a missing
    file could be keyed as, so a key other than the empty string reorders the two.
    """
    write_feature(tmp_path, "Specs/nowhere/a.feature", "Feature: F\n\n  Scenario: S\n")
    rule = ScenarioBindingRule(name="sb", description="d", features="Specs/**/*.feature")

    violations = evaluate_all(conn, [rule], project_root=tmp_path)

    assert [v.file_path for v in violations] == [None, "Specs/nowhere/a.feature"]
