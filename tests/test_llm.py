import json
from unittest.mock import MagicMock, patch

import pytest

from cgm_llm import call_llm, extract_json


def test_extract_json_plain():
    assert extract_json('{"score": 4}') == {"score": 4}


def test_extract_json_fenced():
    text = 'Here you go:\n```json\n{"score": 3, "evidence_ids": [1, 2]}\n```'
    assert extract_json(text) == {"score": 3, "evidence_ids": [1, 2]}


def test_extract_json_embedded_prose():
    text = 'Reasoning first. {"score": 5, "rationale": "strong"} done.'
    assert extract_json(text) == {"score": 5, "rationale": "strong"}


def test_extract_json_failure_raises():
    with pytest.raises(ValueError):
        extract_json("no json here")


@patch("cgm_llm.anthropic.Anthropic")
def test_call_llm_passes_temperature_zero(mock_cls):
    client = MagicMock()
    mock_cls.return_value = client
    client.messages.create.return_value = MagicMock(
        content=[MagicMock(text='{"ok": true}')]
    )
    out = call_llm("claude-opus-4-5", "system prompt", "user prompt")
    assert out == '{"ok": true}'
    kwargs = client.messages.create.call_args.kwargs
    assert kwargs["temperature"] == 0
    assert kwargs["model"] == "claude-opus-4-5"


@patch("cgm_llm.time.sleep")
@patch("cgm_llm.anthropic.Anthropic")
def test_call_llm_retries_then_succeeds(mock_cls, _sleep):
    client = MagicMock()
    mock_cls.return_value = client
    client.messages.create.side_effect = [
        Exception("overloaded"),
        MagicMock(content=[MagicMock(text="ok")], stop_reason="end_turn"),
    ]
    assert call_llm("m", "s", "u") == "ok"
    assert client.messages.create.call_count == 2


@patch("cgm_llm.anthropic.Anthropic")
def test_call_llm_raises_on_truncation(mock_cls):
    client = MagicMock()
    mock_cls.return_value = client
    client.messages.create.return_value = MagicMock(
        content=[MagicMock(text='{"cut off')], stop_reason="max_tokens"
    )
    with pytest.raises(RuntimeError, match="truncated"):
        call_llm("m", "s", "u")
