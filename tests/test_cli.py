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
