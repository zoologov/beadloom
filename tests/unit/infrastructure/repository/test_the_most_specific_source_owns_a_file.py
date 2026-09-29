"""The node whose source covers a file most specifically owns it; a blank source owns nothing.

``most_specific_owner`` is the one ownership rule: the test binding calls it for a
test file's mirror, and ``get_owning_ref_id`` for a code file. Split out of
``tests/test_a_test_file_binds_to_the_node_its_path_mirrors.py`` (BDL-074
``beadloom-2mj3.7``), where it was stated as the binding's own; pure, so unit.
"""

from __future__ import annotations

from beadloom.infrastructure.repository import most_specific_owner

#: A directory node, a child directory node and a single-file node beside it.
NODE_SOURCES = (
    ("graph", "src/app/graph/"),
    ("rule-engine", "src/app/graph/rules/"),
    ("loader", "src/app/graph/loader.py"),
    ("cli", "src/app/cli.py"),
)


class TestOwnership:
    """The one ownership rule, as a pure function over (ref_id, source) pairs."""

    def test_the_longest_covering_prefix_owns_the_file(self) -> None:
        assert most_specific_owner(NODE_SOURCES, "src/app/graph/rules/engine.py") == "rule-engine"

    def test_a_file_source_owns_only_itself(self) -> None:
        assert most_specific_owner(NODE_SOURCES, "src/app/graph/loader_edges.py") == "graph"

    def test_a_blank_source_owns_nothing(self) -> None:
        assert most_specific_owner((("root", ""),), "src/app/cli.py") is None
