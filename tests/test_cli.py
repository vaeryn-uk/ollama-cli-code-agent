from io import StringIO
import sys
from .helpers import mock_ollama_responses, content, tool_call, assert_scenario_completed
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
        tool_call({"function": {"name": "ls", "arguments": {}}}),
        content("done")
    )

    monkeypatch.setattr(sys, "stdin", StringIO("done"))
    monkeypatch.setattr("ocla.cli._confirm_tool", lambda call: True)

    cli_main([])
    captured = capsys.readouterr()
    assert captured.out.strip() == "done"

    assert_scenario_completed(scenario)

