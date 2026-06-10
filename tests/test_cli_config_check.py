"""Tests for the ``beadloom config-check`` CLI command (BDL-039 F3 BEAD-03).

Exits 1 on drift, 0 clean; ``--fix`` regenerates via the same refresh
path and re-checks.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from click.testing import CliRunner

from beadloom.onboarding.agentic_flow_setup import scaffold
from beadloom.onboarding.scanner import generate_agents_md
from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path


def _scaffolded_project(tmp_path: Path) -> Path:
    project = tmp_path / "acme-service"
    project.mkdir()
    (project / "pyproject.toml").write_text(
        '[project]\nname = "acme-service"\nversion = "9.9.9"\n'
        'dependencies = ["click", "rich"]\n',
        encoding="utf-8",
    )
    # config-check opens .beadloom/beadloom.db; ensure the dir exists (a real
    # repo would have run `beadloom init`).
    (project / ".beadloom").mkdir(parents=True, exist_ok=True)
    scaffold(project)
    return project


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


class TestConfigCheckAgenticFlow:
    def test_edited_flow_file_reports_drift(self, tmp_path: Path) -> None:
        project = _scaffolded_project(tmp_path)
        (project / ".claude" / "agents" / "dev.md").write_text(
            "HAND EDITED\n", encoding="utf-8"
        )

        result = CliRunner().invoke(
            main, ["config-check", "--project", str(project)]
        )
        assert result.exit_code == 1
        assert ".claude/agents/dev.md" in result.output

    def test_fix_restores_drifted_flow_file(self, tmp_path: Path) -> None:
        project = _scaffolded_project(tmp_path)
        agent = project / ".claude" / "agents" / "dev.md"
        original = agent.read_text(encoding="utf-8")
        agent.write_text("HAND EDITED\n", encoding="utf-8")

        result = CliRunner().invoke(
            main, ["config-check", "--fix", "--project", str(project)]
        )
        assert result.exit_code == 0
        # --fix restores the flow file BYTE-IDENTICAL to the shipped template.
        assert agent.read_text(encoding="utf-8") == original

        recheck = CliRunner().invoke(
            main, ["config-check", "--project", str(project)]
        )
        assert recheck.exit_code == 0

    def test_unscaffolded_repo_not_flagged_for_flow(self, tmp_path: Path) -> None:
        """A repo that never adopted the flow (only a stray partial file) is not
        flagged for flow drift via the CLI."""
        (tmp_path / ".beadloom").mkdir(parents=True, exist_ok=True)
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "dev.md").write_text("my own notes\n", encoding="utf-8")
        _write_rules_yml(tmp_path, domains=["graph"])
        generate_agents_md(tmp_path)

        result = CliRunner().invoke(
            main, ["config-check", "--project", str(tmp_path)]
        )
        assert result.exit_code == 0, result.output
        assert ".claude/agents/" not in result.output

    def test_claude_md_region_drift_still_detected_when_scaffolded(
        self, tmp_path: Path
    ) -> None:
        """On a scaffolded repo, drift in the CLAUDE.md auto-region is still
        reported (the flow files matching does not mask CLAUDE.md drift)."""
        project = _scaffolded_project(tmp_path)
        claude_md = project / ".claude" / "CLAUDE.md"
        text = claude_md.read_text(encoding="utf-8")
        # Corrupt the version inside the auto-managed project-info region.
        start = text.index("<!-- beadloom:auto-start project-info -->")
        end = text.index("<!-- beadloom:auto-end -->")
        corrupted = (
            text[:start]
            + "<!-- beadloom:auto-start project-info -->\n"
            + "- **Current version:** 0.0.0-STALE\n"
            + text[end:]
        )
        claude_md.write_text(corrupted, encoding="utf-8")

        result = CliRunner().invoke(
            main, ["config-check", "--project", str(project)]
        )
        assert result.exit_code == 1
        assert ".claude/CLAUDE.md" in result.output
