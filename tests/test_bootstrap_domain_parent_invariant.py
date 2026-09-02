"""The bootstrap's post-condition on `kind: domain` nodes (BDL-067, BDL-UX #192).

`bootstrap_project` writes `domain-needs-parent` into the adopter's `rules.yml`
whenever it writes a domain, and one of its branches used to write the domain
without the edge that rule requires — so `beadloom init` exited 0 and
`beadloom ci` exited 1 on a rule the same command had just authored.

The fix is stated as a post-condition over the whole function rather than as a
patch to that branch, so these tests are stated the same way: they assert over
the nodes and edges `bootstrap_project` returns, for every preset the module can
select.

The post-condition itself is no longer this writer's own. It is shared with
`doc_classify.import_docs`, the other writer of nodes, and it is stated over both
of them in `tests/test_one_parent_post_condition_over_every_writer.py` — where
the cases about the rule (which nodes get an edge, and to what) moved with it in
BDL-067 `.21`. What stays here is what only this writer can answer: that the
graph it actually produces satisfies the rule, for every preset it can select.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from beadloom.onboarding.presets import PRESETS
from beadloom.onboarding.scanner.bootstrap import bootstrap_project

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
