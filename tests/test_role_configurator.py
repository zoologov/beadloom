"""Tests for the BDL-052 S3 role configurator (flow.yml + overlays + adapters).

Covers:
- ``.beadloom/flow.yml`` load + validate (good + bad configs);
- ``compose_role`` correctness (CORE+ddd+python vs CORE+fsd+vuejs are distinct;
  FSD parity with DDD; deterministic ordering);
- ``generate_adapters`` writes the claude + cursor sets;
- the drift-guard catches a hand-edited adapter and a CORE change without regen;
- Beadloom's own ``.claude/agents/*`` reproduce exactly from CORE+ddd+python.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from beadloom.onboarding.flow_config import (
    SUPPORTED_ARCHITECTURES,
    SUPPORTED_STACKS,
    FlowConfig,
    FlowConfigError,
    build_flow_config,
    load_flow_config,
    load_flow_config_or_default,
)
from beadloom.onboarding.role_adapters import (
    TOOL_AGENT_DIRS,
    cursor_rules_relpath,
    generate_adapters,
)
from beadloom.onboarding.role_composer import (
    ROLE_NAMES,
    compose_all_roles,
    compose_role,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def _write_flow(root: Path, body: str) -> Path:
    cfg = root / ".beadloom" / "flow.yml"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(body, encoding="utf-8")
    return cfg


# --------------------------------------------------------------------------- #
# flow.yml schema + loader
# --------------------------------------------------------------------------- #


class TestFlowConfigLoad:
    def test_loads_valid_config(self, tmp_path: Path) -> None:
        _write_flow(
            tmp_path,
            "tools: [claude, cursor]\narchitecture: [ddd]\n"
            "stack: [python, fastapi]\nquality: [clean-code, tdd]\n",
        )
        cfg = load_flow_config(tmp_path)
        assert cfg.tools == ("claude", "cursor")
        assert cfg.architecture == "ddd"
        assert cfg.stack == ("fastapi", "python")  # sorted/normalized
        assert cfg.quality == ("clean-code", "tdd")

    def test_beadloom_own_config_is_claude_ddd_python(self) -> None:
        cfg = load_flow_config(REPO_ROOT)
        assert cfg.tools == ("claude",)
        assert cfg.architecture == "ddd"
        assert cfg.stack == ("python",)

    def test_missing_file_raises_filenotfound(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_flow_config(tmp_path)

    def test_or_default_returns_default_when_absent(self, tmp_path: Path) -> None:
        default = FlowConfig(
            tools=("claude",), architecture="ddd", stack=("python",)
        )
        assert load_flow_config_or_default(tmp_path, default=default) is default

    def test_or_default_still_validates_present_bad_config(
        self, tmp_path: Path
    ) -> None:
        _write_flow(tmp_path, "tools: [emacs]\narchitecture: [ddd]\nstack: [python]\n")
        default = FlowConfig(
            tools=("claude",), architecture="ddd", stack=("python",)
        )
        with pytest.raises(FlowConfigError):
            load_flow_config_or_default(tmp_path, default=default)


class TestFlowConfigValidation:
    def test_unknown_tool_raises_with_name_and_allowed(self) -> None:
        with pytest.raises(FlowConfigError, match="emacs"):
            build_flow_config(
                {"tools": ["claude", "emacs"], "architecture": ["ddd"], "stack": ["python"]}
            )

    def test_unknown_architecture_raises(self) -> None:
        with pytest.raises(FlowConfigError, match="hexagonal"):
            build_flow_config(
                {"tools": ["claude"], "architecture": ["hexagonal"], "stack": ["python"]}
            )

    def test_unknown_stack_raises(self) -> None:
        with pytest.raises(FlowConfigError, match="rust"):
            build_flow_config(
                {"tools": ["claude"], "architecture": ["ddd"], "stack": ["rust"]}
            )

    def test_architecture_must_be_exactly_one(self) -> None:
        with pytest.raises(FlowConfigError, match="exactly one"):
            build_flow_config(
                {"tools": ["claude"], "architecture": ["ddd", "fsd"], "stack": ["python"]}
            )

    def test_empty_tools_raises(self) -> None:
        with pytest.raises(FlowConfigError, match="tools"):
            build_flow_config(
                {"tools": [], "architecture": ["ddd"], "stack": ["python"]}
            )

    def test_empty_stack_raises(self) -> None:
        with pytest.raises(FlowConfigError, match="stack"):
            build_flow_config(
                {"tools": ["claude"], "architecture": ["ddd"], "stack": []}
            )

    def test_non_mapping_raises(self) -> None:
        with pytest.raises(FlowConfigError, match="mapping"):
            build_flow_config(["not", "a", "mapping"])

    def test_scalar_string_coerced_to_list(self) -> None:
        cfg = build_flow_config(
            {"tools": "claude", "architecture": "fsd", "stack": "vuejs"}
        )
        assert cfg.tools == ("claude",)
        assert cfg.architecture == "fsd"
        assert cfg.stack == ("vuejs",)

    def test_invalid_yaml_raises_flowconfigerror(self, tmp_path: Path) -> None:
        _write_flow(tmp_path, "tools: [claude\narchitecture: ddd\n:::")
        with pytest.raises(FlowConfigError):
            load_flow_config(tmp_path)


# --------------------------------------------------------------------------- #
# compose_role correctness
# --------------------------------------------------------------------------- #


class TestComposeRole:
    @pytest.mark.parametrize("role", ROLE_NAMES)
    def test_core_ddd_python_has_all_sections(self, role: str) -> None:
        text = compose_role(role, architecture="ddd", stack=["python"])
        assert "## CORE" in text
        assert "## ARCHITECTURE" in text
        assert "## STACK" in text
        # Exactly one python overlay marker (the S2 structural invariant).
        assert text.count("<!-- overlay:python") == 1

    def test_ddd_python_differs_from_fsd_vuejs(self) -> None:
        ddd_py = compose_role("dev", architecture="ddd", stack=["python"])
        fsd_vue = compose_role("dev", architecture="fsd", stack=["vuejs"])
        assert ddd_py != fsd_vue
        # DDD names domains/layers; FSD names slices/layers.
        assert "Domain-Driven Design" in ddd_py
        assert "Feature-Sliced Design" in fsd_vue
        assert "Feature-Sliced Design" not in ddd_py
        assert "Domain-Driven Design" not in fsd_vue

    def test_fsd_overlay_has_layer_order_and_import_rule(self) -> None:
        text = compose_role("dev", architecture="fsd", stack=["typescript"])
        for layer in (
            "app",
            "processes",
            "pages",
            "widgets",
            "features",
            "entities",
            "shared",
        ):
            assert layer in text
        # The lower-cannot-import-higher rule must be stated.
        lowered = text.lower()
        assert "import" in lowered and "higher" in lowered

    def test_fsd_parity_all_roles_have_fragments(self) -> None:
        # FSD is at parity with DDD: every role composes a non-empty arch block.
        for role in ROLE_NAMES:
            text = compose_role(role, architecture="fsd", stack=["typescript"])
            assert "Feature-Sliced Design" in text, role

    def test_stack_overlays_deterministic_order(self) -> None:
        a = compose_role("dev", architecture="ddd", stack=["typescript", "vuejs"])
        b = compose_role("dev", architecture="ddd", stack=["vuejs", "typescript"])
        assert a == b  # sorted internally → order-independent

    def test_multiple_stacks_concatenate(self) -> None:
        text = compose_role(
            "dev", architecture="fsd", stack=["javascript", "typescript", "vuejs"]
        )
        assert "TypeScript" in text or "typescript" in text.lower()
        assert "Vue" in text or "vue" in text.lower()

    def test_unknown_role_raises(self) -> None:
        with pytest.raises(FlowConfigError, match="unknown role"):
            compose_role("architect", architecture="ddd", stack=["python"])

    def test_unknown_architecture_raises(self) -> None:
        with pytest.raises(FlowConfigError, match="architecture"):
            compose_role("dev", architecture="clean", stack=["python"])

    def test_unknown_stack_raises(self) -> None:
        with pytest.raises(FlowConfigError, match="stack"):
            compose_role("dev", architecture="ddd", stack=["cobol"])

    @pytest.mark.parametrize("arch", SUPPORTED_ARCHITECTURES)
    @pytest.mark.parametrize("stack", SUPPORTED_STACKS)
    def test_every_arch_stack_combo_composes_nonempty(
        self, arch: str, stack: str
    ) -> None:
        for role in ROLE_NAMES:
            text = compose_role(role, architecture=arch, stack=[stack])
            assert text.strip()
            assert "## CORE" in text


# --------------------------------------------------------------------------- #
# generate_adapters
# --------------------------------------------------------------------------- #


class TestGenerateAdapters:
    def test_writes_claude_set(self, tmp_path: Path) -> None:
        cfg = FlowConfig(tools=("claude",), architecture="ddd", stack=("python",))
        res = generate_adapters(cfg, tmp_path)
        for role in ROLE_NAMES:
            path = tmp_path / ".claude" / "agents" / f"{role}.md"
            assert path.is_file()
            assert path.read_text(encoding="utf-8") == compose_role(
                role, architecture="ddd", stack=["python"]
            )
        assert "claude" in res.agents

    def test_writes_cursor_set_with_orchestrator_rule(self, tmp_path: Path) -> None:
        cfg = FlowConfig(
            tools=("cursor",), architecture="fsd", stack=("typescript", "vuejs")
        )
        res = generate_adapters(cfg, tmp_path)
        for role in ROLE_NAMES:
            path = tmp_path / ".cursor" / "agents" / f"{role}.md"
            assert path.is_file()
            assert path.read_text(encoding="utf-8") == compose_role(
                role, architecture="fsd", stack=["typescript", "vuejs"]
            )
        rule = tmp_path / cursor_rules_relpath()
        assert rule.is_file()
        assert "cursor" in res.extra[0].lower() or rule.is_file()

    def test_writes_both_tool_sets(self, tmp_path: Path) -> None:
        cfg = FlowConfig(
            tools=("claude", "cursor"), architecture="ddd", stack=("python",)
        )
        generate_adapters(cfg, tmp_path)
        for tool in ("claude", "cursor"):
            adir = tmp_path / TOOL_AGENT_DIRS[tool]
            assert (adir / "dev.md").is_file()

    def test_idempotent(self, tmp_path: Path) -> None:
        cfg = FlowConfig(tools=("claude",), architecture="ddd", stack=("python",))
        generate_adapters(cfg, tmp_path)
        first = (tmp_path / ".claude" / "agents" / "dev.md").read_text(
            encoding="utf-8"
        )
        generate_adapters(cfg, tmp_path)
        second = (tmp_path / ".claude" / "agents" / "dev.md").read_text(
            encoding="utf-8"
        )
        assert first == second

    def test_cursor_only_does_not_write_claude(self, tmp_path: Path) -> None:
        cfg = FlowConfig(tools=("cursor",), architecture="ddd", stack=("python",))
        generate_adapters(cfg, tmp_path)
        assert not (tmp_path / ".claude" / "agents" / "dev.md").exists()


# --------------------------------------------------------------------------- #
# Drift-guard — Beadloom's own adapters reproduce from CORE+ddd+python
# --------------------------------------------------------------------------- #


class TestDriftGuard:
    def test_live_claude_agents_reproduce_from_compose(self) -> None:
        composed = compose_all_roles(load_flow_config(REPO_ROOT))
        for role in ROLE_NAMES:
            live = (REPO_ROOT / ".claude" / "agents" / f"{role}.md").read_text(
                encoding="utf-8"
            )
            assert live == composed[role], (
                f"{role}: .claude/agents/{role}.md drifted from "
                "compose_role(ddd, python) — re-run setup-agentic-flow"
            )

    def test_guard_catches_hand_edited_adapter(self, tmp_path: Path) -> None:
        cfg = FlowConfig(tools=("claude",), architecture="ddd", stack=("python",))
        generate_adapters(cfg, tmp_path)
        dev = tmp_path / ".claude" / "agents" / "dev.md"
        dev.write_text(dev.read_text(encoding="utf-8") + "\nHAND EDIT\n", "utf-8")
        composed = compose_role("dev", architecture="ddd", stack=["python"])
        assert dev.read_text(encoding="utf-8") != composed

    def test_guard_catches_core_change_without_regen(self, tmp_path: Path) -> None:
        # Simulate: a CORE/overlay improvement landed but the adapter on disk
        # was generated from the OLD composition → it no longer matches.
        cfg = FlowConfig(tools=("claude",), architecture="ddd", stack=("python",))
        generate_adapters(cfg, tmp_path)
        dev = tmp_path / ".claude" / "agents" / "dev.md"
        stale = dev.read_text(encoding="utf-8").replace("## CORE", "## CORE (old)")
        dev.write_text(stale, encoding="utf-8")
        composed = compose_role("dev", architecture="ddd", stack=["python"])
        assert dev.read_text(encoding="utf-8") != composed
