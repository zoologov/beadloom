"""A ``check`` rule reports each threshold it is given, under its own name.

The per-layer cohesion checks of a Feature-Sliced frontend are ``check`` rules with
``max_symbols``, and ``max_files`` and ``min_doc_coverage`` share the evaluator.
These cases pin what a finding carries (the rule's name, description, type and
severity), where each threshold's boundary lies, and how the documentation
coverage ratio is counted, so that a finding cannot drift away from the rule
that produced it.

The graph is a disposable in-memory index built through the real schema.
"""

from __future__ import annotations

import sqlite3
from dataclasses import replace
from typing import TYPE_CHECKING

import pytest

from beadloom.graph.rules import CardinalityRule, NodeMatcher, evaluate_cardinality_rules
from beadloom.infrastructure.db import create_schema

if TYPE_CHECKING:
    from collections.abc import Iterator

_RULE_NAME = "slice-size"
_RULE_DESCRIPTION = "A slice of the widgets layer stays small"


@pytest.fixture()
def index() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    yield conn
    conn.close()


def _node(conn: sqlite3.Connection, ref_id: str, kind: str = "component") -> None:
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary, source, extra) VALUES (?, ?, ?, ?, ?)",
        (ref_id, kind, "", f"src/{ref_id}/", "{}"),
    )


def _files(conn: sqlite3.Connection, ref_id: str, count: int) -> None:
    for number in range(count):
        path = f"src/{ref_id}/module_{number}.py"
        conn.execute(
            "INSERT INTO file_index (path, hash, kind, indexed_at) VALUES (?, ?, ?, ?)",
            (path, f"{ref_id}-{number}", "code", "2026-10-09"),
        )
        conn.execute(
            "INSERT INTO code_symbols (file_path, symbol_name, kind, line_start, line_end,"
            " file_hash) VALUES (?, ?, ?, ?, ?, ?)",
            (path, f"symbol_{number}", "function", 1, 2, f"{ref_id}-{number}"),
        )


def _pairs(conn: sqlite3.Connection, ref_id: str, *statuses: str) -> None:
    for number, status in enumerate(statuses):
        conn.execute(
            "INSERT INTO sync_state (doc_path, code_path, ref_id, code_hash_at_sync,"
            " doc_hash_at_sync, synced_at, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (f"docs/{ref_id}/{number}.md", f"src/{ref_id}/", ref_id, "c", "d", "t", status),
        )


_UNBOUNDED = CardinalityRule(
    name=_RULE_NAME,
    description=_RULE_DESCRIPTION,
    for_matcher=NodeMatcher(kind="component"),
    severity="error",
)


@pytest.mark.parametrize(
    "rule",
    [
        pytest.param(replace(_UNBOUNDED, max_symbols=2), id="max_symbols"),
        pytest.param(replace(_UNBOUNDED, max_files=2), id="max_files"),
        pytest.param(replace(_UNBOUNDED, min_doc_coverage=0.5), id="min_doc_coverage"),
    ],
)
def test_a_finding_carries_the_identity_of_the_rule_that_produced_it(
    index: sqlite3.Connection, rule: CardinalityRule
) -> None:
    # Arrange: three files and symbols, and no documentation pair at all.
    _node(index, "board")
    _files(index, "board", 3)

    # Act
    violations = evaluate_cardinality_rules(index, [rule])

    # Assert
    assert [
        (v.rule_name, v.rule_description, v.rule_type, v.severity, v.from_ref_id)
        for v in violations
    ] == [(_RULE_NAME, _RULE_DESCRIPTION, "cardinality", "error", "board")]


@pytest.mark.parametrize(
    "rule",
    [
        pytest.param(replace(_UNBOUNDED, max_symbols=3), id="max_symbols"),
        pytest.param(replace(_UNBOUNDED, max_files=3), id="max_files"),
    ],
)
def test_a_node_exactly_at_the_limit_is_not_reported(
    index: sqlite3.Connection, rule: CardinalityRule
) -> None:
    # Arrange
    _node(index, "board")
    _files(index, "board", 3)

    # Act
    violations = evaluate_cardinality_rules(index, [rule])

    # Assert
    assert violations == []


def test_a_node_the_matcher_skips_does_not_end_the_judgement_of_the_nodes_after_it(
    index: sqlite3.Connection,
) -> None:
    # Arrange: the first row of the table is outside the matcher.
    _node(index, "shop", kind="service")
    _node(index, "board")
    _files(index, "board", 3)

    # Act
    violations = evaluate_cardinality_rules(index, [replace(_UNBOUNDED, max_files=2)])

    # Assert
    assert [v.from_ref_id for v in violations] == ["board"]


@pytest.mark.parametrize(
    ("statuses", "minimum", "reported"),
    [
        (("ok", "unverified", "stale", "missing"), 0.5, False),
        (("ok", "unverified", "stale", "missing"), 0.6, True),
        (("ok",), 1.0, False),
        (("stale",), 0.1, True),
    ],
    ids=["half-at-half", "half-under-sixty", "one-ok-pair-whole", "one-stale-pair"],
)
def test_coverage_counts_every_pair_not_known_to_be_behind(
    index: sqlite3.Connection, statuses: tuple[str, ...], minimum: float, reported: bool
) -> None:
    # Arrange
    _node(index, "board")
    _pairs(index, "board", *statuses)
    rule = replace(_UNBOUNDED, min_doc_coverage=minimum)

    # Act
    violations = evaluate_cardinality_rules(index, [rule])

    # Assert
    assert bool(violations) is reported


def test_a_coverage_finding_states_the_ratio_and_the_minimum(
    index: sqlite3.Connection,
) -> None:
    # Arrange
    _node(index, "board")
    _pairs(index, "board", "ok", "unverified", "stale", "missing")

    # Act
    violations = evaluate_cardinality_rules(index, [replace(_UNBOUNDED, min_doc_coverage=0.6)])

    # Assert
    assert [v.message for v in violations] == [
        f"Node 'board' has doc coverage 50% (min 60%): rule '{_RULE_NAME}'"
    ]
