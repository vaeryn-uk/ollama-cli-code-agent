from io import StringIO
import sys
from .helpers import (
    mock_ollama_responses,
    content,
    tool_call,
    assert_scenario_completed,
    permit_all_tool_calls,
)
from ocla.cli import main as cli_main


def test_cli_simple_reply(monkeypatch, capsys):
    scenario = mock_ollama_responses(content("pong"))

    monkeypatch.setattr(sys, "stdin", StringIO("ping"))

    cli_main([])
    captured = capsys.readouterr()
    assert captured.out.strip() == "pong"

    assert_scenario_completed(scenario)


def test_cli_tool_called(monkeypatch, capsys):
    scenario = mock_ollama_responses(
        tool_call({"function": {"name": "list_files", "arguments": {}}}),
        content("done"),
    )

    monkeypatch.setattr(sys, "stdin", StringIO("done"))
    permit_all_tool_calls(monkeypatch)

    cli_main([])
    captured = capsys.readouterr()
    assert captured.out.strip() == "done"

    assert_scenario_completed(scenario)
