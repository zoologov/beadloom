"""Tests for the ``beadloom config-check`` CLI command (BDL-039 F3 BEAD-03).

Exits 1 on drift, 0 clean; ``--fix`` regenerates via the same refresh
path and re-checks.
"""

from __future__ import annotations

import hashlib
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

    def test_fix_reports_a_hand_edit_and_does_not_delete_it(
        self, tmp_path: Path
    ) -> None:
        """BDL-061 S3: ``--fix`` reports a hand edit and leaves it in place.

        It used to restore the file byte-identical, deleting the edit with no
        diff and no confirmation (BDL-UX #139, #152). The finding is a ``warn``,
        so the exit code stays 0 — an adopter's green project does not go red on
        upgrade — and the message names where the edit belongs.
        """
        project = _scaffolded_project(tmp_path)
        agent = project / ".claude" / "agents" / "dev.md"
        agent.write_text("HAND EDITED\n", encoding="utf-8")

        result = CliRunner().invoke(
            main, ["config-check", "--fix", "--project", str(project)]
        )
        # Still reported (exit 1) — the guard did not get weaker. What changed
        # is that the edit is still there afterwards, and the message says where
        # it belongs instead of offering to delete it.
        assert result.exit_code == 1
        assert agent.read_text(encoding="utf-8") == "HAND EDITED\n"
        assert ".beadloom/flow/" in result.output

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


class TestConfigCheckFlowYml:
    """BDL-052 S3: config-check covers .beadloom/flow.yml + composed adapters."""

    def _write_flow(self, project: Path, body: str) -> None:
        (project / ".beadloom").mkdir(parents=True, exist_ok=True)
        (project / ".beadloom" / "flow.yml").write_text(body, encoding="utf-8")

    def test_bad_flow_yml_flagged(self, tmp_path: Path) -> None:
        project = _scaffolded_project(tmp_path)
        self._write_flow(
            project, "tools: [emacs]\narchitecture: [ddd]\nstack: [python]\n"
        )
        result = CliRunner().invoke(
            main, ["config-check", "--project", str(project)]
        )
        assert result.exit_code == 1
        assert "flow.yml" in result.output

    def test_composed_adapter_drift_flagged_with_flow(self, tmp_path: Path) -> None:
        project = _scaffolded_project(tmp_path)
        self._write_flow(
            project, "tools: [claude]\narchitecture: [ddd]\nstack: [python]\n"
        )
        # Recompose so the adapter matches the flow, then hand-edit it.
        CliRunner().invoke(
            main, ["config-check", "--fix", "--project", str(project)]
        )
        (project / ".claude" / "agents" / "dev.md").write_text(
            "HAND EDITED\n", encoding="utf-8"
        )
        result = CliRunner().invoke(
            main, ["config-check", "--project", str(project)]
        )
        assert result.exit_code == 1
        assert ".claude/agents/dev.md" in result.output

    def test_fix_recomposes_adapters_for_flow(self, tmp_path: Path) -> None:
        project = _scaffolded_project(tmp_path)
        self._write_flow(
            project, "tools: [claude, cursor]\narchitecture: [fsd]\nstack: [vuejs]\n"
        )
        result = CliRunner().invoke(
            main, ["config-check", "--fix", "--project", str(project)]
        )
        assert result.exit_code == 0, result.output
        # The cursor set + FSD/vuejs composition were written.
        cursor_dev = project / ".cursor" / "agents" / "dev.md"
        assert cursor_dev.is_file()
        assert "Feature-Sliced Design" in cursor_dev.read_text(encoding="utf-8")


def _write_flow_yml(project: Path, body: str) -> None:
    (project / ".beadloom").mkdir(parents=True, exist_ok=True)
    (project / ".beadloom" / "flow.yml").write_text(body, encoding="utf-8")


def _agent_config_digests(project: Path) -> dict[str, str]:
    """SHA-256 of every agent-config artifact on disk, project-relative.

    Enumerated by WALKING the tree rather than by asking the production code
    which paths it considers its surface: a report is not evidence, and a
    surface list that forgot a path would otherwise excuse itself.
    ``.beadloom/flow-manifest.json`` is out of frame on purpose — it is
    Beadloom's own record of its writes, not authored content, and naming it in
    every ``--fix`` run would be noise. Everything else under ``.claude/`` and
    ``.cursor/``, plus ``AGENTS.md`` and the IDE pointer files, is in frame.
    """
    roots = [project / ".claude", project / ".cursor"]
    singles = [
        project / ".beadloom" / "AGENTS.md",
        project / ".cursorrules",
        project / ".windsurfrules",
        project / ".clinerules",
    ]
    files: list[Path] = [p for p in singles if p.is_file()]
    for root in roots:
        if root.is_dir():
            files.extend(p for p in root.rglob("*") if p.is_file())
    return {
        str(p.relative_to(project)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in files
    }


class TestFixNeverDestroysWhatBeadloomDidNotWrite:
    """BDL-061 `.59` / BDL-UX #186 — ``--fix`` honours the sentence above it.

    ``config-check`` says of a hand-edited role adapter *"It will NOT be
    rewritten"* and then closes by offering ``config-check --fix``. Running it
    restored the composed body byte-for-byte, deleting the edit, and reported
    *"Agent-config in sync — no blocking drift"* at exit 0 — a destructive act
    reporting success, which is the same class as a check that reports clean
    without checking (BDL-UX #172/#174/#175) and worse, because those only
    misinformed.
    """

    def test_a_hand_edited_adapter_survives_fix_when_a_flow_yml_exists(
        self, tmp_path: Path
    ) -> None:
        """The coordinator's measurement, as a test: sha in == sha out."""
        project = _scaffolded_project(tmp_path)
        _write_flow_yml(
            project, "tools: [claude]\narchitecture: [ddd]\nstack: [python]\n"
        )
        CliRunner().invoke(main, ["config-check", "--fix", "--project", str(project)])
        agent = project / ".claude" / "agents" / "dev.md"
        edited = agent.read_text(encoding="utf-8") + (
            "\n## Our standing engineering practice\n\nNever merge on a red gate.\n"
        )
        agent.write_text(edited, encoding="utf-8")
        before = hashlib.sha256(agent.read_bytes()).hexdigest()

        result = CliRunner().invoke(
            main, ["config-check", "--fix", "--project", str(project)]
        )

        assert hashlib.sha256(agent.read_bytes()).hexdigest() == before
        assert agent.read_text(encoding="utf-8") == edited
        assert ".claude/agents/dev.md" in result.output

    def test_a_run_that_declined_does_not_report_no_blocking_drift(
        self, tmp_path: Path
    ) -> None:
        """The other half: the verdict may not read clean over a standing finding."""
        project = _scaffolded_project(tmp_path)
        _write_flow_yml(
            project, "tools: [claude]\narchitecture: [ddd]\nstack: [python]\n"
        )
        CliRunner().invoke(main, ["config-check", "--fix", "--project", str(project)])
        agent = project / ".claude" / "agents" / "dev.md"
        agent.write_text(
            agent.read_text(encoding="utf-8") + "\n## Ours\n", encoding="utf-8"
        )

        result = CliRunner().invoke(
            main, ["config-check", "--fix", "--project", str(project)]
        )

        assert result.exit_code == 1, result.output
        assert "no blocking drift" not in result.output
        assert ".claude/agents/dev.md" in result.output
        assert "declined" in result.output.lower()

    def test_the_closing_advice_does_not_offer_fix_for_a_finding_it_will_decline(
        self, tmp_path: Path
    ) -> None:
        """BDL-UX #186's second expectation: doing what the last line says must
        not undo what the line above it promised."""
        project = _scaffolded_project(tmp_path)
        _write_flow_yml(
            project, "tools: [claude]\narchitecture: [ddd]\nstack: [python]\n"
        )
        CliRunner().invoke(main, ["config-check", "--fix", "--project", str(project)])
        agent = project / ".claude" / "agents" / "dev.md"
        agent.write_text(
            agent.read_text(encoding="utf-8") + "\n## Ours\n", encoding="utf-8"
        )

        result = CliRunner().invoke(
            main, ["config-check", "--project", str(project)]
        )

        assert result.exit_code == 1
        assert "It will NOT be rewritten" in result.output
        assert "config-check --fix" not in result.output

    def test_every_file_a_fix_run_changed_is_named_in_its_output(
        self, tmp_path: Path
    ) -> None:
        """Say what it did — measured against the disk, not against the writers.

        A ``--fix`` that changes bytes and says nothing is how #186 became
        invisible. This asserts the general property rather than the one path:
        whatever the run touched, the run named.
        """
        project = _scaffolded_project(tmp_path)
        _write_flow_yml(
            project, "tools: [claude, cursor]\narchitecture: [fsd]\nstack: [vuejs]\n"
        )
        _write_rules_yml(project, domains=["graph"])
        before = _agent_config_digests(project)

        result = CliRunner().invoke(
            main, ["config-check", "--fix", "--project", str(project)]
        )

        after = _agent_config_digests(project)
        changed = {
            path
            for path in set(before) | set(after)
            if before.get(path) != after.get(path)
        }
        assert changed, "the probe changed nothing — it would pass vacuously"
        unnamed = sorted(path for path in changed if path not in result.output)
        assert not unnamed, f"changed but never named: {unnamed}\n{result.output}"

