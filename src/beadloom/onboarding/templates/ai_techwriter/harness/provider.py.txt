"""Goose provider config + recipe location (RFC Q2 / Q4).

The model boundary, in one typed place:

* :class:`ProviderConfig` — Qwen3.7-Plus over an **OpenAI-compatible /
  DashScope** endpoint. The API key is read from a **named environment
  variable** (``QWEN_API_KEY`` by default) and is **never inlined** in the repo
  or in this module — only referenced by name, resolved at run time on the
  CI runner that holds the secret.
* Generous per-run **hard caps** (max turns / tokens) act purely as a runaway
  safety net (RFC Q2) — never as a per-call quality knob; extended thinking
  stays ENABLED (quality first, no tiering — principle 10).

No I/O happens at import time; :meth:`ProviderConfig.resolve_api_key` is the
only function that touches the environment.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

#: Canonical model id (top-tier, no tiering — RFC Q2).
QWEN_MODEL = "qwen3.7-plus"

#: Env var holding the model API key on the CI runner (never inlined).
DEFAULT_API_KEY_ENV = "QWEN_API_KEY"

#: DashScope OpenAI-compatible gateway (international endpoint).
DASHSCOPE_OPENAI_BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"


@dataclass(frozen=True)
class ProviderConfig:
    """How Goose reaches the model — provider, endpoint, key env, caps.

    ``provider`` is Goose's provider id (``"openai"`` for any OpenAI-compatible
    gateway, which DashScope exposes). ``api_key_env`` names the env var; the
    secret value is resolved on the runner and passed to Goose via the process
    environment, never written to disk.
    """

    provider: str
    model: str
    base_url: str
    api_key_env: str
    max_turns: int
    max_tokens: int
    thinking_enabled: bool

    def resolve_api_key(self) -> str | None:
        """Read the key from the named env var (``None`` if unset).

        Returning ``None`` is intentional: in a sandbox / local dry-run the
        secret is absent, and the caller must surface that rather than call the
        API anonymously.
        """
        value = os.environ.get(self.api_key_env)
        return value or None

    def goose_env(self, *, api_key: str | None) -> dict[str, str]:
        """Build the Goose provider environment for one invocation.

        The OpenAI-compatible provider knobs (``GOOSE_PROVIDER`` / ``GOOSE_MODEL``
        / ``OPENAI_BASE_URL`` / ``OPENAI_API_KEY``) are set here. When *api_key*
        is ``None`` the key var is simply omitted so Goose fails loudly instead
        of issuing an anonymous request.
        """
        env: dict[str, str] = {
            "GOOSE_PROVIDER": self.provider,
            "GOOSE_MODEL": self.model,
            "OPENAI_BASE_URL": self.base_url,
            # auto mode lets the recipe's allow/deny tool gating apply without
            # interactive approval prompts (headless CI) — RFC Q4 blast radius
            # is enforced by the recipe, not by interactive trust.
            "GOOSE_MODE": "auto",
        }
        if api_key is not None:
            env["OPENAI_API_KEY"] = api_key
        return env


def qwen_provider(
    *,
    api_key_env: str = DEFAULT_API_KEY_ENV,
    max_turns: int = 50,
    max_tokens: int = 2_000_000,
) -> ProviderConfig:
    """Default provider config: Qwen3.7-Plus via DashScope (OpenAI-compatible).

    Caps default to a generous runaway ceiling (mirrors
    :class:`~tools.ai_techwriter.models.HarnessConfig`) — a safety net only.
    """
    return ProviderConfig(
        provider="openai",
        model=QWEN_MODEL,
        base_url=DASHSCOPE_OPENAI_BASE_URL,
        api_key_env=api_key_env,
        max_turns=max_turns,
        max_tokens=max_tokens,
        thinking_enabled=True,
    )


def default_recipe_path() -> Path:
    """Path to the shipped Goose recipe (``tools/ai_techwriter/recipe.yaml``)."""
    return Path(__file__).resolve().parent / "recipe.yaml"
