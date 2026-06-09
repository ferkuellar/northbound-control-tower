from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from ai.providers.claude import ClaudeProvider


def _make_provider(api_key: str | None = "test-key") -> ClaudeProvider:
    provider = ClaudeProvider.__new__(ClaudeProvider)
    provider.model_name = "claude-sonnet-4-6"
    provider.api_key = api_key
    return provider


def _make_response(*texts: str) -> SimpleNamespace:
    blocks = [SimpleNamespace(type="text", text=t) for t in texts]
    return SimpleNamespace(content=blocks)


# ── system message ─────────────────────────────────────────────────────────────

def test_system_message_is_imported_system_prompt() -> None:
    from ai.prompts import SYSTEM_PROMPT
    provider = _make_provider()
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _make_response("{}")

    with patch("ai.providers.claude.anthropic.Anthropic", return_value=mock_client):
        provider.generate_analysis("test prompt", max_tokens=100, temperature=0.2)

    system = mock_client.messages.create.call_args.kwargs["system"]
    assert system == SYSTEM_PROMPT, "ClaudeProvider must use SYSTEM_PROMPT from ai.prompts, not a hardcoded string"


def test_system_message_is_sent() -> None:
    provider = _make_provider()
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _make_response("{}")

    with patch("ai.providers.claude.anthropic.Anthropic", return_value=mock_client):
        provider.generate_analysis("test prompt", max_tokens=100, temperature=0.2)

    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert "system" in call_kwargs


def test_system_message_requires_json_only() -> None:
    provider = _make_provider()
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _make_response("{}")

    with patch("ai.providers.claude.anthropic.Anthropic", return_value=mock_client):
        provider.generate_analysis("test prompt", max_tokens=100, temperature=0.2)

    system = mock_client.messages.create.call_args.kwargs["system"]
    assert "valid JSON only" in system
    assert "no markdown fences" in system
    assert "no preamble" in system
    assert "parseable by json.loads()" in system
    assert "Never invent data" in system


# ── parameters preserved ───────────────────────────────────────────────────────

def test_model_max_tokens_temperature_passed() -> None:
    provider = _make_provider()
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _make_response("{}")

    with patch("ai.providers.claude.anthropic.Anthropic", return_value=mock_client):
        provider.generate_analysis("my prompt", max_tokens=512, temperature=0.5)

    kw = mock_client.messages.create.call_args.kwargs
    assert kw["model"] == "claude-sonnet-4-6"
    assert kw["max_tokens"] == 512
    assert kw["temperature"] == 0.5
    assert kw["messages"] == [{"role": "user", "content": "my prompt"}]


# ── text extraction ────────────────────────────────────────────────────────────

def test_single_text_block_returned() -> None:
    provider = _make_provider()
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _make_response('{"key": "value"}')

    with patch("ai.providers.claude.anthropic.Anthropic", return_value=mock_client):
        result = provider.generate_analysis("prompt", max_tokens=100, temperature=0.2)

    assert result == '{"key": "value"}'


def test_multiple_text_blocks_joined_with_newline() -> None:
    provider = _make_provider()
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _make_response('{"a": 1}', '{"b": 2}')

    with patch("ai.providers.claude.anthropic.Anthropic", return_value=mock_client):
        result = provider.generate_analysis("prompt", max_tokens=100, temperature=0.2)

    assert result == '{"a": 1}\n{"b": 2}'


def test_non_text_blocks_ignored() -> None:
    provider = _make_provider()
    mock_client = MagicMock()
    non_text = SimpleNamespace(type="tool_use", id="tu_1")
    text = SimpleNamespace(type="text", text='{"result": true}')
    mock_client.messages.create.return_value = SimpleNamespace(content=[non_text, text])

    with patch("ai.providers.claude.anthropic.Anthropic", return_value=mock_client):
        result = provider.generate_analysis("prompt", max_tokens=100, temperature=0.2)

    assert result == '{"result": true}'


# ── missing api key ────────────────────────────────────────────────────────────

def test_missing_api_key_raises_value_error() -> None:
    provider = _make_provider(api_key=None)

    with pytest.raises(ValueError, match="provider key is not configured"):
        provider.generate_analysis("prompt", max_tokens=100, temperature=0.2)


def test_missing_api_key_does_not_call_anthropic() -> None:
    provider = _make_provider(api_key=None)

    with patch("ai.providers.claude.anthropic.Anthropic") as mock_anthropic:
        with pytest.raises(ValueError):
            provider.generate_analysis("prompt", max_tokens=100, temperature=0.2)

    mock_anthropic.assert_not_called()
