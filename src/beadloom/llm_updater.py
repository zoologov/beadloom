"""LLM-powered documentation auto-updater."""

# beadloom:domain=llm-updater

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import httpx

if TYPE_CHECKING:
    from pathlib import Path

_SYSTEM_PROMPT = (
    "You are a documentation maintenance assistant for a software project. "
    "When given the current documentation and changed code, you update the "
    "documentation to accurately reflect the code changes. "
    "Return ONLY the updated documentation content. "
    "Preserve the original Markdown format, style, and structure. "
    "Do not add commentary, explanations, or markdown code fences around the output."
)


@dataclass(frozen=True)
class LLMConfig:
    """LLM provider configuration."""

    provider: str  # "anthropic" or "openai"
    model: str
    api_key_env: str
    max_tokens: int = 4096


class LLMError(Exception):
    """Raised when an LLM API call fails."""


def parse_llm_config(raw: dict[str, Any]) -> LLMConfig:
    """Parse and validate LLM config from config.yml ``llm`` section.

    Raises
    ------
    ValueError
        If required fields are missing or provider is unsupported.
    """
    provider = raw.get("provider", "")
    if provider not in ("anthropic", "openai"):
        msg = f"Unsupported LLM provider: {provider!r}. Use 'anthropic' or 'openai'."
        raise ValueError(msg)

    model = raw.get("model", "")
    if not model:
        msg = "LLM config requires 'model' field."
        raise ValueError(msg)

    api_key_env = raw.get("api_key_env", "")
    if not api_key_env:
        msg = "LLM config requires 'api_key_env' field."
        raise ValueError(msg)

    max_tokens = int(raw.get("max_tokens", 4096))

    return LLMConfig(
        provider=provider,
        model=model,
        api_key_env=api_key_env,
        max_tokens=max_tokens,
    )


def build_update_prompt(
    doc_content: str,
    code_changes: list[dict[str, str]],
    context_summary: str,
) -> str:
    """Build the user prompt for LLM doc update.

    Parameters
    ----------
    doc_content:
        Current documentation file content.
    code_changes:
        List of dicts with ``code_path`` and ``content`` keys.
    context_summary:
        Additional context (graph summary, related docs).
    """
    parts: list[str] = []

    parts.append("## Current Documentation\n")
    parts.append(doc_content)
    parts.append("")

    parts.append("## Changed Code Files\n")
    for change in code_changes:
        parts.append(f"### {change['code_path']}\n")
        parts.append("```")
        parts.append(change["content"])
        parts.append("```\n")

    if context_summary:
        parts.append("## Project Context\n")
        parts.append(context_summary)
        parts.append("")

    parts.append(
        "## Task\n"
        "Update the documentation above to reflect the code changes. "
        "Return the complete updated documentation."
    )

    return "\n".join(parts)


def _get_api_key(config: LLMConfig) -> str:
    """Resolve API key from environment variable.

    Raises
    ------
    LLMError
        If the environment variable is not set.
    """
    key = os.environ.get(config.api_key_env, "")
    if not key:
        msg = f"API key not found. Set environment variable: {config.api_key_env}"
        raise LLMError(msg)
    return key


def _call_anthropic(config: LLMConfig, api_key: str, prompt: str) -> str:
    """Call Anthropic Messages API."""
    response = httpx.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": config.model,
            "max_tokens": config.max_tokens,
            "system": _SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=120.0,
    )

    if response.status_code != 200:
        msg = f"Anthropic API error {response.status_code}: {response.text}"
        raise LLMError(msg)

    data = response.json()
    content_blocks = data.get("content", [])
    if not content_blocks:
        msg = "Anthropic API returned empty response."
        raise LLMError(msg)

    return str(content_blocks[0].get("text", ""))


def _call_openai(config: LLMConfig, api_key: str, prompt: str) -> str:
    """Call OpenAI Chat Completions API."""
    response = httpx.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": config.model,
            "max_tokens": config.max_tokens,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        },
        timeout=120.0,
    )

    if response.status_code != 200:
        msg = f"OpenAI API error {response.status_code}: {response.text}"
        raise LLMError(msg)

    data = response.json()
    choices = data.get("choices", [])
    if not choices:
        msg = "OpenAI API returned empty response."
        raise LLMError(msg)

    return str(choices[0].get("message", {}).get("content", ""))


def call_llm(config: LLMConfig, prompt: str) -> str:
    """Call the configured LLM provider and return response text.

    Raises
    ------
    LLMError
        On API errors or missing API key.
    """
    api_key = _get_api_key(config)

    if config.provider == "anthropic":
        return _call_anthropic(config, api_key, prompt)
    if config.provider == "openai":
        return _call_openai(config, api_key, prompt)

    msg = f"Unsupported provider: {config.provider}"
    raise LLMError(msg)


def auto_update_doc(
    config: LLMConfig,
    doc_path: Path,
    code_changes: list[dict[str, str]],
    context_summary: str = "",
) -> str:
    """Generate an updated doc using LLM.

    Parameters
    ----------
    config:
        LLM provider configuration.
    doc_path:
        Path to the documentation file.
    code_changes:
        List of dicts with ``code_path`` and ``content`` keys.
    context_summary:
        Optional context from knowledge graph.

    Returns
    -------
    str
        Proposed updated documentation content.

    Raises
    ------
    LLMError
        On API errors.
    FileNotFoundError
        If doc_path does not exist.
    """
    doc_content = doc_path.read_text(encoding="utf-8")
    prompt = build_update_prompt(doc_content, code_changes, context_summary)
    return call_llm(config, prompt)
