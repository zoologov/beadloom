"""Self-checks of this repository's graph, rules and code structure (BDL-074 A3).

Moved out of
``tests/unit/application/source_derivation/test_one_part_of_ancestry_walk_serves_the_rule_engine.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

import ast

import yaml

from beadloom.application.source_derivation.source_tree import (
    module_tree,
    python_files,
)
from tests.support.repository_root import REPO_ROOT

SRC = REPO_ROOT / "src"
PACKAGE = SRC / "beadloom"
RULES_YML = REPO_ROOT / ".beadloom" / "_graph" / "rules.yml"


#: Files still holding a layer tag as a literal, each with the bead that removes
#: it. Compared for EQUALITY, so a stale entry fails as loudly as a new literal:
#: an exemption that outlives its reason is how the next `_LAYER_TAGS` gets in.
#:
#: Empty since BDL-070 A5 (`beadloom-06dz`) removed `_LAYER_TAGS` / `_LAYER_RANK`
#: from `architecture_view`, which was the last holder. An empty set is a
#: stronger assertion than a populated one, not a weaker: every module in `src/`
#: is now inside the scan with no exception to argue about.
LITERAL_EXEMPTIONS: set[str] = set()


def _declared_layer_tags() -> set[str]:
    """Every layer tag this project DECLARES, read from the declaration."""
    document = yaml.safe_load(RULES_YML.read_text(encoding="utf-8"))
    tags = set(document.get("tags") or {})
    for rule in document.get("rules") or []:
        for layer in (rule.get("layers") or []) if isinstance(rule, dict) else []:
            tags.add(str(layer["tag"]))
    return tags


class TestNoLayerTagIsWrittenDown:
    """A layer is whatever the declaration names one — in `src/`, nothing else."""

    def test_the_declaration_names_the_tags_this_scan_looks_for(self) -> None:
        assert _declared_layer_tags() == {
            "layer-service",
            "layer-application",
            "layer-domain",
            "layer-infra",
        }

    def test_no_module_holds_a_layer_tag_as_a_literal_outside_the_named_exemptions(
        self,
    ) -> None:
        declared = _declared_layer_tags()
        holders = {
            str(path.relative_to(SRC))
            for path in python_files(PACKAGE)
            for node in ast.walk(module_tree(path))
            if isinstance(node, ast.Constant) and node.value in declared
        }
        assert holders == LITERAL_EXEMPTIONS

    def test_the_shared_lookup_itself_holds_no_tag(self) -> None:
        source = (PACKAGE / "graph" / "rules" / "layers.py").read_text(encoding="utf-8")
        assert not any(tag in source for tag in _declared_layer_tags())
