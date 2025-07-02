from io import StringIO
import os
import sys
import logging
import pytest

from ocla.config import PROMPT_MODE
from .helpers import (
    mock_ollama_responses,
    content,
    tool_call,
    assert_scenario_completed,
    permit_all_tool_calls,
)
from .conftest import WIREMOCK_BASE_URL
import ocla.cli
from ocla.cli import main as cli_main


def test_cli_simple_reply(monkeypatch, capsys):
    scenario = mock_ollama_responses(content("pong"))

    monkeypatch.setenv(PROMPT_MODE.env, "oneshot")
    monkeypatch.setattr(sys, "stdin", StringIO("ping"))

    cli_main([])
    captured = capsys.readouterr()
    lines = captured.out.strip().splitlines()
    assert lines[0] == "pong"

    assert_scenario_completed(scenario)


def test_cli_tool_called(monkeypatch, capsys):
    scenario = mock_ollama_responses(
        tool_call({"function": {"name": "list_files", "arguments": {}}}),
        content("done"),
    )

    monkeypatch.setattr(sys, "stdin", StringIO("done"))
    monkeypatch.setenv(PROMPT_MODE.env, "oneshot")
    permit_all_tool_calls(monkeypatch)

    cli_main([])
    captured = capsys.readouterr()
    lines = captured.out.strip().splitlines()
    assert "done" in lines

    assert_scenario_completed(scenario)


def test_ocla_ollama_host_overrides(monkeypatch, capsys):
    scenario = mock_ollama_responses(content("pong"))

    monkeypatch.setenv("OLLAMA_HOST", "http://ignored:1234")
    monkeypatch.setenv("OCLA_OLLAMA_HOST", WIREMOCK_BASE_URL)
    monkeypatch.setenv(PROMPT_MODE.env, "oneshot")

    monkeypatch.setattr(sys, "stdin", StringIO("ping"))

    cli_main([])

    assert os.environ["OLLAMA_HOST"] == WIREMOCK_BASE_URL

    assert_scenario_completed(scenario)


def test_thinking_cli_arg(monkeypatch):
    scenario = mock_ollama_responses(content("pong"))

    captured = {}
    orig_chat = ocla.cli.ollama.chat

    def fake_chat(*args, **kwargs):
        captured["think"] = kwargs.get("think")
        return orig_chat(*args, **kwargs)

    monkeypatch.setattr(ocla.cli.ollama, "chat", fake_chat)
    monkeypatch.setenv(PROMPT_MODE.env, "oneshot")
    monkeypatch.setattr(sys, "stdin", StringIO("ping"))

    cli_main(["--thinking", "DISABLED"])

    assert captured.get("think") is False

    assert_scenario_completed(scenario)


def test_missing_model(monkeypatch, capsys):
    def fake_show(model):
        raise ocla.cli.ResponseError("not found", status_code=404)

    monkeypatch.setattr(ocla.cli.ollama, "show", fake_show)
    monkeypatch.setenv(PROMPT_MODE.env, "oneshot")
    monkeypatch.setattr(sys, "stdin", StringIO("ping"))

    with pytest.raises(SystemExit):
        cli_main([])

    captured = capsys.readouterr()
    assert "does not have the requested model" in captured.out
