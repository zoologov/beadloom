"""Every node's tags are read once per run, and a row that cannot be read has no tags.

The node-tags unit layer (BDL-074 E1). :class:`NodeTags` needs only something
that answers ``execute("SELECT ref_id, extra FROM nodes")`` with rows, so the
cases below hand it a stand-in that returns fixed rows and counts how often it
was asked. No index is opened: what is under test is how the rows are read, and
when — not SQLite.

The four malformed shapes are the table in :func:`_read_all_tags`'s docstring:
each of them answers "no tags" rather than ending the run.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

import pytest

from beadloom.graph.rules.node_tags import NodeTags, node_tags

if TYPE_CHECKING:
    import sqlite3


class _Rows:
    """A connection stand-in: fixed ``(ref_id, extra)`` rows, and a count of reads."""

    def __init__(self, rows: list[tuple[str, str | None]]) -> None:
        self._rows = rows
        self.reads = 0

    def execute(self, sql: str) -> list[tuple[str, str | None]]:
        assert sql == "SELECT ref_id, extra FROM nodes"
        self.reads += 1
        return list(self._rows)


def _tags_over(rows: _Rows) -> NodeTags:
    """The tag lookup over the stand-in, typed as the connection it stands in for."""
    return node_tags(cast("sqlite3.Connection", rows))


def _extra(*tags: str) -> str:
    return json.dumps({"tags": list(tags)})


class TestTheTagsANodeCarries:
    def test_a_node_answers_the_tags_it_declares(self) -> None:
        # Arrange
        tags = _tags_over(_Rows([("web", _extra("tier-web", "public"))]))

        # Act / Assert
        assert tags.of("web") == {"tier-web", "public"}

    def test_a_node_the_graph_does_not_hold_has_none(self) -> None:
        # Arrange
        tags = _tags_over(_Rows([("web", _extra("tier-web"))]))

        # Act / Assert
        assert tags.of("store") == set()

    def test_an_object_without_a_tags_key_has_none(self) -> None:
        # Arrange
        tags = _tags_over(_Rows([("web", json.dumps({"owner": "ops"}))]))

        # Act / Assert
        assert tags.of("web") == set()

    def test_the_whole_map_holds_only_tagged_nodes(self) -> None:
        # Arrange
        rows = [("web", _extra("tier-web")), ("bare", _extra()), ("none", None)]
        tags = _tags_over(_Rows(rows))

        # Act / Assert
        assert dict(tags.as_mapping()) == {"web": {"tier-web"}}


class TestARowThatCannotBeReadHasNoTags:
    """One unreadable row answers "no tags" for that node and breaks nothing else."""

    @pytest.mark.parametrize(
        "extra",
        [None, "null", "3", '"x"', "{not json"],
        ids=["sql-null", "json-null", "a-number", "a-string", "not-json"],
    )
    def test_the_row_answers_the_empty_set(self, extra: str | None) -> None:
        # Arrange
        tags = _tags_over(_Rows([("odd", extra), ("web", _extra("tier-web"))]))

        # Act / Assert
        assert tags.of("odd") == set()
        assert tags.of("web") == {"tier-web"}


class TestTheTableIsReadOnceAndOnlyWhenAsked:
    def test_nothing_is_read_until_the_first_question(self) -> None:
        # Arrange
        rows = _Rows([("web", _extra("tier-web"))])

        # Act
        _tags_over(rows)

        # Assert
        assert rows.reads == 0

    def test_many_questions_read_the_table_once(self) -> None:
        # Arrange
        rows = _Rows([("web", _extra("tier-web")), ("store", _extra("tier-store"))])
        tags = _tags_over(rows)

        # Act
        tags.of("web")
        tags.of("store")
        tags.as_mapping()

        # Assert
        assert rows.reads == 1
