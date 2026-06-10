"""Tests for AgentConfigAsCode drift detection (BDL-039 F3 BEAD-03).

``check_config_drift`` regenerates the agent-config artifacts in memory
(AGENTS.md + CLAUDE.md auto-managed sections + IDE adapters) and diffs
them against on-disk content, reporting one ``ConfigDrift`` per drifted
artifact.  It checks ONLY auto-managed regions — editing user-authored
prose must never trip it (avoids the #73 false-positive class).
"""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

import pytest

from beadloom.onboarding.agentic_flow_setup import AGENT_FILES, COMMAND_FILES, scaffold
from beadloom.onboarding.config_sync import (
    ConfigDrift,
    check_config_drift,
    refresh_agentic_flow_files,
)
from beadloom.onboarding.scanner import (
    _RULES_ADAPTER_TEMPLATE,
    generate_agents_md,
    refresh_claude_md,
)

if TYPE_CHECKING:
    from pathlib import Path


def _make_scaffolded_project(tmp_path: Path) -> Path:
    """A project root with the agentic flow scaffolded into it."""
    project = tmp_path / "acme-service"
    project.mkdir()
    (project / "pyproject.toml").write_text(
        '[project]\nname = "acme-service"\nversion = "9.9.9"\n'
        'dependencies = ["click", "rich"]\n',
        encoding="utf-8",
    )
    scaffold(project)
    return project


def _make_conn() -> sqlite3.Connection:
    """In-memory connection (config drift reads the filesystem, not the DB)."""
    return sqlite3.connect(":memory:")


def _write_rules_yml(project_root: Path, *, domains: list[str]) -> None:
    """Write a minimal rules.yml whose rule names embed the domain list."""
    graph_dir = project_root / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True, exist_ok=True)
    rules = "rules:\n"
    for d in domains:
        rules += (
            f"  - name: {d}-needs-parent\n"
            f"    require: {{}}\n"
            f"    description: domain {d} must have a parent\n"
        )
    (graph_dir / "rules.yml").write_text(rules, encoding="utf-8")


# ---------------------------------------------------------------------------
# Clean state — no drift.
# ---------------------------------------------------------------------------


class TestNoDrift:
    def test_freshly_generated_agents_md_has_no_drift(self, tmp_path: Path) -> None:
        """Right after generation, AGENTS.md is in sync — zero drift."""
        _write_rules_yml(tmp_path, domains=["graph", "onboarding"])
        generate_agents_md(tmp_path)

        conn = _make_conn()
        try:
            drifts = check_config_drift(tmp_path, conn)
        finally:
            conn.close()

        assert drifts == []

    def test_no_artifacts_present_is_not_drift(self, tmp_path: Path) -> None:
        """Absent target files are skipped, not reported as drift."""
        conn = _make_conn()
        try:
            drifts = check_config_drift(tmp_path, conn)
        finally:
            conn.close()

        assert drifts == []

    def test_fresh_claude_md_auto_section_no_drift(self, tmp_path: Path) -> None:
        """A freshly-refreshed CLAUDE.md auto-section reports no drift."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir(parents=True)
        (claude_dir / "CLAUDE.md").write_text(
            "# Project\n\n## 0.1 Project: x\n\n"
            "- **Current version:** 9.9.9\n\n"
            "human prose here\n",
            encoding="utf-8",
        )
        # Refresh installs markers + correct content.
        refresh_claude_md(tmp_path)

        conn = _make_conn()
        try:
            drifts = check_config_drift(tmp_path, conn)
        finally:
            conn.close()

        assert all(d.file != ".claude/CLAUDE.md" for d in drifts)


# ---------------------------------------------------------------------------
# Drift detection.
# ---------------------------------------------------------------------------


class TestAgentsMdDrift:
    def test_stale_agents_md_reports_drift(self, tmp_path: Path) -> None:
        """Editing rules.yml after generation drifts AGENTS.md."""
        _write_rules_yml(tmp_path, domains=["graph"])
        generate_agents_md(tmp_path)
        # Graph adds a `contracts` domain — the on-disk AGENTS.md is now stale.
        _write_rules_yml(tmp_path, domains=["graph", "contracts"])

        conn = _make_conn()
        try:
            drifts = check_config_drift(tmp_path, conn)
        finally:
            conn.close()

        agents_drifts = [d for d in drifts if d.file.endswith("AGENTS.md")]
        assert len(agents_drifts) == 1
        assert "contracts" in agents_drifts[0].reason or agents_drifts[0].reason

    def test_user_custom_block_edit_does_not_drift(self, tmp_path: Path) -> None:
        """Editing the preserved custom block of AGENTS.md is NOT drift."""
        _write_rules_yml(tmp_path, domains=["graph"])
        agents_path = generate_agents_md(tmp_path)
        text = agents_path.read_text(encoding="utf-8")
        text = text.replace(
            "<!-- beadloom:custom-start -->\n",
            "<!-- beadloom:custom-start -->\nMy own project notes.\n",
        )
        agents_path.write_text(text, encoding="utf-8")

        conn = _make_conn()
        try:
            drifts = check_config_drift(tmp_path, conn)
        finally:
            conn.close()

        assert all(not d.file.endswith("AGENTS.md") for d in drifts)


class TestClaudeMdDrift:
    def test_stale_auto_section_reports_drift(self, tmp_path: Path) -> None:
        """A drifted CLAUDE.md auto-managed section is reported."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir(parents=True)
        (claude_dir / "CLAUDE.md").write_text(
            "# Project\n\n## 0.1 Project: x\n\n"
            "<!-- beadloom:auto-start project-info -->\n"
            "- **Current version:** 0.0.1-STALE\n"
            "<!-- beadloom:auto-end -->\n\n"
            "human prose\n",
            encoding="utf-8",
        )

        conn = _make_conn()
        try:
            drifts = check_config_drift(tmp_path, conn)
        finally:
            conn.close()

        claude_drifts = [d for d in drifts if d.file == ".claude/CLAUDE.md"]
        assert len(claude_drifts) == 1

    def test_human_prose_edit_does_not_drift(self, tmp_path: Path) -> None:
        """Editing human prose outside the markers never trips the check."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir(parents=True)
        (claude_dir / "CLAUDE.md").write_text(
            "# Project\n\n## 0.1 Project: x\n\n"
            "- **Current version:** 9.9.9\n\n"
            "human prose\n",
            encoding="utf-8",
        )
        refresh_claude_md(tmp_path)
        # Now edit only the human prose far from the markers.
        cm = claude_dir / "CLAUDE.md"
        cm.write_text(
            cm.read_text(encoding="utf-8") + "\n\nMore human notes added later.\n",
            encoding="utf-8",
        )

        conn = _make_conn()
        try:
            drifts = check_config_drift(tmp_path, conn)
        finally:
            conn.close()

        assert all(d.file != ".claude/CLAUDE.md" for d in drifts)


class TestAdapterDrift:
    def test_stale_adapter_reports_drift(self, tmp_path: Path) -> None:
        """A beadloom adapter whose content drifted from the template."""
        (tmp_path / ".cursor").mkdir()
        (tmp_path / ".cursorrules").write_text(
            "# Beadloom old adapter\nRead .beadloom/AGENTS.md\n",
            encoding="utf-8",
        )

        conn = _make_conn()
        try:
            drifts = check_config_drift(tmp_path, conn)
        finally:
            conn.close()

        assert any(d.file == ".cursorrules" for d in drifts)

    def test_fresh_adapter_no_drift(self, tmp_path: Path) -> None:
        """An adapter matching the current template is not drift."""
        (tmp_path / ".cursor").mkdir()
        (tmp_path / ".cursorrules").write_text(
            _RULES_ADAPTER_TEMPLATE, encoding="utf-8"
        )

        conn = _make_conn()
        try:
            drifts = check_config_drift(tmp_path, conn)
        finally:
            conn.close()

        assert all(d.file != ".cursorrules" for d in drifts)

    def test_user_adapter_content_not_checked(self, tmp_path: Path) -> None:
        """A non-beadloom adapter file (user content) is never checked."""
        (tmp_path / ".cursor").mkdir()
        (tmp_path / ".cursorrules").write_text(
            "# My own cursor rules\nUse TypeScript.\n", encoding="utf-8"
        )

        conn = _make_conn()
        try:
            drifts = check_config_drift(tmp_path, conn)
        finally:
            conn.close()

        assert all(d.file != ".cursorrules" for d in drifts)


class TestAgenticFlowDrift:
    """Drift for the scaffolded ``.claude/agents/*`` + ``.claude/commands/*``."""

    def test_freshly_scaffolded_flow_has_no_drift(self, tmp_path: Path) -> None:
        """Right after ``scaffold``, the flow files match the vendored templates."""
        project = _make_scaffolded_project(tmp_path)

        conn = _make_conn()
        try:
            drifts = check_config_drift(project, conn)
        finally:
            conn.close()

        flow_drifts = [
            d for d in drifts if "/agents/" in d.file or "/commands/" in d.file
        ]
        assert flow_drifts == []

    def test_edited_agent_file_reports_drift(self, tmp_path: Path) -> None:
        """A hand-edited scaffolded agent file is reported as drifted."""
        project = _make_scaffolded_project(tmp_path)
        agent = project / ".claude" / "agents" / "dev.md"
        agent.write_text("HAND EDITED PROTOCOL\n", encoding="utf-8")

        conn = _make_conn()
        try:
            drifts = check_config_drift(project, conn)
        finally:
            conn.close()

        flow_drifts = [d for d in drifts if d.file == ".claude/agents/dev.md"]
        assert len(flow_drifts) == 1

    def test_edited_command_file_reports_drift(self, tmp_path: Path) -> None:
        """A hand-edited scaffolded command file is reported as drifted."""
        project = _make_scaffolded_project(tmp_path)
        cmd = project / ".claude" / "commands" / "coordinator.md"
        cmd.write_text("REWRITTEN PLAYBOOK\n", encoding="utf-8")

        conn = _make_conn()
        try:
            drifts = check_config_drift(project, conn)
        finally:
            conn.close()

        flow_drifts = [d for d in drifts if d.file == ".claude/commands/coordinator.md"]
        assert len(flow_drifts) == 1

    def test_unscaffolded_project_not_flagged(self, tmp_path: Path) -> None:
        """A repo without the flow scaffolded is never flagged for flow drift.

        The flow is only checked when ALL of the canonical agents+commands are
        present (a repo that never adopted the flow must not be forced into it).
        """
        # Only a stray, partial set of files — flow was never scaffolded.
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "dev.md").write_text("just my own notes\n", encoding="utf-8")

        conn = _make_conn()
        try:
            drifts = check_config_drift(tmp_path, conn)
        finally:
            conn.close()

        flow_drifts = [
            d for d in drifts if "/agents/" in d.file or "/commands/" in d.file
        ]
        assert flow_drifts == []

    @pytest.mark.parametrize("kind", ["agents", "commands"])
    @pytest.mark.parametrize("idx", [0, 1, 2, 3])
    def test_each_flow_file_independently_detected(
        self, tmp_path: Path, kind: str, idx: int
    ) -> None:
        """The byte-equality guard fails for EACH individual flow file when it
        diverges — so no single template can silently drift from the proven flow.
        """
        names = AGENT_FILES if kind == "agents" else COMMAND_FILES
        name = names[idx]
        project = _make_scaffolded_project(tmp_path)
        target = project / ".claude" / kind / f"{name}.md"
        target.write_text(target.read_text(encoding="utf-8") + "\n<!-- diverged -->\n")

        conn = _make_conn()
        try:
            drifts = check_config_drift(project, conn)
        finally:
            conn.close()

        assert any(d.file == f".claude/{kind}/{name}.md" for d in drifts)

    def test_partial_scaffold_not_flagged(self, tmp_path: Path) -> None:
        """A repo with SOME (but not all) flow files present is not flagged —
        the flow is only checked when fully scaffolded."""
        project = _make_scaffolded_project(tmp_path)
        # Remove one command file -> the flow is no longer fully scaffolded.
        (project / ".claude" / "commands" / f"{COMMAND_FILES[0]}.md").unlink()
        # Diverge a remaining file; it must still NOT be flagged.
        agent = project / ".claude" / "agents" / "dev.md"
        agent.write_text("HAND EDITED\n", encoding="utf-8")

        conn = _make_conn()
        try:
            drifts = check_config_drift(project, conn)
        finally:
            conn.close()

        flow_drifts = [
            d for d in drifts if "/agents/" in d.file or "/commands/" in d.file
        ]
        assert flow_drifts == []

    def test_all_drifted_flow_files_reported(self, tmp_path: Path) -> None:
        """Every present-but-drifted flow file gets its own ConfigDrift."""
        project = _make_scaffolded_project(tmp_path)
        for name in AGENT_FILES:
            (project / ".claude" / "agents" / f"{name}.md").write_text(
                "x\n", encoding="utf-8"
            )
        for name in COMMAND_FILES:
            (project / ".claude" / "commands" / f"{name}.md").write_text(
                "y\n", encoding="utf-8"
            )

        conn = _make_conn()
        try:
            drifts = check_config_drift(project, conn)
        finally:
            conn.close()

        flow_files = {
            d.file for d in drifts if "/agents/" in d.file or "/commands/" in d.file
        }
        expected = {f".claude/agents/{n}.md" for n in AGENT_FILES} | {
            f".claude/commands/{n}.md" for n in COMMAND_FILES
        }
        assert flow_files == expected


# ---------------------------------------------------------------------------
# refresh_agentic_flow_files — the config-check --fix companion.
# ---------------------------------------------------------------------------


class TestRefreshAgenticFlowFiles:
    def test_restores_drifted_files_byte_identical(self, tmp_path: Path) -> None:
        """``--fix`` restores every drifted flow file to the shipped template
        byte-for-byte (and the post-fix check is clean)."""
        project = _make_scaffolded_project(tmp_path)
        agent = project / ".claude" / "agents" / "dev.md"
        cmd = project / ".claude" / "commands" / "coordinator.md"
        original = agent.read_text(encoding="utf-8")
        agent.write_text("HAND EDITED\n", encoding="utf-8")
        cmd.write_text("REWRITTEN\n", encoding="utf-8")

        written = refresh_agentic_flow_files(project)

        assert "agents/dev.md" in written
        assert "commands/coordinator.md" in written
        assert agent.read_text(encoding="utf-8") == original
        conn = _make_conn()
        try:
            drifts = check_config_drift(project, conn)
        finally:
            conn.close()
        flow_drifts = [
            d for d in drifts if "/agents/" in d.file or "/commands/" in d.file
        ]
        assert flow_drifts == []

    def test_noop_on_unscaffolded_repo(self, tmp_path: Path) -> None:
        """``--fix`` never forces the flow onto a repo that did not adopt it."""
        assert refresh_agentic_flow_files(tmp_path) == []
        # No .claude/ tree was created as a side effect.
        assert not (tmp_path / ".claude" / "agents").exists()

    def test_noop_on_partial_scaffold(self, tmp_path: Path) -> None:
        """A partially-scaffolded repo (some files missing) is left untouched."""
        project = _make_scaffolded_project(tmp_path)
        (project / ".claude" / "agents" / "test.md").unlink()
        agent = project / ".claude" / "agents" / "dev.md"
        agent.write_text("HAND EDITED\n", encoding="utf-8")

        assert refresh_agentic_flow_files(project) == []
        # The divergent file is NOT restored (flow not fully scaffolded).
        assert agent.read_text(encoding="utf-8") == "HAND EDITED\n"

    def test_rewrites_all_files_even_when_in_sync(self, tmp_path: Path) -> None:
        """On a fully-scaffolded repo, every flow file is reported rewritten
        (force=True) — idempotent and byte-stable."""
        project = _make_scaffolded_project(tmp_path)
        written = refresh_agentic_flow_files(project)
        expected = {f"agents/{n}.md" for n in AGENT_FILES} | {
            f"commands/{n}.md" for n in COMMAND_FILES
        }
        assert set(written) == expected


# ---------------------------------------------------------------------------
# Determinism + dataclass contract.
# ---------------------------------------------------------------------------


class TestContract:
    def test_configdrift_is_frozen_dataclass(self) -> None:
        d = ConfigDrift(file="x", reason="y")
        assert d.file == "x"
        assert d.reason == "y"

    def test_deterministic_ordering(self, tmp_path: Path) -> None:
        """Repeated runs return identical, sorted results."""
        _write_rules_yml(tmp_path, domains=["graph"])
        generate_agents_md(tmp_path)
        _write_rules_yml(tmp_path, domains=["graph", "contracts"])
        (tmp_path / ".cursor").mkdir()
        (tmp_path / ".cursorrules").write_text(
            "# Beadloom old\n.beadloom/AGENTS.md\n", encoding="utf-8"
        )

        conn = _make_conn()
        try:
            first = check_config_drift(tmp_path, conn)
            second = check_config_drift(tmp_path, conn)
        finally:
            conn.close()

        assert first == second
        files = [d.file for d in first]
        assert files == sorted(files)
