"""Self-checks of this repository's graph, rules and code structure (BDL-074 A3).

Moved out of ``tests/test_integration_v1.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import yaml
from click.testing import CliRunner

from beadloom.onboarding.graph_files import each_graph_file
from beadloom.services.cli import main
from tests.support.repository_root import REPO_ROOT as _PROJECT_ROOT

if TYPE_CHECKING:
    from pathlib import Path

_GRAPH_DIR = _PROJECT_ROOT / ".beadloom" / "_graph"


class TestGraphCompleteness:
    """Verify the architecture graph has the DDD domain structure.

    Read from the graph DIRECTORY rather than from one file since BDL-UX #265
    split this repository's graph into one file per node. `each_graph_file` is
    the one policy every reader of that directory holds, so this population
    cannot disagree with the loader's about which files count.
    """

    @staticmethod
    def _nodes() -> set[str]:
        return {
            str(node["ref_id"])
            for _path, data in each_graph_file(_GRAPH_DIR)
            for node in (data.get("nodes") or [])
            if isinstance(node, dict) and node.get("ref_id")
        }

    @staticmethod
    def _edges() -> list[dict[str, object]]:
        return [
            edge
            for _path, data in each_graph_file(_GRAPH_DIR)
            for edge in (data.get("edges") or [])
            if isinstance(edge, dict)
        ]

    def test_graph_has_domain_nodes(self) -> None:
        ref_ids = self._nodes()
        # All 5 DDD domains must be present
        for domain in ("context-oracle", "doc-sync", "graph", "onboarding", "infrastructure"):
            assert domain in ref_ids, f"Missing domain: {domain}"
        # Rule engine feature (was "linter" domain)
        assert "rule-engine" in ref_ids

    def test_graph_domain_edges(self) -> None:
        edges = self._edges()
        # graph domain part_of beadloom
        assert any(
            e["src"] == "graph" and e["dst"] == "beadloom" and e["kind"] == "part_of"
            for e in edges
        )
        # cli uses graph
        assert any(
            e["src"] == "cli" and e["dst"] == "graph" and e["kind"] == "uses" for e in edges
        )

    def test_rules_yml_exists(self) -> None:
        rules_path = _PROJECT_ROOT / ".beadloom" / "_graph" / "rules.yml"
        assert rules_path.is_file()
        data = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
        assert data["version"] == 3
        assert len(data["rules"]) >= 7


class TestSelfLint:
    """Run beadloom lint on its own codebase — on the self-check snapshot.

    ``lint`` reindexes before it judges, so run against this repository it WROTE
    the live index (BDL-074 A2); against the snapshot it writes the snapshot's.
    """

    def test_self_lint_clean(self, self_check_snapshot: Path) -> None:
        """Self-lint should produce 0 errors (warnings are acceptable)."""
        runner = CliRunner()
        result = runner.invoke(
            main, ["lint", "--project", str(self_check_snapshot), "--format", "json"]
        )
        assert result.exit_code == 0, result.output
        parsed = json.loads(result.stdout)
        assert parsed["summary"]["error_count"] == 0
        assert parsed["summary"]["rules_evaluated"] >= 7
