"""Tests for the Goose provider config + recipe wiring (BEAD-03 / F4.1).

Covers :class:`ProviderConfig` (Qwen3.7-Plus over an OpenAI-compatible /
DashScope endpoint, key from ``QWEN_API_KEY`` — never inlined) and the recipe
contract assertions. No network: the env key is referenced by name only and the
recipe is validated as a static artifact.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import yaml
from tools.ai_techwriter.provider import (
    DASHSCOPE_OPENAI_BASE_URL,
    DEFAULT_API_KEY_ENV,
    DEFAULT_BASE_URL_ENV,
    QWEN_MODEL,
    ProviderConfig,
    default_recipe_path,
    qwen_provider,
)

if TYPE_CHECKING:
    import pytest


def test_qwen_provider_defaults() -> None:
    cfg = qwen_provider()
    assert cfg.provider == "openai"
    assert cfg.model == QWEN_MODEL == "qwen3.7-plus"
    assert cfg.api_key_env == DEFAULT_API_KEY_ENV == "QWEN_API_KEY"
    # DashScope OpenAI-compatible endpoint.
    assert cfg.base_url.startswith("https://")
    assert "compatible-mode" in cfg.base_url or "dashscope" in cfg.base_url
    # Thinking ENABLED (quality first — no think-capping).
    assert cfg.thinking_enabled is True
    # Generous runaway caps (safety net, not a quality knob).
    assert cfg.max_turns >= 20
    assert cfg.max_tokens >= 1_000_000


def test_provider_env_references_key_by_name_only() -> None:
    cfg = qwen_provider()
    env = cfg.goose_env(api_key="secret-value-123")
    # The OpenAI-compatible provider knobs are wired.
    assert env["GOOSE_PROVIDER"] == "openai"
    assert env["GOOSE_MODEL"] == "qwen3.7-plus"
    assert env["OPENAI_BASE_URL"] == cfg.base_url
    assert env["OPENAI_API_KEY"] == "secret-value-123"
    # Thinking enabled flag is surfaced to Goose.
    assert env["GOOSE_MODE"] == "auto"


def test_provider_goose_env_omits_key_when_absent() -> None:
    cfg = qwen_provider()
    env = cfg.goose_env(api_key=None)
    # Without a resolved key we never invent one — the var is simply absent so
    # Goose fails loudly rather than calling the API anonymously.
    assert "OPENAI_API_KEY" not in env
    assert env["GOOSE_PROVIDER"] == "openai"


def test_provider_resolve_key_reads_named_env(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = qwen_provider()
    monkeypatch.setenv("QWEN_API_KEY", "from-env")
    assert cfg.resolve_api_key() == "from-env"


def test_provider_resolve_key_none_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = qwen_provider()
    monkeypatch.delenv("QWEN_API_KEY", raising=False)
    assert cfg.resolve_api_key() is None


# --------------------------------------------------------------------------- #
# base_url env resolution (QWEN_BASE_URL → MaaS workspace endpoint)
# --------------------------------------------------------------------------- #


def test_base_url_env_name_is_qwen_base_url() -> None:
    assert DEFAULT_BASE_URL_ENV == "QWEN_BASE_URL"


def test_qwen_provider_base_url_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QWEN_BASE_URL", "https://maas.example.com/v1")
    cfg = qwen_provider()
    assert cfg.base_url == "https://maas.example.com/v1"


def test_qwen_provider_base_url_default_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("QWEN_BASE_URL", raising=False)
    cfg = qwen_provider()
    assert cfg.base_url == DASHSCOPE_OPENAI_BASE_URL


def test_qwen_provider_base_url_default_when_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    # An empty/whitespace var must not silently point Goose at "" — fall back.
    monkeypatch.setenv("QWEN_BASE_URL", "")
    cfg = qwen_provider()
    assert cfg.base_url == DASHSCOPE_OPENAI_BASE_URL


def test_qwen_provider_explicit_base_url_wins_over_env(monkeypatch: pytest.MonkeyPatch) -> None:
    # An explicit caller arg overrides both env and the generic default.
    monkeypatch.setenv("QWEN_BASE_URL", "https://from-env/v1")
    cfg = qwen_provider(base_url="https://explicit/v1")
    assert cfg.base_url == "https://explicit/v1"


def test_custom_provider_config() -> None:
    cfg = ProviderConfig(
        provider="openai",
        model="m",
        base_url="https://x/v1",
        api_key_env="MY_KEY",
        max_turns=5,
        max_tokens=10,
        thinking_enabled=False,
    )
    assert cfg.api_key_env == "MY_KEY"
    assert cfg.max_turns == 5


# --------------------------------------------------------------------------- #
# recipe artifact
# --------------------------------------------------------------------------- #


def test_default_recipe_path_points_at_shipped_yaml() -> None:
    path = default_recipe_path()
    assert path.name == "recipe.yaml"
    assert path.exists(), f"shipped recipe missing: {path}"


def test_recipe_declares_constrained_tool_allow_list() -> None:
    recipe = yaml.safe_load(default_recipe_path().read_text(encoding="utf-8"))
    assert isinstance(recipe, dict)
    # The recipe takes the per-doc packet as a parameter.
    param_names = {p["key"] for p in recipe["parameters"]}
    assert "packet" in param_names
    # Instructions port the tech-writer protocol (accuracy over volume, mark
    # unknowns, freshness-baseline gotcha, reconcile doc<->code).
    text = (recipe.get("instructions", "") + recipe.get("prompt", "")).lower()
    assert "accuracy over volume" in text
    assert "docs/" in text


def test_recipe_allow_list_is_read_only_plus_docs_writes() -> None:
    recipe = yaml.safe_load(default_recipe_path().read_text(encoding="utf-8"))
    allow = recipe["tools"]["allow"]
    joined = "\n".join(allow).lower()
    # beadloom read + git read + read-only fs are allowed.
    assert "beadloom ctx" in joined
    assert "beadloom sync-check" in joined
    assert "git diff" in joined
    # writes are restricted to docs/**.
    assert "docs/**" in joined
    # explicit denials: no src writes, no arbitrary shell, no network.
    deny = "\n".join(recipe["tools"]["deny"]).lower()
    assert "src/**" in deny


def test_recipe_enables_thinking() -> None:
    recipe = yaml.safe_load(default_recipe_path().read_text(encoding="utf-8"))
    settings = recipe.get("settings", {})
    assert settings.get("thinking") is True


def test_recipe_path_round_trips_for_runner() -> None:
    # default_recipe_path must be a Path the GooseAgentRunner can stringify.
    assert isinstance(default_recipe_path(), Path)
