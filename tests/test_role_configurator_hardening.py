"""Hardening tests for the BDL-052 S3 role configurator (BEAD-08).

Complements ``tests/test_role_configurator.py`` (BEAD-07) — these pin the
behaviours that guarantee the configurator is honest and tool/stack-agnostic,
without re-asserting what BEAD-07 already proves:

- **Compose correctness + FSD↔DDD parity**: ``ddd+python`` and
  ``fsd+vuejs/typescript`` are DISTINCT and each contains ONLY its own CORE +
  architecture + stack overlays (the other's content is absent), and FSD is at
  full parity with DDD across every role (not a stub).
- **All overlays compose** for all roles, with the right per-stack/per-role
  overlay markers and a deterministic (sorted) multi-stack order.
- **flow.yml validation + resolve precedence + detect_stack** edge cases.
- **Adapter generation** tool-set selection + the Cursor orchestrator pointer.
- **Drift-guard** at the ``config-check`` level: a CORE/overlay edit without
  regen, a hand-edited adapter, and a cursor-set hand-edit all FAIL and are
  restored by ``--fix``.
- **CLI scaffolding**: ``--tool cursor --architecture fsd --stack vuejs,typescript``
  composes the fsd+vuejs+typescript Cursor set (NOT python/ddd).
- **Beadloom self-consistency** at the per-role marker level.

Deterministic, no network — generation happens under ``tmp_path``.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from click.testing import CliRunner

from beadloom.onboarding.flow_config import (
    FLOW_CONFIG_RELPATH,
    SUPPORTED_STACKS,
    FlowConfig,
    FlowConfigError,
    build_flow_config,
    detect_stack,
    load_flow_config,
    resolve_flow_config,
)
from beadloom.onboarding.role_adapters import (
    cursor_rules_body,
    cursor_rules_relpath,
    generate_adapters,
)
from beadloom.onboarding.role_composer import (
    ROLE_NAMES,
    compose_all_roles,
    compose_role,
    roles_templates_root,
)
from beadloom.services.cli import main

REPO_ROOT = Path(__file__).resolve().parents[1]

def _ddd_python(role: str) -> str:
    return compose_role(role, architecture="ddd", stack=["python"])


def _fsd_frontend(role: str) -> str:
    return compose_role(role, architecture="fsd", stack=["vuejs", "typescript"])


def _overlay_markers(text: str) -> list[str]:
    """The ``<!-- overlay:NAME -->`` markers, in document order."""
    return re.findall(r"overlay:([\w-]+)", text)


def _write_flow(root: Path, body: str) -> Path:
    cfg = root / FLOW_CONFIG_RELPATH
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(body, encoding="utf-8")
    return cfg


# --------------------------------------------------------------------------- #
# Compose correctness + FSD↔DDD parity (the central guarantee)
# --------------------------------------------------------------------------- #


class TestComposeFsdDddParity:
    def test_ddd_python_contains_only_its_own_overlays(self) -> None:
        text = _ddd_python("dev")
        # Its own CORE + ddd architecture + python stack.
        assert _overlay_markers(text) == ["ddd", "python"]
        assert "Domain-Driven Design" in text
        # And NONE of the FSD-frontend content leaks in.
        assert "Feature-Sliced Design" not in text
        assert "overlay:fsd" not in text
        assert "overlay:vuejs" not in text
        assert "overlay:typescript" not in text

    def test_fsd_frontend_contains_only_its_own_overlays(self) -> None:
        text = _fsd_frontend("dev")
        # fsd architecture + sorted stack overlays (typescript before vuejs).
        assert _overlay_markers(text) == ["fsd", "typescript", "vuejs"]
        assert "Feature-Sliced Design" in text
        # And NONE of the ddd/python content leaks in.
        assert "Domain-Driven Design" not in text
        assert "overlay:ddd" not in text
        assert "overlay:python" not in text

    @pytest.mark.parametrize("role", ROLE_NAMES)
    def test_ddd_and_fsd_distinct_for_every_role(self, role: str) -> None:
        assert _ddd_python(role) != _fsd_frontend(role)

    @pytest.mark.parametrize("role", ROLE_NAMES)
    def test_fsd_parity_every_role_has_real_arch_block_not_stub(
        self, role: str
    ) -> None:
        """FSD is at parity with DDD: every role carries a substantive FSD
        architecture overlay (the layer chain), not an empty placeholder."""
        text = compose_role(role, architecture="fsd", stack=["typescript"])
        assert "Feature-Sliced Design" in text
        assert "overlay:fsd" in text
        # Parity check: the FSD arch fragment file exists and is substantive
        # (not a placeholder) for EVERY role — mirroring DDD's per-role coverage.
        frag = roles_templates_root() / "architecture" / "fsd" / f"{role}.md.txt"
        assert frag.is_file(), role
        body = frag.read_text(encoding="utf-8")
        assert len(body.strip()) > 100, role  # real guidance, not a stub
        # Names FSD's distinguishing vocabulary (slice/layer/segment).
        lowered = body.lower()
        assert "slice" in lowered or "layer" in lowered, role

    def test_fsd_dev_states_lower_cannot_import_higher(self) -> None:
        text = compose_role("dev", architecture="fsd", stack=["typescript"])
        lowered = text.lower()
        assert "lower" in lowered and "higher" in lowered and "import" in lowered

    @pytest.mark.parametrize("role", ROLE_NAMES)
    def test_ddd_parity_every_role_has_real_arch_block(self, role: str) -> None:
        text = _ddd_python(role)
        assert "Domain-Driven Design" in text
        frag = roles_templates_root() / "architecture" / "ddd" / f"{role}.md.txt"
        assert frag.is_file() and frag.read_text(encoding="utf-8").strip()


# --------------------------------------------------------------------------- #
# All overlays compose; deterministic ordering; per-stack/per-role markers
# --------------------------------------------------------------------------- #


class TestAllOverlaysCompose:
    def test_multi_stack_overlays_appended_in_sorted_order(self) -> None:
        text = compose_role(
            "dev",
            architecture="fsd",
            stack=["vuejs", "python", "typescript"],
        )
        # Architecture first, then the stacks sorted alphabetically.
        assert _overlay_markers(text) == [
            "fsd",
            "python",
            "typescript",
            "vuejs",
        ]

    @pytest.mark.parametrize("stack", SUPPORTED_STACKS)
    def test_dev_role_carries_each_stack_overlay_marker(self, stack: str) -> None:
        # Every stack overlay refines the dev role -> its marker is present.
        text = compose_role("dev", architecture="ddd", stack=[stack])
        assert f"overlay:{stack}" in text

    def test_framework_only_stack_does_not_pollute_unrefined_role(self) -> None:
        # fastapi only refines `dev`; the `test` role gets CORE+arch but NO
        # fastapi STACK block (a missing per-role fragment contributes nothing).
        dev = compose_role("dev", architecture="ddd", stack=["fastapi"])
        test = compose_role("test", architecture="ddd", stack=["fastapi"])
        assert "overlay:fastapi" in dev
        assert "overlay:fastapi" not in test
        assert "## CORE" in test  # still a valid, non-empty role file

    def test_multi_stack_merges_cleanly_fastapi_python(self) -> None:
        text = compose_role(
            "dev", architecture="ddd", stack=["fastapi", "python"]
        )
        assert _overlay_markers(text) == ["ddd", "fastapi", "python"]
        # Both stack idioms are present.
        assert "FastAPI" in text
        assert "ruff" in text or "pytest" in text

    def test_stack_order_independent_byte_identical(self) -> None:
        a = compose_role(
            "dev", architecture="fsd", stack=["typescript", "vuejs", "javascript"]
        )
        b = compose_role(
            "dev", architecture="fsd", stack=["vuejs", "javascript", "typescript"]
        )
        assert a == b

    def test_duplicate_stack_entries_compose_per_listed(self) -> None:
        # compose_role does not de-dup (the validated FlowConfig does that);
        # but it must still compose without error and stay deterministic.
        once = compose_role("dev", architecture="ddd", stack=["python"])
        twice = compose_role(
            "dev", architecture="ddd", stack=["python", "python"]
        )
        # Two python fragments concatenated == the single fragment doubled.
        assert twice == once + once[once.index("<!-- overlay:python") :]


class TestComposeRoleErrors:
    def test_missing_core_fragment_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A role whose CORE fragment is absent raises loudly (no silent empty
        file). Exercised by pointing the templates root at an empty dir."""
        empty = tmp_path / "roles"
        empty.mkdir()
        import beadloom.onboarding.role_composer as rc

        monkeypatch.setattr(rc, "roles_templates_root", lambda: empty)
        with pytest.raises(FlowConfigError, match="missing CORE"):
            compose_role("dev", architecture="ddd", stack=["python"])


# --------------------------------------------------------------------------- #
# flow.yml validation + resolve precedence + detect_stack
# --------------------------------------------------------------------------- #


class TestFlowConfigEdges:
    def test_non_string_list_member_raises(self) -> None:
        with pytest.raises(FlowConfigError, match="string"):
            build_flow_config(
                {"tools": [1, 2], "architecture": ["ddd"], "stack": ["python"]}
            )

    def test_quality_unknown_value_raises(self) -> None:
        with pytest.raises(FlowConfigError, match="quality"):
            build_flow_config(
                {
                    "tools": ["claude"],
                    "architecture": ["ddd"],
                    "stack": ["python"],
                    "quality": ["six-sigma"],
                }
            )

    def test_quality_optional_defaults_empty(self) -> None:
        cfg = build_flow_config(
            {"tools": ["claude"], "architecture": ["ddd"], "stack": ["python"]}
        )
        assert cfg.quality == ()

    def test_stack_deduped_and_sorted(self) -> None:
        cfg = build_flow_config(
            {
                "tools": ["claude"],
                "architecture": ["ddd"],
                "stack": ["python", "fastapi", "python"],
            }
        )
        assert cfg.stack == ("fastapi", "python")


class TestDetectStack:
    def test_empty_project_defaults_to_python(self, tmp_path: Path) -> None:
        assert detect_stack(tmp_path) == ("python",)

    def test_detects_multiple_extensions_sorted(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "a.py").write_text("x", encoding="utf-8")
        (src / "b.ts").write_text("x", encoding="utf-8")
        (src / "c.vue").write_text("x", encoding="utf-8")
        assert detect_stack(tmp_path) == ("python", "typescript", "vuejs")

    def test_detects_under_app_dir(self, tmp_path: Path) -> None:
        app = tmp_path / "app"
        app.mkdir()
        (app / "main.js").write_text("x", encoding="utf-8")
        assert detect_stack(tmp_path) == ("javascript",)


class TestResolvePrecedence:
    def test_flag_overrides_flow_yml(self, tmp_path: Path) -> None:
        _write_flow(
            tmp_path,
            "tools: [claude]\narchitecture: [ddd]\nstack: [python]\n",
        )
        cfg = resolve_flow_config(
            tmp_path,
            tools=("cursor",),
            architecture="fsd",
            stack=("vuejs",),
        )
        assert cfg.tools == ("cursor",)
        assert cfg.architecture == "fsd"
        assert cfg.stack == ("vuejs",)

    def test_flow_yml_used_when_no_flags(self, tmp_path: Path) -> None:
        _write_flow(
            tmp_path,
            "tools: [claude, cursor]\narchitecture: [fsd]\nstack: [typescript]\n",
        )
        cfg = resolve_flow_config(tmp_path)
        assert cfg.tools == ("claude", "cursor")
        assert cfg.architecture == "fsd"
        assert cfg.stack == ("typescript",)

    def test_defaults_when_no_flow_and_no_flags(self, tmp_path: Path) -> None:
        # No flow.yml, empty project -> claude / ddd / detected python.
        cfg = resolve_flow_config(tmp_path)
        assert cfg.tools == ("claude",)
        assert cfg.architecture == "ddd"
        assert cfg.stack == ("python",)

    def test_malformed_flow_yml_raises_even_with_flags(self, tmp_path: Path) -> None:
        _write_flow(
            tmp_path, "tools: [emacs]\narchitecture: [ddd]\nstack: [python]\n"
        )
        with pytest.raises(FlowConfigError):
            resolve_flow_config(tmp_path, architecture="fsd")


# --------------------------------------------------------------------------- #
# Adapter generation — tool selection + cursor pointer
# --------------------------------------------------------------------------- #


class TestAdapterGeneration:
    def test_cursor_rules_body_is_orchestrator_pointer(self) -> None:
        body = cursor_rules_body()
        lowered = body.lower()
        assert "cursor" in lowered
        assert "coordinator" in lowered
        assert "beadloom ci" in lowered
        # Names the four roles it points at.
        for role in ROLE_NAMES:
            assert role in body

    def test_claude_only_does_not_write_cursor_pointer(self, tmp_path: Path) -> None:
        cfg = FlowConfig(tools=("claude",), architecture="ddd", stack=("python",))
        res = generate_adapters(cfg, tmp_path)
        assert not (tmp_path / cursor_rules_relpath()).exists()
        assert res.extra == []

    def test_both_tools_write_identical_role_bodies(self, tmp_path: Path) -> None:
        cfg = FlowConfig(
            tools=("claude", "cursor"),
            architecture="fsd",
            stack=("typescript", "vuejs"),
        )
        generate_adapters(cfg, tmp_path)
        for role in ROLE_NAMES:
            claude = (tmp_path / ".claude" / "agents" / f"{role}.md").read_text(
                encoding="utf-8"
            )
            cursor = (tmp_path / ".cursor" / "agents" / f"{role}.md").read_text(
                encoding="utf-8"
            )
            assert claude == cursor
            assert "Feature-Sliced Design" in claude

    def test_result_lists_relative_paths(self, tmp_path: Path) -> None:
        cfg = FlowConfig(tools=("cursor",), architecture="ddd", stack=("python",))
        res = generate_adapters(cfg, tmp_path)
        assert res.agents["cursor"] == [
            str(Path(".cursor") / "agents" / f"{r}.md") for r in ROLE_NAMES
        ]
        assert str(cursor_rules_relpath()) in res.extra

    def test_idempotent_across_tools_and_pointer(self, tmp_path: Path) -> None:
        cfg = FlowConfig(
            tools=("claude", "cursor"), architecture="fsd", stack=("vuejs",)
        )
        generate_adapters(cfg, tmp_path)
        snap = {
            p: p.read_text(encoding="utf-8")
            for p in tmp_path.rglob("*.md")
        }
        generate_adapters(cfg, tmp_path)
        after = {
            p: p.read_text(encoding="utf-8")
            for p in tmp_path.rglob("*.md")
        }
        assert snap == after

    def test_generated_adapter_equals_compose(self, tmp_path: Path) -> None:
        cfg = FlowConfig(
            tools=("cursor",), architecture="fsd", stack=("typescript", "vuejs")
        )
        generate_adapters(cfg, tmp_path)
        composed = compose_all_roles(cfg)
        for role in ROLE_NAMES:
            on_disk = (tmp_path / ".cursor" / "agents" / f"{role}.md").read_text(
                encoding="utf-8"
            )
            assert on_disk == composed[role]


# --------------------------------------------------------------------------- #
# Drift-guard at the config-check level (the key honesty guarantee)
# --------------------------------------------------------------------------- #


def _scaffolded_project(tmp_path: Path, flow_body: str) -> Path:
    from beadloom.onboarding.agentic_flow_setup import scaffold

    project = tmp_path / "acme-service"
    project.mkdir()
    (project / "pyproject.toml").write_text(
        '[project]\nname = "acme-service"\nversion = "9.9.9"\n'
        'dependencies = ["click", "rich"]\n',
        encoding="utf-8",
    )
    (project / ".beadloom").mkdir(parents=True, exist_ok=True)
    (project / ".beadloom" / "flow.yml").write_text(flow_body, encoding="utf-8")
    scaffold(project)
    # Compose the adapters to match the flow (config-check --fix path).
    CliRunner().invoke(main, ["config-check", "--fix", "--project", str(project)])
    return project


class TestDriftGuardConfigCheck:
    def test_core_overlay_edit_without_regen_fails(self, tmp_path: Path) -> None:
        """A CORE/overlay change that the adapter on disk was NOT regenerated
        for is caught: simulate by editing the on-disk adapter away from its
        composition (equivalent to a stale composition)."""
        project = _scaffolded_project(
            tmp_path, "tools: [claude]\narchitecture: [ddd]\nstack: [python]\n"
        )
        dev = project / ".claude" / "agents" / "dev.md"
        stale = dev.read_text(encoding="utf-8").replace(
            "## CORE", "## CORE (old, pre-overlay-bump)"
        )
        dev.write_text(stale, encoding="utf-8")
        result = CliRunner().invoke(
            main, ["config-check", "--project", str(project)]
        )
        assert result.exit_code == 1
        assert ".claude/agents/dev.md" in result.output

    def test_cursor_adapter_handedit_fails_and_fix_restores(
        self, tmp_path: Path
    ) -> None:
        project = _scaffolded_project(
            tmp_path,
            "tools: [claude, cursor]\narchitecture: [fsd]\nstack: [vuejs]\n",
        )
        cursor_dev = project / ".cursor" / "agents" / "dev.md"
        original = cursor_dev.read_text(encoding="utf-8")
        cursor_dev.write_text("HAND EDITED\n", encoding="utf-8")
        bad = CliRunner().invoke(
            main, ["config-check", "--project", str(project)]
        )
        assert bad.exit_code == 1
        assert ".cursor/agents/dev.md" in bad.output
        fixed = CliRunner().invoke(
            main, ["config-check", "--fix", "--project", str(project)]
        )
        assert fixed.exit_code == 0
        assert cursor_dev.read_text(encoding="utf-8") == original

    def test_clean_after_fix_is_green(self, tmp_path: Path) -> None:
        project = _scaffolded_project(
            tmp_path, "tools: [claude]\narchitecture: [ddd]\nstack: [python]\n"
        )
        result = CliRunner().invoke(
            main, ["config-check", "--project", str(project)]
        )
        assert result.exit_code == 0, result.output


# --------------------------------------------------------------------------- #
# CLI scaffolding — cursor + fsd + vuejs,typescript (NOT python/ddd)
# --------------------------------------------------------------------------- #


class TestCliScaffoldCursorFsd:
    def _project(self, tmp_path: Path) -> Path:
        project = tmp_path / "frontend-app"
        project.mkdir()
        (project / "pyproject.toml").write_text(
            '[project]\nname = "frontend-app"\nversion = "1.0.0"\n'
            'dependencies = ["click"]\n',
            encoding="utf-8",
        )
        return project

    def test_cursor_fsd_frontend_scaffold(self, tmp_path: Path) -> None:
        project = self._project(tmp_path)
        result = CliRunner().invoke(
            main,
            [
                "setup-agentic-flow",
                "--project",
                str(project),
                "--tool",
                "cursor",
                "--architecture",
                "fsd",
                "--stack",
                "vuejs,typescript",
            ],
        )
        assert result.exit_code == 0, result.output
        # The Cursor set is composed from fsd + vuejs + typescript.
        for role in ROLE_NAMES:
            text = (project / ".cursor" / "agents" / f"{role}.md").read_text(
                encoding="utf-8"
            )
            assert "Feature-Sliced Design" in text
            # NOT the python/ddd defaults.
            assert "Domain-Driven Design" not in text
            assert "overlay:python" not in text
        dev = (project / ".cursor" / "agents" / "dev.md").read_text(
            encoding="utf-8"
        )
        assert _overlay_markers(dev) == ["fsd", "typescript", "vuejs"]
        # The Cursor orchestrator pointer was written.
        assert (project / cursor_rules_relpath()).is_file()
        # And it did NOT write a Claude agent set (cursor only).
        assert not (project / ".claude" / "agents" / "dev.md").exists()

    def test_cli_echoes_selected_composition(self, tmp_path: Path) -> None:
        project = self._project(tmp_path)
        result = CliRunner().invoke(
            main,
            [
                "setup-agentic-flow",
                "--project",
                str(project),
                "--tool",
                "cursor",
                "--architecture",
                "fsd",
                "--stack",
                "vuejs,typescript",
            ],
        )
        assert "architecture=fsd" in result.output
        assert "typescript" in result.output and "vuejs" in result.output


# --------------------------------------------------------------------------- #
# Beadloom self-consistency — own adapters match composition per role + markers
# --------------------------------------------------------------------------- #


class TestBeadloomSelfConsistency:
    def test_own_flow_is_claude_ddd_python(self) -> None:
        cfg = load_flow_config(REPO_ROOT)
        assert cfg.tools == ("claude",)
        assert cfg.architecture == "ddd"
        assert cfg.stack == ("python",)

    @pytest.mark.parametrize("role", ROLE_NAMES)
    def test_live_adapter_has_expected_markers(self, role: str) -> None:
        live = (REPO_ROOT / ".claude" / "agents" / f"{role}.md").read_text(
            encoding="utf-8"
        )
        # ddd architecture + python stack overlays present; FSD/vuejs absent.
        assert "overlay:ddd" in live
        assert "overlay:python" in live
        assert "overlay:fsd" not in live
        assert "Domain-Driven Design" in live

    @pytest.mark.parametrize("role", ROLE_NAMES)
    def test_live_adapter_byte_equals_compose(self, role: str) -> None:
        live = (REPO_ROOT / ".claude" / "agents" / f"{role}.md").read_text(
            encoding="utf-8"
        )
        assert live == compose_role(role, architecture="ddd", stack=["python"])
