"""The bootstrap's post-condition on `kind: domain` nodes (BDL-067, BDL-UX #192).

`bootstrap_project` writes `domain-needs-parent` into the adopter's `rules.yml`
whenever it writes a domain, and one of its branches used to write the domain
without the edge that rule requires — so `beadloom init` exited 0 and
`beadloom ci` exited 1 on a rule the same command had just authored.

The fix is stated as a post-condition over the whole function rather than as a
patch to that branch, so these tests are stated the same way: they assert over
the nodes and edges `bootstrap_project` returns, for every preset the module can
select, and over the helper that enforces it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from beadloom.onboarding.presets import PRESETS
from beadloom.onboarding.scanner.bootstrap import (
    _missing_domain_parent_edges,
    bootstrap_project,
)

if TYPE_CHECKING:
    from pathlib import Path


def _flat_project(root: Path, name: str = "orders-web") -> Path:
    """One source file directly under `src/` — the shape with no clusters.

    `_cluster_with_children` yields only subdirectories that contain code, so a
    flat source dir yields nothing and the bootstrap takes its fallback branch.
    """
    project = root / name
    (project / "src").mkdir(parents=True)
    (project / "src" / "index.ts").write_text("export const orders = [];\n", encoding="utf-8")
    return project


def _orphan_domains(result: dict[str, Any]) -> list[str]:
    nodes: list[dict[str, str]] = result["nodes"]
    edges: list[dict[str, str]] = result["edges"]
    parented = {e["src"] for e in edges if e["kind"] == "part_of"}
    return [n["ref_id"] for n in nodes if n["kind"] == "domain" and n["ref_id"] not in parented]


class TestTheInvariantHoldsForEveryPreset:
    """No preset the module can select writes a parentless domain."""

    @pytest.mark.parametrize("preset_name", sorted(PRESETS))
    def test_a_flat_project_writes_no_parentless_domain(
        self, tmp_path: Path, preset_name: str
    ) -> None:
        project = _flat_project(tmp_path, name=f"flat-{preset_name}")

        result = bootstrap_project(project, preset_name=preset_name)

        assert _orphan_domains(result) == []

    @pytest.mark.parametrize("preset_name", sorted(PRESETS))
    def test_the_edge_names_the_root_node_as_written(
        self, tmp_path: Path, preset_name: str
    ) -> None:
        """Not a recomputed name: cluster refs are sanitised and the root is not.

        `_sanitize_ref_id` strips parentheses, so a project named `orders (web)`
        has a root ref_id no recomputation reproduces. An edge built from the
        recomputed name resolves to nothing.
        """
        project = _flat_project(tmp_path, name=f"orders ({preset_name})")

        result = bootstrap_project(project, preset_name=preset_name)

        nodes: list[dict[str, str]] = result["nodes"]
        edges: list[dict[str, str]] = result["edges"]
        ref_ids = {n["ref_id"] for n in nodes}
        assert "(" in next(n["ref_id"] for n in nodes if n["kind"] == "service")
        assert [e for e in edges if e["dst"] not in ref_ids] == []


class TestTheHelperStatesThePostCondition:
    """`_missing_domain_parent_edges` names exactly the domains that lack a parent."""

    def test_a_parentless_domain_gets_one_edge_to_the_root(self) -> None:
        nodes = [
            {"ref_id": "orders (web)", "kind": "service"},
            {"ref_id": "src", "kind": "domain"},
        ]

        missing = _missing_domain_parent_edges(nodes, [], "orders (web)")

        assert missing == [{"src": "src", "dst": "orders (web)", "kind": "part_of"}]

    def test_a_domain_that_already_has_a_parent_is_left_alone(self) -> None:
        """The classifier's parent wins — the root is the fallback, not an override."""
        nodes = [
            {"ref_id": "supply-chain", "kind": "service"},
            {"ref_id": "platform", "kind": "domain"},
            {"ref_id": "platform-orders", "kind": "domain"},
        ]
        edges = [
            {"src": "platform", "dst": "supply-chain", "kind": "part_of"},
            {"src": "platform-orders", "dst": "platform", "kind": "part_of"},
        ]

        assert _missing_domain_parent_edges(nodes, edges, "supply-chain") == []

    def test_a_depends_on_edge_does_not_count_as_a_parent(self) -> None:
        """`domain-needs-parent` requires `part_of`; any other kind leaves it violated."""
        nodes = [
            {"ref_id": "ledger", "kind": "service"},
            {"ref_id": "billing", "kind": "domain"},
            {"ref_id": "audit", "kind": "domain"},
        ]
        edges = [{"src": "billing", "dst": "audit", "kind": "depends_on"}]

        missing = _missing_domain_parent_edges(nodes, edges, "ledger")

        assert {e["src"] for e in missing} == {"billing", "audit"}

    def test_a_domain_whose_ref_id_is_the_root_gets_no_self_edge(self) -> None:
        """A top-level dir named after the project collides with the root node.

        `part_of` from a node to itself is not a parent, and the loader would
        have to resolve a cycle of length one. Nothing is emitted.
        """
        nodes = [{"ref_id": "ledger", "kind": "service"}, {"ref_id": "ledger", "kind": "domain"}]

        assert _missing_domain_parent_edges(nodes, [], "ledger") == []

    def test_nodes_of_other_kinds_are_not_this_rule_s_business(self) -> None:
        nodes = [
            {"ref_id": "ledger", "kind": "service"},
            {"ref_id": "models", "kind": "entity"},
            {"ref_id": "rest", "kind": "feature"},
        ]

        assert _missing_domain_parent_edges(nodes, [], "ledger") == []
