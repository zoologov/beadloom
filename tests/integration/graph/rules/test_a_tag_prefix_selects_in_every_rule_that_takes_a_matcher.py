"""A ``tag_prefix`` matcher selects by tags in every rule type that takes a matcher.

BDL-080 S2b (`beadloom-5wh2`). An evaluator loads a node's tags only when one of
its rules reads them, and a matcher handed no tags skips its tag test, so an
evaluator that did not know about the prefix would select EVERY node of the kind:
the rule would over-report rather than fall silent. Each case below puts a node
outside the prefix where a broken evaluator would report it.

The project is written to disk and indexed with the real reindex; the tags
(``ui-*``, ``tier-*``) are none of this repository's.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.graph.linter import lint
from tests.support.tiered_project import write_tiered_project

if TYPE_CHECKING:
    from pathlib import Path

    from beadloom.graph.linter import LintResult

_NODES = [
    ("shop", "service", []),
    ("board", "component", ["ui-widgets"]),
    ("search", "component", ["ui-features"]),
    ("ledger", "component", ["tier-core"]),
    ("stock", "component", ["tier-core"]),
]

_EDGES = [
    ("board", "shop", "part_of"),
    ("board", "ledger", "uses"),
    ("ledger", "stock", "uses"),
]

_MODULES = {
    "src/ledger/__init__.py": '"""The ledger."""\n\nBALANCE = 0\n',
    "src/board/__init__.py": (
        '"""A board reading the ledger."""\n\nfrom ledger import BALANCE\n\n'
        '__all__ = ["BALANCE"]\n'
    ),
    "src/stock/__init__.py": (
        '"""Stock reading the ledger."""\n\nfrom ledger import BALANCE\n\n'
        '__all__ = ["BALANCE"]\n'
    ),
}


def _lint(tmp_path: Path, rule: str) -> LintResult:
    project = write_tiered_project(
        tmp_path / "shop",
        nodes=_NODES,
        edges=_EDGES,
        more_rules=rule,
        modules=_MODULES,
    )
    return lint(project)


def _named(result: LintResult, rule_name: str) -> set[str]:
    return {
        str(v.from_ref_id)
        for v in result.violations
        if v.rule_name == rule_name and "cannot fire" not in v.message
    }


def test_require_judges_only_the_nodes_whose_tag_begins_with_the_prefix(
    tmp_path: Path,
) -> None:
    rule = (
        "  - name: ui-in-shop\n"
        '    description: "a slice belongs to the shop"\n'
        "    require:\n"
        "      for: { tag_prefix: ui- }\n"
        "      has_edge_to: { ref_id: shop }\n"
        "      edge_kind: part_of\n"
    )

    assert _named(_lint(tmp_path, rule), "ui-in-shop") == {"search"}


def test_forbid_edge_judges_only_the_edges_from_the_prefix(tmp_path: Path) -> None:
    rule = (
        "  - name: ui-not-to-core\n"
        '    description: "a slice does not use the core"\n'
        "    forbid:\n"
        "      from: { tag_prefix: ui- }\n"
        "      to: { tag_prefix: tier- }\n"
        "      edge_kind: uses\n"
    )

    assert _named(_lint(tmp_path, rule), "ui-not-to-core") == {"board"}


def test_deny_judges_only_the_imports_from_the_prefix(tmp_path: Path) -> None:
    rule = (
        "  - name: ui-imports-no-core\n"
        '    description: "a slice imports nothing from the core"\n'
        "    deny:\n"
        "      from: { tag_prefix: ui- }\n"
        "      to: { tag_prefix: tier- }\n"
    )

    assert _named(_lint(tmp_path, rule), "ui-imports-no-core") == {"board"}
