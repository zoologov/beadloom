"""BDL-061 S3 — compose(core, architecture, stack, project) for the whole flow.

Three artifact kinds are composed from four layers: the shipped CORE, one
architecture overlay, the stack overlays, and the **project** layer that lives
in ``.beadloom/flow/{roles,commands,claude}``. Two properties have to hold at
the same time, and until this slice they could not:

* a project can extend any flow artifact without turning ``beadloom ci`` red
  (BDL-UX #139, #152);
* drift in the shipped CORE is still detected while that extension exists —
  including the case measured in #177, where ``config-check`` printed
  ``agent-config in sync`` over a ``CLAUDE.md`` that had been gutted.
"""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

import pytest

from beadloom.onboarding.agentic_flow_setup import scaffold
from beadloom.onboarding.config_sync import check_config_drift

if TYPE_CHECKING:
    from pathlib import Path


def _make_project(tmp_path: Path, *, flow_yml: str | None = None) -> Path:
    """A scaffolded project root, optionally carrying a ``.beadloom/flow.yml``."""
    project = tmp_path / "acme-service"
    (project / ".beadloom").mkdir(parents=True)
    (project / "pyproject.toml").write_text(
        '[project]\nname = "acme-service"\nversion = "9.9.9"\n', encoding="utf-8"
    )
    if flow_yml is not None:
        (project / ".beadloom" / "flow.yml").write_text(flow_yml, encoding="utf-8")
    scaffold(project, include_agents=False)
    return project


def _conn() -> sqlite3.Connection:
    """In-memory connection — config drift reads the filesystem, not the DB."""
    return sqlite3.connect(":memory:")


def _drift_files(project: Path) -> list[str]:
    return [d.file for d in check_config_drift(project, _conn())]


class TestClaudeMdBodyIsChecked:
    """#177's open question, answered: the CLAUDE.md BODY was checked by nothing.

    ``_claude_md_drift`` only ever diffed the marker-bounded auto-regions, so
    every one of these mutations left ``check_config_drift`` returning ``[]``
    and the Gate printing ``config-check PASS: agent-config in sync``.
    """

    def test_gutted_claude_md_is_reported(self, tmp_path: Path) -> None:
        project = _make_project(tmp_path)
        (project / ".claude" / "CLAUDE.md").write_text("# gone\n", encoding="utf-8")
        assert ".claude/CLAUDE.md" in _drift_files(project)

    def test_deleting_a_core_section_is_reported(self, tmp_path: Path) -> None:
        project = _make_project(tmp_path)
        claude_md = project / ".claude" / "CLAUDE.md"
        text = claude_md.read_text(encoding="utf-8")
        start = text.find("\n## 7.")
        end = text.find("\n## 8.")
        assert start != -1, "fixture assumption: the core has a section 7"
        claude_md.write_text(text[:start] + text[end:], encoding="utf-8")
        assert ".claude/CLAUDE.md" in _drift_files(project)

    def test_untouched_scaffold_is_clean(self, tmp_path: Path) -> None:
        """The new check must not turn a freshly scaffolded project red."""
        project = _make_project(tmp_path)
        assert ".claude/CLAUDE.md" not in _drift_files(project)


class TestProjectOverlayComposes:
    """The project layer in ``.beadloom/flow/`` is part of the composition."""

    _FLOW = "tools: [claude]\narchitecture: [ddd]\nstack: [python]\n"

    def _overlay(self, project: Path, kind: str, name: str, text: str) -> None:
        target = project / ".beadloom" / "flow" / kind
        target.mkdir(parents=True, exist_ok=True)
        (target / f"{name}.md").write_text(text, encoding="utf-8")

    def test_claude_overlay_is_appended_and_not_drift(self, tmp_path: Path) -> None:
        project = _make_project(tmp_path, flow_yml=self._FLOW)
        self._overlay(project, "claude", "CLAUDE", "\n## Acme house rules\n\nNo YOLO.\n")
        scaffold(project, include_agents=False)
        body = (project / ".claude" / "CLAUDE.md").read_text(encoding="utf-8")
        assert "Acme house rules" in body
        assert ".claude/CLAUDE.md" not in _drift_files(project)

    def test_role_overlay_is_appended_and_not_drift(self, tmp_path: Path) -> None:
        from beadloom.onboarding.config_sync import refresh_composed_adapters

        project = _make_project(tmp_path, flow_yml=self._FLOW)
        self._overlay(project, "roles", "dev", "\n## Acme: mutation testing\n")
        refresh_composed_adapters(project)
        body = (project / ".claude" / "agents" / "dev.md").read_text(encoding="utf-8")
        assert "Acme: mutation testing" in body
        assert ".claude/agents/dev.md" not in _drift_files(project)

    def test_command_overlay_is_appended_and_not_drift(self, tmp_path: Path) -> None:
        project = _make_project(tmp_path, flow_yml=self._FLOW)
        self._overlay(project, "commands", "coordinator", "\n## Acme: wave policy\n")
        scaffold(project, include_agents=False)
        body = (project / ".claude" / "commands" / "coordinator.md").read_text(
            encoding="utf-8"
        )
        assert "Acme: wave policy" in body
        assert ".claude/commands/coordinator.md" not in _drift_files(project)

    def test_core_drift_still_caught_while_an_overlay_exists(
        self, tmp_path: Path
    ) -> None:
        """The property the slice turns on: extension does NOT blind the check."""
        project = _make_project(tmp_path, flow_yml=self._FLOW)
        self._overlay(project, "claude", "CLAUDE", "\n## Acme house rules\n")
        scaffold(project, include_agents=False)
        assert ".claude/CLAUDE.md" not in _drift_files(project)
        claude_md = project / ".claude" / "CLAUDE.md"
        text = claude_md.read_text(encoding="utf-8")
        claude_md.write_text(
            text.replace("## 7. Anti-patterns (NEVER)", "## 7. Suggestions (maybe)"),
            encoding="utf-8",
        )
        assert ".claude/CLAUDE.md" in _drift_files(project)

    def test_overlay_survives_an_upgrade(self, tmp_path: Path) -> None:
        """A shipped-core change recomposes without discarding the project layer."""
        project = _make_project(tmp_path, flow_yml=self._FLOW)
        self._overlay(project, "claude", "CLAUDE", "\n## Acme house rules\n")
        scaffold(project, include_agents=False)
        scaffold(project, force=True, include_agents=False)
        body = (project / ".claude" / "CLAUDE.md").read_text(encoding="utf-8")
        assert "Acme house rules" in body


class TestComposeApi:
    """``compose`` is one function over the four layers, for all three kinds."""

    def test_compose_reports_the_layers_it_used(self, tmp_path: Path) -> None:
        from beadloom.onboarding.composer import compose
        from beadloom.onboarding.flow_config import FlowConfig

        project = _make_project(tmp_path)
        (project / ".beadloom" / "flow" / "roles").mkdir(parents=True)
        (project / ".beadloom" / "flow" / "roles" / "dev.md").write_text(
            "\n## Acme\n", encoding="utf-8"
        )
        config = FlowConfig(
            tools=("claude",), architecture="ddd", stack=("python",)
        )
        result = compose("roles", "dev", config=config, project_root=project)
        layers = [f.layer for f in result.fragments]
        # ``core:_writing`` is the shared writing standard, ``core:_rooms`` the
        # shared room statement (BDL-061 S4, BDL-068 S3.2) and ``core:_landing``
        # what the merge slot grants (BDL-068 S5, BDL-UX #194/#237), each
        # composed into every role straight after its own core. All three are
        # LAYERS and not roles: one text, one file, every consumer.
        assert layers == [
            "core",
            "core:_writing",
            "core:_rooms",
            "core:_landing",
            "architecture:ddd",
            "stack:python",
            "project",
        ]
        assert result.text.endswith("\n## Acme\n")

    def test_unknown_kind_is_loud(self, tmp_path: Path) -> None:
        from beadloom.onboarding.composer import compose
        from beadloom.onboarding.flow_config import FlowConfig, FlowConfigError

        config = FlowConfig(tools=("claude",), architecture="ddd", stack=("python",))
        with pytest.raises(FlowConfigError, match="unknown artifact kind"):
            compose("wat", "dev", config=config)


class TestSuppressionIsDeclaredAndReported:
    """Overlays are append-only; standing down a core rule is a declaration."""

    def _flow(self, suppress: str) -> str:
        return (
            "tools: [claude]\narchitecture: [ddd]\nstack: [python]\n"
            f"overlays:\n  suppress:\n{suppress}"
        )

    def test_missing_reason_is_a_config_error(self, tmp_path: Path) -> None:
        from beadloom.onboarding.flow_config import FlowConfigError, build_flow_config

        with pytest.raises(FlowConfigError, match="reason"):
            build_flow_config(
                {
                    "tools": ["claude"],
                    "architecture": ["ddd"],
                    "stack": ["python"],
                    "overlays": {"suppress": [{"rule": "X", "until": "2030-01-01"}]},
                }
            )

    def test_missing_exit_condition_is_a_config_error(self, tmp_path: Path) -> None:
        from beadloom.onboarding.flow_config import FlowConfigError, build_flow_config

        with pytest.raises(FlowConfigError, match="until"):
            build_flow_config(
                {
                    "tools": ["claude"],
                    "architecture": ["ddd"],
                    "stack": ["python"],
                    "overlays": {"suppress": [{"rule": "X", "reason": "because"}]},
                }
            )

    def test_suppression_is_appended_and_the_core_text_remains(
        self, tmp_path: Path
    ) -> None:
        project = _make_project(
            tmp_path,
            flow_yml=self._flow(
                '    - rule: "Anti-patterns / Shell"\n'
                '      reason: "the team runs on Windows"\n'
                '      until: "a windows stack overlay ships"\n'
            ),
        )
        scaffold(project, include_agents=False)
        body = (project / ".claude" / "CLAUDE.md").read_text(encoding="utf-8")
        assert "Project rule suppressions" in body
        assert "the team runs on Windows" in body
        assert "a windows stack overlay ships" in body
        # Append-only: the core is unchanged above the notice.
        assert "## 0. CRITICAL RULES" in body

    def test_expiry_is_computed_but_never_composed(self) -> None:
        """BDL-061 `.57`: the verdict about today is a finding, not a byte.

        ``describe()`` used to append ``EXPIRED``, which made the composition a
        function of the clock — the property ``composer``'s own docstring denies
        and the whole licence for ``config-check`` to compare against a
        composition. Expiry is still computed; it is reported by ``config-check``
        instead of being written into every artifact.
        """
        from beadloom.onboarding.flow_suppression import FlowSuppression

        s = FlowSuppression(rule="X", reason="y", until="2020-01-01")
        assert s.expired() is True
        assert s.describe() == "X: y (until 2020-01-01)"

    def test_event_shaped_exit_condition_never_expires(self) -> None:
        from beadloom.onboarding.flow_suppression import FlowSuppression

        s = FlowSuppression(rule="X", reason="y", until="a windows overlay ships")
        assert s.expired() is False


class TestLanguageFromFlowYml:
    """#136 — a team writing in Russian is held to the standard in Russian."""

    def test_language_defaults_to_en(self, tmp_path: Path) -> None:
        from beadloom.onboarding.flow_config import build_flow_config

        config = build_flow_config(
            {"tools": ["claude"], "architecture": ["ddd"], "stack": ["python"]}
        )
        assert config.language == "en"

    def test_language_is_read_from_flow_yml(self, tmp_path: Path) -> None:
        from beadloom.onboarding.flow_config import load_flow_config

        (tmp_path / ".beadloom").mkdir()
        (tmp_path / ".beadloom" / "flow.yml").write_text(
            "tools: [claude]\narchitecture: [ddd]\nstack: [python]\nlanguage: ru\n",
            encoding="utf-8",
        )
        assert load_flow_config(tmp_path).language == "ru"

    def test_a_bad_language_tag_is_loud(self) -> None:
        from beadloom.onboarding.flow_config import FlowConfigError, build_flow_config

        with pytest.raises(FlowConfigError, match="language"):
            build_flow_config(
                {
                    "tools": ["claude"],
                    "architecture": ["ddd"],
                    "stack": ["python"],
                    "language": "Русский",
                }
            )

    def test_a_missing_localisation_is_reported_not_silent(
        self, tmp_path: Path
    ) -> None:
        """The honest skip: no `ru` fragment ships, so the composition SAYS so."""
        from beadloom.onboarding.composer import compose
        from beadloom.onboarding.flow_config import FlowConfig

        config = FlowConfig(
            tools=("claude",), architecture="ddd", stack=("python",), language="ru"
        )
        result = compose("roles", "dev", config=config)
        assert result.notes, "a fallback to English must never be silent"
        assert any("'ru'" in note for note in result.notes)

    def test_a_localised_project_fragment_is_used(self, tmp_path: Path) -> None:
        from beadloom.onboarding.composer import compose
        from beadloom.onboarding.flow_config import FlowConfig

        project = _make_project(tmp_path)
        overlay = project / ".beadloom" / "flow" / "roles"
        overlay.mkdir(parents=True)
        (overlay / "dev.md").write_text("\n## Стандарт письма\n", encoding="utf-8")
        config = FlowConfig(
            tools=("claude",), architecture="ddd", stack=("python",), language="ru"
        )
        result = compose("roles", "dev", config=config, project_root=project)
        assert "Стандарт письма" in result.text


class TestCrossMajorReinitReportsOrphans:
    """#137 — a re-init on an older layout names what it no longer owns."""

    def test_role_files_left_in_commands_are_reported(self, tmp_path: Path) -> None:
        project = _make_project(tmp_path)
        legacy = project / ".claude" / "commands" / "dev.md"
        legacy.write_text("old layout role file\n", encoding="utf-8")
        (project / ".claude" / "commands" / "epic-init.md").write_text(
            "superseded\n", encoding="utf-8"
        )
        result = scaffold(project, include_agents=False)
        joined = "\n".join(result.orphans)
        assert ".claude/commands/dev.md" in joined
        assert ".claude/commands/epic-init.md" in joined
        assert "rm -f" in joined
        # Reported, never removed.
        assert legacy.is_file()

    def test_a_clean_repo_reports_no_orphans(self, tmp_path: Path) -> None:
        project = _make_project(tmp_path)
        assert scaffold(project, include_agents=False).orphans == []

    def test_a_hand_edited_command_is_reported_with_migration_guidance(
        self, tmp_path: Path
    ) -> None:
        project = _make_project(tmp_path)
        scaffold(project, include_agents=False)
        target = project / ".claude" / "commands" / "coordinator.md"
        target.write_text("HAND EDITED\n", encoding="utf-8")
        result = scaffold(project, include_agents=False)
        assert "coordinator" in result.commands_skipped
        joined = "\n".join(result.migration_notes)
        assert ".beadloom/flow/commands/coordinator.md" in joined
        assert target.read_text(encoding="utf-8") == "HAND EDITED\n"


class TestShippedTemplatesCarryNoProjectLocalFacts:
    """#177's third ask: nothing under templates/ may name OUR beads or issues."""

    def test_no_bead_id_or_issue_number_in_the_shipped_templates(self) -> None:
        import re
        from pathlib import Path

        from beadloom.onboarding.composer import templates_dir

        bead_id = re.compile(r"beadloom-[a-z0-9]{4}\.\d+")
        offenders: list[str] = []
        for path in sorted(Path(templates_dir()).rglob("*.txt")):
            text = path.read_text(encoding="utf-8")
            if bead_id.search(text):
                offenders.append(str(path))
        assert offenders == [], (
            "a project-local bead id reached a shipped template — the #177 "
            f"failure: {offenders}"
        )
