"""Tests for the ``beadloom config-check`` CLI command (BDL-039 F3 BEAD-03).

Exits 1 on drift, 0 clean; ``--fix`` regenerates via the same refresh
path and re-checks.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from click.testing import CliRunner

from beadloom.onboarding.scanner import generate_agents_md
from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path


def _write_rules_yml(project_root: Path, *, domains: list[str]) -> None:
    graph_dir = project_root / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True, exist_ok=True)
    rules = "rules:\n"
    for d in domains:
        rules += (
            f"  - name: {d}-needs-parent\n"
            f"    require: {{}}\n"
            f"    description: domain {d}\n"
        )
    (graph_dir / "rules.yml").write_text(rules, encoding="utf-8")


class TestConfigCheckCLI:
    def test_clean_exits_zero(self, tmp_path: Path) -> None:
        _write_rules_yml(tmp_path, domains=["graph"])
        generate_agents_md(tmp_path)

        result = CliRunner().invoke(
            main, ["config-check", "--project", str(tmp_path)]
        )
        assert result.exit_code == 0

    def test_drift_exits_one_and_reports(self, tmp_path: Path) -> None:
        _write_rules_yml(tmp_path, domains=["graph"])
        generate_agents_md(tmp_path)
        _write_rules_yml(tmp_path, domains=["graph", "contracts"])

        result = CliRunner().invoke(
            main, ["config-check", "--project", str(tmp_path)]
        )
        assert result.exit_code == 1
        assert "AGENTS.md" in result.output
        assert "setup-rules --refresh" in result.output

    def test_fix_regenerates_and_clears(self, tmp_path: Path) -> None:
        _write_rules_yml(tmp_path, domains=["graph"])
        generate_agents_md(tmp_path)
        _write_rules_yml(tmp_path, domains=["graph", "contracts"])

        result = CliRunner().invoke(
            main, ["config-check", "--fix", "--project", str(tmp_path)]
        )
        assert result.exit_code == 0

        # A follow-up check is clean.
        recheck = CliRunner().invoke(
            main, ["config-check", "--project", str(tmp_path)]
        )
        assert recheck.exit_code == 0
