"""An indexed layer rule the view cannot read is left out, and the others are still drawn.

The architecture view reads every ``layers`` rule from the index, not from
``rules.yml``. Before the data file carried every rule it read only the first, and
an unreadable row hid the strata altogether; now one row the view cannot use — not
JSON, JSON that is no object, an object that declares no layer — is left out and
the rules beside it are read as written. A scope that is not a non-empty string
reads as no scope, so the rule judges the whole graph rather than a container
nobody named.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

import pytest

from beadloom.application.site.layer_rules_view import declared_layer_rules
from beadloom.infrastructure.db import create_schema, open_db

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Iterator
    from pathlib import Path

#: A readable rule of two layers, as the reindex writes one.
_READABLE = {
    "layers": [{"name": "pages", "tag": "ui-pages"}, {"name": "shared", "tag": "ui-shared"}],
    "enforce": "top-down",
    "allow_skip": True,
    "edge_kind": "depends_on",
}


@pytest.fixture()
def conn(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    connection = open_db(tmp_path / "index.db")
    create_schema(connection)
    yield connection
    connection.close()


def _index_rule(conn: sqlite3.Connection, name: str, rule_json: str) -> None:
    conn.execute(
        "INSERT INTO rules (name, description, rule_type, rule_json) VALUES (?, '', 'layers', ?)",
        (name, rule_json),
    )
    conn.commit()


@pytest.mark.parametrize(
    "unreadable",
    [
        pytest.param("{not json", id="not-json"),
        pytest.param(json.dumps(["a", "list"]), id="not-an-object"),
        pytest.param(json.dumps({"layers": []}), id="no-layer"),
        pytest.param(json.dumps({"layers": [{"name": "untagged"}]}), id="no-tagged-layer"),
    ],
)
def test_an_unreadable_row_is_left_out_and_the_rule_beside_it_is_read(
    conn: sqlite3.Connection, unreadable: str
) -> None:
    _index_rule(conn, "a-broken", unreadable)
    _index_rule(conn, "b-frontend", json.dumps(_READABLE))

    rules = declared_layer_rules(conn)

    assert [(r.name, [layer.tag for layer in r.layers]) for r in rules] == [
        ("b-frontend", ["ui-pages", "ui-shared"])
    ]


def test_a_row_that_is_not_json_is_logged_by_its_rules_name(
    conn: sqlite3.Connection, caplog: pytest.LogCaptureFixture
) -> None:
    _index_rule(conn, "a-broken", "{not json")

    with caplog.at_level(logging.WARNING):
        declared_layer_rules(conn)

    assert any("'a-broken'" in record.getMessage() for record in caplog.records)


@pytest.mark.parametrize(
    ("declared", "read"),
    [
        pytest.param("shop-portal", "shop-portal", id="a-ref-id"),
        pytest.param("", None, id="empty"),
        pytest.param(7, None, id="not-a-string"),
    ],
)
def test_a_scope_is_read_only_when_it_names_a_container(
    conn: sqlite3.Connection, declared: object, read: str | None
) -> None:
    _index_rule(conn, "frontend", json.dumps({**_READABLE, "scope": declared}))

    (rule,) = declared_layer_rules(conn)

    assert rule.scope == read
