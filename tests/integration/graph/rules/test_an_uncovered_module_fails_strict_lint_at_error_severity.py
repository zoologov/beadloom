"""An uncovered module fails ``lint --strict`` when the coverage rule is an error.

BDL-051 Slice 3b promoted ``module_coverage`` from warn to error once every module
was classified, so a future uncovered module breaks CI. The clean tree exiting 0
proves nothing about that; these cases prove the gate bites: an error-severity rule
and a new shadow module exit 1, the identical shadow at warn does not, the finding
carries ``error`` in the JSON, and classifying the module restores green.

Split out of ``tests/test_bead15_s3b_coverage.py`` by node (BDL-074 E1).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from click.testing import CliRunner

from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path


class TestErrorLevelRegressionGuard:
    """The promoted (error) coverage-lint must FAIL the gate on a new shadow module.

    This is the entire point of S3b: once every module is classified, the rule is
    promoted warn -> error so any *future* uncovered module breaks CI. The dev's
    tests prove the clean tree exits 0; these prove the gate bites otherwise.
    """

    def _make_project(self, tmp_path: Path, *, severity: str) -> Path:
        """A synthetic project mirroring the real rule: one covered + one shadow module."""
        project = tmp_path / "proj"
        graph_dir = project / ".beadloom" / "_graph"
        graph_dir.mkdir(parents=True)
        (project / "docs").mkdir()
        (graph_dir / "services.yml").write_text(
            "version: 1\n"
            "nodes:\n"
            "  - ref_id: beadloom\n"
            "    kind: service\n"
            "    summary: root\n"
            "  - ref_id: graph\n"
            "    kind: domain\n"
            "    summary: graph domain\n"
            "    source: src/beadloom/graph/\n"
            "  - ref_id: graph-loader\n"
            "    kind: component\n"
            "    summary: loader\n"
            "    source: src/beadloom/graph/loader.py\n"
            "edges:\n"
            "  - src: graph\n"
            "    dst: beadloom\n"
            "    kind: part_of\n"
            "  - src: graph-loader\n"
            "    dst: graph\n"
            "    kind: part_of\n"
        )
        (graph_dir / "rules.yml").write_text(
            "version: 3\n"
            "rules:\n"
            "  - name: module-coverage\n"
            "    description: every module must be a node or exempt\n"
            f"    severity: {severity}\n"
            "    module_coverage:\n"
            "      source_root: src/beadloom/\n"
            "      min_symbols: 1\n"
            "      exempt:\n"
            "        - '**/__init__.py'\n"
        )
        src = project / "src" / "beadloom" / "graph"
        src.mkdir(parents=True)
        (src / "loader.py").write_text(
            "# beadloom:component=graph-loader\ndef load():\n    pass\n"
        )
        # The SHADOW module: real code, no annotation, not a node source, not exempt.
        (src / "shadow.py").write_text("def secret():\n    return 1\n")
        return project

    def test_new_uncovered_module_fails_lint_strict_at_error(self, tmp_path: Path) -> None:
        """error severity + a new shadow module -> ``lint --strict`` exits NON-zero."""
        project = self._make_project(tmp_path, severity="error")
        runner = CliRunner()
        result = runner.invoke(main, ["lint", "--strict", "--project", str(project)])
        assert result.exit_code == 1, result.output
        assert "shadow.py" in result.output

    def test_same_shadow_module_at_warn_does_not_fail_strict(self, tmp_path: Path) -> None:
        """Control: the IDENTICAL shadow at warn severity does NOT fail --strict (rc 0).

        Proves it is the *error* promotion — not merely the finding's presence —
        that fails the gate. This is the warn->error contrast the bead asks for.
        """
        project = self._make_project(tmp_path, severity="warn")
        runner = CliRunner()
        result = runner.invoke(main, ["lint", "--strict", "--project", str(project)])
        assert result.exit_code == 0, result.output

    def test_finding_carries_error_severity_in_json(self, tmp_path: Path) -> None:
        """The shadow finding is emitted with severity ``error`` (not silently demoted)."""
        project = self._make_project(tmp_path, severity="error")
        runner = CliRunner()
        result = runner.invoke(main, ["lint", "--format", "json", "--project", str(project)])
        # stdout, not output: plain `lint` now names on STDERR that its exit
        # code ignores error-severity violations without --strict (BDL-UX #147),
        # and CliRunner's `output` merges the two streams.
        payload = json.loads(result.stdout)
        coverage = [v for v in payload["violations"] if v["rule_name"] == "module-coverage"]
        assert coverage, payload
        assert all(v["severity"] == "error" for v in coverage)
        assert any("shadow.py" in str(v["file_path"]) for v in coverage)

    def test_covering_the_module_restores_green(self, tmp_path: Path) -> None:
        """Annotating the shadow module makes ``lint --strict`` pass again (rc 0).

        Demonstrates the gate is satisfiable by classification, not just by lowering
        severity — the closed loop S3b establishes.
        """
        project = self._make_project(tmp_path, severity="error")
        shadow = project / "src" / "beadloom" / "graph" / "shadow.py"
        shadow.write_text("# beadloom:component=graph-loader\ndef secret():\n    return 1\n")
        runner = CliRunner()
        result = runner.invoke(main, ["lint", "--strict", "--project", str(project)])
        assert result.exit_code == 0, result.output
