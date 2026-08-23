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
    apply_config_fixes,
    check_config_drift,
    refresh_agentic_flow_files,
    refresh_composed_adapters,
)
from beadloom.onboarding.role_composer import ROLE_NAMES
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
        # Both sides of the round-trip state the same codec. The read already did;
        # the write inherited the image's locale, so under a non-UTF-8 image this
        # line raised on a role file containing an em dash (BDL-061.42).
        target.write_text(
            target.read_text(encoding="utf-8") + "\n<!-- diverged -->\n", encoding="utf-8"
        )

        conn = _make_conn()
        try:
            drifts = check_config_drift(project, conn)
        finally:
            conn.close()

        assert any(d.file == f".claude/{kind}/{name}.md" for d in drifts)

    def test_partial_scaffold_checks_what_is_there_and_names_what_is_not(
        self, tmp_path: Path
    ) -> None:
        """The inverse of what this test asserted before BDL-061 `.57`.

        It used to pin "a repo with SOME flow files present is not flagged",
        which measured out as: deleting ONE file switched the checks off for
        every other one, and the deletion itself was reported by nothing. The
        gate is not satisfied by having less to check (BDL-UX #174), so the
        statement is now the opposite one — the remaining files are still
        checked, and the absent file is its own finding.
        """
        project = _make_scaffolded_project(tmp_path)
        gone = f".claude/commands/{COMMAND_FILES[0]}.md"
        (project / gone).unlink()
        agent = project / ".claude" / "agents" / "dev.md"
        agent.write_text("HAND EDITED\n", encoding="utf-8")

        conn = _make_conn()
        try:
            drifts = check_config_drift(project, conn)
        finally:
            conn.close()

        flow_drifts = {
            d.file for d in drifts if "/agents/" in d.file or "/commands/" in d.file
        }
        assert ".claude/agents/dev.md" in flow_drifts
        assert gone in flow_drifts

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
    def test_hand_edited_files_are_reported_never_rewritten(
        self, tmp_path: Path
    ) -> None:
        """BDL-061 S3 contract change: ``--fix`` no longer eats a hand edit.

        It used to restore every divergent flow file byte-for-byte, which is the
        failure BDL-UX #139/#152 were filed for — the only copy of a team's
        standing engineering practice was deleted with no diff and no
        confirmation. A hand-edited file is now left alone and reported as a
        ``warn`` naming the project-layer path the edit belongs in.
        """
        project = _make_scaffolded_project(tmp_path)
        agent = project / ".claude" / "agents" / "dev.md"
        cmd = project / ".claude" / "commands" / "coordinator.md"
        agent.write_text("HAND EDITED\n", encoding="utf-8")
        cmd.write_text("REWRITTEN\n", encoding="utf-8")

        written = refresh_agentic_flow_files(project)

        assert "agents/dev.md" not in written
        assert "commands/coordinator.md" not in written
        assert agent.read_text(encoding="utf-8") == "HAND EDITED\n"
        assert cmd.read_text(encoding="utf-8") == "REWRITTEN\n"

        conn = _make_conn()
        try:
            drifts = check_config_drift(project, conn)
        finally:
            conn.close()
        reported = {
            d.file: d for d in drifts if "/agents/" in d.file or "/commands/" in d.file
        }
        command_drift = reported[".claude/commands/coordinator.md"]
        assert command_drift.severity == "error"
        assert ".beadloom/flow/commands/coordinator.md" in (
            command_drift.remediation or ""
        )

    def test_noop_on_unscaffolded_repo(self, tmp_path: Path) -> None:
        """``--fix`` never forces the flow onto a repo that did not adopt it."""
        assert refresh_agentic_flow_files(tmp_path) == []
        # No .claude/ tree was created as a side effect.
        assert not (tmp_path / ".claude" / "agents").exists()

    def test_a_partial_scaffold_is_restored_without_eating_the_hand_edit(
        self, tmp_path: Path
    ) -> None:
        """``--fix`` on a partial scaffold: recreate the deleted file, keep the edit.

        Before BDL-061 `.57` one deletion made ``--fix`` a no-op for the whole
        repo. It now acts on what it can, and the one thing it still must not do
        is rewrite somebody's only copy of an intent (BDL-UX #139, #151).
        """
        project = _make_scaffolded_project(tmp_path)
        deleted = project / ".claude" / "agents" / "test.md"
        deleted.unlink()
        agent = project / ".claude" / "agents" / "dev.md"
        agent.write_text("HAND EDITED\n", encoding="utf-8")

        # Asserted through `--fix`'s own entry point rather than one of its two
        # writers. Since a scaffold records its selection in `flow.yml`
        # (BDL-UX #187), `.claude/agents/*` belongs to the COMPOSED adapter
        # writer and the scaffold path deliberately leaves it alone; measuring
        # one writer would report a capability the command still has.
        report = apply_config_fixes(project)

        assert deleted.is_file()
        assert ".claude/agents/test.md" in (*report.created, *report.rewritten)
        assert agent.read_text(encoding="utf-8") == "HAND EDITED\n"
        assert [d.file for d in report.declined] == [".claude/agents/dev.md"]

    def test_rewrites_every_file_it_owns_even_when_in_sync(self, tmp_path: Path) -> None:
        """On a fully-scaffolded repo, every flow file this writer OWNS is
        reported rewritten — idempotent and byte-stable. CLAUDE.md is one of
        them: since BDL-061 S3 its body is composed, not a snapshot of
        Beadloom's own live file. `.claude/agents/*` is not: a repo whose
        scaffold recorded a `flow.yml` (BDL-UX #187) has its role files written
        by the composed-adapter writer, and having both write them would be two
        owners for one file."""
        project = _make_scaffolded_project(tmp_path)
        written = refresh_agentic_flow_files(project)
        expected = {f"commands/{n}.md" for n in COMMAND_FILES} | {"CLAUDE.md"}
        assert set(written) == expected
        # The role files still have an owner — asserted, not assumed.
        assert set(refresh_composed_adapters(project).rewritten) == {
            f".claude/agents/{n}.md" for n in ROLE_NAMES
        }


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


# ---------------------------------------------------------------------------
# refresh_composed_adapters — what --fix rewrites, and what it refuses to.
# ---------------------------------------------------------------------------


class TestRefreshComposedAdapters:
    """BDL-061 `.59` / BDL-UX #186 — ``--fix`` may only rewrite what it wrote.

    The check tells the reader a hand-edited adapter *"will NOT be rewritten"*.
    Whether that sentence is true is decided here: the composer's ``--fix``
    companion regenerated every configured adapter unconditionally, so the
    promise was false for exactly the file it was printed about.
    """

    def _adopt_flow(self, project: Path, body: str) -> None:
        (project / ".beadloom").mkdir(parents=True, exist_ok=True)
        (project / ".beadloom" / "flow.yml").write_text(body, encoding="utf-8")

    def test_a_hand_edit_is_declined_by_name_while_the_rest_recompose(
        self, tmp_path: Path
    ) -> None:
        from beadloom.onboarding.config_sync import refresh_composed_adapters

        project = _make_scaffolded_project(tmp_path)
        self._adopt_flow(
            project, "tools: [claude]\narchitecture: [ddd]\nstack: [python]\n"
        )
        refresh_composed_adapters(project)  # baseline: recorded by the manifest
        edited = project / ".claude" / "agents" / "dev.md"
        body = edited.read_text(encoding="utf-8") + "\n## Ours\n\nNo red merges.\n"
        edited.write_text(body, encoding="utf-8")
        stale = project / ".claude" / "agents" / "test.md"
        composed_test = stale.read_text(encoding="utf-8")
        stale.unlink()

        report = refresh_composed_adapters(project)

        # The edit is still there, and the run says which file it left alone.
        assert edited.read_text(encoding="utf-8") == body
        assert [d.file for d in report.declined] == [".claude/agents/dev.md"]
        assert "hand-edited" in report.declined[0].reason
        assert ".beadloom/flow/roles/dev.md" in (report.declined[0].remediation or "")
        # Declining one file does not stop it fixing the others.
        assert stale.read_text(encoding="utf-8") == composed_test
        assert ".claude/agents/test.md" in report.rewritten
        assert ".claude/agents/dev.md" not in report.rewritten

    def test_the_plain_vendored_scaffold_is_not_a_hand_edit(
        self, tmp_path: Path
    ) -> None:
        """Adopting a flow.yml on an already-scaffolded repo must still be fixable.

        The vendored role files are bytes Beadloom itself shipped and wrote, but
        nothing records them, so under a naive ownership test they read as a
        hand edit — and ``--fix`` would then refuse to recompose them for ever.
        Refusing to touch a file we wrote is the mirror of the defect, not the
        cure: unowned is not the same as somebody's only copy.
        """
        from beadloom.onboarding.config_sync import refresh_composed_adapters

        project = _make_scaffolded_project(tmp_path)
        self._adopt_flow(
            project, "tools: [claude, cursor]\narchitecture: [fsd]\nstack: [vuejs]\n"
        )

        report = refresh_composed_adapters(project)

        assert report.declined == ()
        assert ".claude/agents/dev.md" in report.rewritten
        assert "Feature-Sliced Design" in (
            project / ".claude" / "agents" / "dev.md"
        ).read_text(encoding="utf-8")

    def test_an_unverified_adapter_is_declined_too(self, tmp_path: Path) -> None:
        """The rule is stated over provenance, not over the word ``hand_edited``.

        ``unverified`` — the body matches no composition Beadloom could have
        produced, and nothing accounts for it — is the worst case available,
        because it is a ``warn``: overwriting one would have deleted the body
        and then let the command print "no blocking drift" at exit 0, with no
        red anywhere in the output to catch it. Its own remediation says
        *review it, then `setup-agentic-flow --force`* — a deliberate act by
        somebody who has looked. ``--fix`` has not looked.

        Written AFTER the implementation, unlike the rest of this class; its
        value rests on the sabotage that reddens it (declining only
        ``hand_edited``), not on its having failed first.
        """
        from beadloom.onboarding.config_sync import refresh_composed_adapters

        project = tmp_path / "acme-service"
        (project / ".beadloom").mkdir(parents=True)
        (project / ".beadloom" / "flow.yml").write_text(
            "tools: [claude]\narchitecture: [ddd]\nstack: [python]\n", encoding="utf-8"
        )
        agents = project / ".claude" / "agents"
        agents.mkdir(parents=True)
        # A role protocol from somewhere else: no manifest, no provenance.
        body = "# Our own dev protocol\n\nPair on migrations.\n"
        (agents / "dev.md").write_text(body, encoding="utf-8")

        report = refresh_composed_adapters(project)

        assert (agents / "dev.md").read_text(encoding="utf-8") == body
        assert [d.file for d in report.declined] == [".claude/agents/dev.md"]
        assert "unverified" in report.declined[0].reason
        assert ".claude/agents/dev.md" not in report.rewritten
