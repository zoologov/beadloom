"""Self-checks of this repository's graph, rules and code structure (BDL-074 A3).

Moved out of
``tests/integration/graph/rules/test_a_layer_the_declaration_names_and_no_node_is_in.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

import yaml

from beadloom.application.impact.boundary import open_boundary
from beadloom.application.impact.unread_ownership import unread_ownership
from beadloom.graph.rules.layer_declaration import (
    layers_no_node_is_in,
)
from beadloom.graph.rules.loader import load_rules
from beadloom.graph.rules.node_tags import node_tags
from beadloom.graph.rules.types import LayerRule
from tests.support.repository_root import REPO_ROOT

if TYPE_CHECKING:
    from pathlib import Path

#: The file this bead gives an owner, relative to the project root.
THE_RULES_FILE = ".beadloom/_graph/rules.yml"


class TestThisRepository:
    """What the removal and the new check do to this project's own graph."""

    def test_the_rules_file_carries_no_tags_catalog(self) -> None:
        """Q5, as data: one declaration of a node's layer, and it is the node."""
        data = yaml.safe_load((REPO_ROOT / THE_RULES_FILE).read_text(encoding="utf-8"))
        assert "tags" not in data

    def test_every_declared_layer_is_populated_here(
        self, self_check_snapshot: Path
    ) -> None:
        """The neutrality claim for this repository, measured rather than argued."""
        db_path = self_check_snapshot / ".beadloom" / "beadloom.db"
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            declared = [
                rule
                for rule in load_rules(self_check_snapshot / ".beadloom" / "_graph" / "rules.yml")
                if isinstance(rule, LayerRule)
            ]
            tags = node_tags(conn).as_mapping()
            for rule in declared:
                assert layers_no_node_is_in(rule.layers, tags) == ()
        finally:
            conn.close()

    def test_exactly_one_node_owns_the_rules_file(self, self_check_snapshot: Path) -> None:
        """Measured over every node in the graph, not over one impact answer.

        `impact` derives the nodes it names from Python call sites, and this
        file is YAML, so no code sweep can reach its owner. The claim the bead
        makes — one owner, not none and not two — is therefore held against the
        whole node population, which is the stronger measurement.
        """
        boundary = open_boundary(self_check_snapshot)
        db_path = self_check_snapshot / ".beadloom" / "beadloom.db"
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            every_node = [str(row[0]) for row in conn.execute("SELECT ref_id FROM nodes")]
        finally:
            conn.close()
        owners = [
            owned.node
            for owned in unread_ownership(boundary, every_node, self_check_snapshot)
            if THE_RULES_FILE in owned.files
        ]
        assert len(owners) == 1

    def test_the_owner_owns_the_rules_file_and_nothing_else(
        self, self_check_snapshot: Path
    ) -> None:
        """So the `Owns unread` cell reads `1 — .beadloom/_graph/rules.yml`.

        A node whose source were the whole `_graph/` directory would own a
        hundred files and the cell would lead with whichever sorted first.
        """
        boundary = open_boundary(self_check_snapshot)
        owned = unread_ownership(boundary, ["architecture-rules"], self_check_snapshot)
        assert [entry.files for entry in owned] == [(THE_RULES_FILE,)]
