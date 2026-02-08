"""Tests for beadloom.llm_updater module."""

from __future__ import annotations

import os
import unittest.mock
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from beadloom.llm_updater import (
    LLMConfig,
    LLMError,
    auto_update_doc,
    build_update_prompt,
    call_llm,
    parse_llm_config,
)


class TestParseLLMConfig:
    def test_anthropic_config(self) -> None:
        raw = {
            "provider": "anthropic",
            "model": "claude-sonnet-4-20250514",
            "api_key_env": "ANTHROPIC_API_KEY",
        }
        config = parse_llm_config(raw)
        assert config.provider == "anthropic"
        assert config.model == "claude-sonnet-4-20250514"
        assert config.api_key_env == "ANTHROPIC_API_KEY"
        assert config.max_tokens == 4096

    def test_openai_config(self) -> None:
        raw = {
            "provider": "openai",
            "model": "gpt-4o",
            "api_key_env": "OPENAI_API_KEY",
            "max_tokens": 2048,
        }
        config = parse_llm_config(raw)
        assert config.provider == "openai"
        assert config.model == "gpt-4o"
        assert config.max_tokens == 2048

    def test_unsupported_provider(self) -> None:
        raw = {"provider": "gemini", "model": "x", "api_key_env": "K"}
        with pytest.raises(ValueError, match="Unsupported LLM provider"):
            parse_llm_config(raw)

    def test_missing_model(self) -> None:
        raw = {"provider": "anthropic", "api_key_env": "K"}
        with pytest.raises(ValueError, match="model"):
            parse_llm_config(raw)

    def test_missing_api_key_env(self) -> None:
        raw = {"provider": "anthropic", "model": "x"}
        with pytest.raises(ValueError, match="api_key_env"):
            parse_llm_config(raw)

    def test_empty_provider(self) -> None:
        raw = {"provider": "", "model": "x", "api_key_env": "K"}
        with pytest.raises(ValueError, match="Unsupported"):
            parse_llm_config(raw)


class TestBuildUpdatePrompt:
    def test_basic_prompt(self) -> None:
        prompt = build_update_prompt(
            doc_content="# Feature\n\nOld description.",
            code_changes=[
                {"code_path": "src/api.py", "content": "def handler():\n    return 'new'\n"},
            ],
            context_summary="Feature F1 is part of domain D1.",
        )
        assert "# Feature" in prompt
        assert "Old description" in prompt
        assert "src/api.py" in prompt
        assert "return 'new'" in prompt
        assert "Feature F1" in prompt
        assert "## Task" in prompt

    def test_multiple_code_changes(self) -> None:
        prompt = build_update_prompt(
            doc_content="Doc.",
            code_changes=[
                {"code_path": "a.py", "content": "code_a"},
                {"code_path": "b.py", "content": "code_b"},
            ],
            context_summary="",
        )
        assert "a.py" in prompt
        assert "b.py" in prompt

    def test_empty_context(self) -> None:
        prompt = build_update_prompt(
            doc_content="Doc.",
            code_changes=[{"code_path": "x.py", "content": "x"}],
            context_summary="",
        )
        assert "## Project Context" not in prompt


def _mock_anthropic_response(text: str) -> unittest.mock.MagicMock:
    """Create a mock httpx response for Anthropic API."""
    resp = unittest.mock.MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"content": [{"type": "text", "text": text}]}
    return resp


def _mock_openai_response(text: str) -> unittest.mock.MagicMock:
    """Create a mock httpx response for OpenAI API."""
    resp = unittest.mock.MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"choices": [{"message": {"content": text}}]}
    return resp


def _mock_error_response(status_code: int, text: str) -> unittest.mock.MagicMock:
    """Create a mock httpx error response."""
    resp = unittest.mock.MagicMock()
    resp.status_code = status_code
    resp.text = text
    return resp


class TestCallLLM:
    def test_anthropic_success(self) -> None:
        config = LLMConfig(
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            api_key_env="TEST_KEY",
        )

        with (
            unittest.mock.patch.dict(os.environ, {"TEST_KEY": "sk-test-123"}),
            unittest.mock.patch(
                "beadloom.llm_updater.httpx.post",
                return_value=_mock_anthropic_response("Updated doc content"),
            ) as mock_post,
        ):
            result = call_llm(config, "test prompt")

        assert result == "Updated doc content"
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "api.anthropic.com" in call_args[0][0]
        assert call_args[1]["headers"]["x-api-key"] == "sk-test-123"

    def test_openai_success(self) -> None:
        config = LLMConfig(
            provider="openai",
            model="gpt-4o",
            api_key_env="TEST_KEY",
        )

        with (
            unittest.mock.patch.dict(os.environ, {"TEST_KEY": "sk-openai-123"}),
            unittest.mock.patch(
                "beadloom.llm_updater.httpx.post",
                return_value=_mock_openai_response("Updated by OpenAI"),
            ) as mock_post,
        ):
            result = call_llm(config, "test prompt")

        assert result == "Updated by OpenAI"
        call_args = mock_post.call_args
        assert "api.openai.com" in call_args[0][0]

    def test_missing_api_key(self) -> None:
        config = LLMConfig(
            provider="anthropic",
            model="x",
            api_key_env="NONEXISTENT_KEY_12345",
        )
        os.environ.pop("NONEXISTENT_KEY_12345", None)
        with pytest.raises(LLMError, match="API key not found"):
            call_llm(config, "test")

    def test_anthropic_api_error(self) -> None:
        config = LLMConfig(
            provider="anthropic",
            model="x",
            api_key_env="TEST_KEY",
        )

        with (
            unittest.mock.patch.dict(os.environ, {"TEST_KEY": "sk-test"}),
            unittest.mock.patch(
                "beadloom.llm_updater.httpx.post",
                return_value=_mock_error_response(500, "Internal Server Error"),
            ),
            pytest.raises(LLMError, match="Anthropic API error 500"),
        ):
            call_llm(config, "test")

    def test_openai_api_error(self) -> None:
        config = LLMConfig(
            provider="openai",
            model="x",
            api_key_env="TEST_KEY",
        )

        with (
            unittest.mock.patch.dict(os.environ, {"TEST_KEY": "sk-test"}),
            unittest.mock.patch(
                "beadloom.llm_updater.httpx.post",
                return_value=_mock_error_response(429, "Rate limited"),
            ),
            pytest.raises(LLMError, match="OpenAI API error 429"),
        ):
            call_llm(config, "test")

    def test_anthropic_empty_response(self) -> None:
        config = LLMConfig(
            provider="anthropic",
            model="x",
            api_key_env="TEST_KEY",
        )
        resp = unittest.mock.MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"content": []}

        with (
            unittest.mock.patch.dict(os.environ, {"TEST_KEY": "sk-test"}),
            unittest.mock.patch("beadloom.llm_updater.httpx.post", return_value=resp),
            pytest.raises(LLMError, match="empty response"),
        ):
            call_llm(config, "test")

    def test_openai_empty_response(self) -> None:
        config = LLMConfig(
            provider="openai",
            model="x",
            api_key_env="TEST_KEY",
        )
        resp = unittest.mock.MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"choices": []}

        with (
            unittest.mock.patch.dict(os.environ, {"TEST_KEY": "sk-test"}),
            unittest.mock.patch("beadloom.llm_updater.httpx.post", return_value=resp),
            pytest.raises(LLMError, match="empty response"),
        ):
            call_llm(config, "test")


class TestAutoUpdateDoc:
    def test_reads_doc_and_calls_llm(self, tmp_path: Path) -> None:
        doc = tmp_path / "spec.md"
        doc.write_text("# Old Spec\n\nOld content.\n")

        config = LLMConfig(
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            api_key_env="TEST_KEY",
        )

        with (
            unittest.mock.patch.dict(os.environ, {"TEST_KEY": "sk-test"}),
            unittest.mock.patch(
                "beadloom.llm_updater.httpx.post",
                return_value=_mock_anthropic_response("# Updated Spec\n\nNew content.\n"),
            ),
        ):
            result = auto_update_doc(
                config,
                doc,
                [{"code_path": "src/api.py", "content": "def new(): pass"}],
                context_summary="Context here.",
            )

        assert "Updated Spec" in result

    def test_missing_doc_raises(self, tmp_path: Path) -> None:
        config = LLMConfig(
            provider="anthropic",
            model="x",
            api_key_env="TEST_KEY",
        )
        with pytest.raises(FileNotFoundError):
            auto_update_doc(
                config,
                tmp_path / "nonexistent.md",
                [{"code_path": "x.py", "content": "x"}],
            )


class TestCallLLMRequestPayload:
    """Verify that the correct request payload is sent to each provider."""

    def test_anthropic_payload_structure(self) -> None:
        config = LLMConfig(
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            api_key_env="TEST_KEY",
            max_tokens=1024,
        )

        with (
            unittest.mock.patch.dict(os.environ, {"TEST_KEY": "sk-test"}),
            unittest.mock.patch(
                "beadloom.llm_updater.httpx.post",
                return_value=_mock_anthropic_response("ok"),
            ) as mock_post,
        ):
            call_llm(config, "my prompt")

        payload = mock_post.call_args[1]["json"]
        assert payload["model"] == "claude-sonnet-4-20250514"
        assert payload["max_tokens"] == 1024
        assert payload["messages"] == [{"role": "user", "content": "my prompt"}]
        assert "system" in payload

    def test_openai_payload_structure(self) -> None:
        config = LLMConfig(
            provider="openai",
            model="gpt-4o",
            api_key_env="TEST_KEY",
            max_tokens=2048,
        )

        with (
            unittest.mock.patch.dict(os.environ, {"TEST_KEY": "sk-test"}),
            unittest.mock.patch(
                "beadloom.llm_updater.httpx.post",
                return_value=_mock_openai_response("ok"),
            ) as mock_post,
        ):
            call_llm(config, "my prompt")

        payload = mock_post.call_args[1]["json"]
        assert payload["model"] == "gpt-4o"
        assert payload["max_tokens"] == 2048
        assert len(payload["messages"]) == 2
        assert payload["messages"][0]["role"] == "system"
        assert payload["messages"][1] == {"role": "user", "content": "my prompt"}
