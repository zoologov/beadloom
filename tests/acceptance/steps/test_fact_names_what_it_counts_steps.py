"""Step implementations for `features/fact_names_what_it_counts.feature`.

BDL-062 `.4`, closing BDL-UX #193. The steps run the real ``DocScanner`` and the
real ``FactRegistry`` — a stub keyword table would agree with itself and prove
nothing about the collision the scenarios describe.

The module is named ``test_*`` so default pytest collection picks the scenarios
up: the acceptance suite runs inside ``uv run pytest``, not beside it.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.doc_sync.audit import FactRegistry
from beadloom.doc_sync.scanner import DocScanner
from beadloom.infrastructure.db import create_schema

scenarios("../features/fact_names_what_it_counts.feature")

FACT_NAME = "nodes_with_framework"
RETIRED_FACT_NAME = "framework_count"


@pytest.fixture()
def world() -> dict[str, Any]:
    return {}


@given(parsers.parse('a line of prose reading "{line}"'))
def _line(world: dict[str, Any], line: str) -> None:
    world["line"] = line


@given(
    parsers.parse(
        "a project whose graph records a test framework on {count:d} of its nodes"
    )
)
def _graph_with_frameworks(world: dict[str, Any], count: int, tmp_path: Path) -> None:
    root = tmp_path / "adopter"
    root.mkdir()
    (root / "pyproject.toml").write_text(
        '[project]\nname = "invoice-svc"\nversion = "3.7.0"\n', encoding="utf-8"
    )
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    for index in range(count):
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, extra) VALUES (?, ?, ?)",
            (f"node-{index}", "feature", '{"tests": {"framework": "pytest"}}'),
        )
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, extra) VALUES (?, ?, ?)",
        ("node-bare", "feature", "{}"),
    )
    conn.commit()
    world["root"] = root
    world["db"] = conn


@when("the scanner reads that line for fact mentions")
def _scan(world: dict[str, Any]) -> None:
    world["mentions"] = DocScanner().scan_line(
        world["line"], origin=Path("prose.md"), line_number=1
    )


@when("the audit collects that project's facts")
def _collect(world: dict[str, Any]) -> None:
    world["fact_set"] = FactRegistry().collect_set(world["root"], world["db"])


@then("no mention claims how many nodes declare a framework")
def _no_framework_mention(world: dict[str, Any]) -> None:
    # Both names are checked. Before the rename the claim was carried by
    # ``framework_count``, so checking only the new name would make this
    # scenario pass on the defect it was written for; after the rename the old
    # name is a regression guard against re-registering those keywords.
    node_counting = {FACT_NAME, RETIRED_FACT_NAME}
    matched = [m for m in world["mentions"] if m.fact_name in node_counting]
    assert matched == [], (
        f"a sentence about the frameworks a parser supports was read as a claim "
        f"about nodes: {[(m.fact_name, m.value) for m in matched]}"
    )


@then(parsers.parse("a mention claims that {count:d} nodes declare a framework"))
def _framework_mention(world: dict[str, Any], count: int) -> None:
    values = [m.value for m in world["mentions"] if m.fact_name == FACT_NAME]
    assert count in values, (
        f"no {FACT_NAME} mention of {count}; the line produced "
        f"{[(m.fact_name, m.value) for m in world['mentions']]}"
    )


@then(parsers.parse("the fact named {fact_name} has the value {value:d}"))
def _fact_value(world: dict[str, Any], fact_name: str, value: int) -> None:
    facts = world["fact_set"].facts
    assert fact_name in facts, f"{fact_name} absent; declared: {sorted(facts)}"
    assert facts[fact_name].value == value


@then(parsers.parse("no fact is named {fact_name}"))
def _fact_absent(world: dict[str, Any], fact_name: str) -> None:
    fact_set = world["fact_set"]
    assert fact_name not in fact_set.facts, f"{fact_name} is still declared"
    assert fact_name not in fact_set.not_applicable, (
        f"{fact_name} is still declared, as a declined fact"
    )
