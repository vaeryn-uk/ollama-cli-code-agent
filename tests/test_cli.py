from io import StringIO
import sys
import logging
from .helpers import (
    mock_ollama_responses,
    content,
    tool_call,
    assert_scenario_completed,
    permit_all_tool_calls,
)
import ocla.cli
from ocla.cli import main as cli_main


def test_cli_simple_reply(monkeypatch, capsys):
    scenario = mock_ollama_responses(content("pong"))

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
    permit_all_tool_calls(monkeypatch)

    cli_main([])
    captured = capsys.readouterr()
    lines = captured.out.strip().splitlines()
    assert "done" in lines

    assert_scenario_completed(scenario)


def test_context_window_warning(monkeypatch, capsys, caplog):
    scenario = mock_ollama_responses(content("pong"))

    monkeypatch.setattr("ocla.cli._model_context_limit", lambda model: 5)
    monkeypatch.setenv("OCLA_CONTEXT_WINDOW", "10")
    monkeypatch.setattr("ocla.session._estimate_tokens", lambda *a, **k: 1)

    monkeypatch.setattr(sys, "stdin", StringIO("ping"))

    with caplog.at_level(logging.WARNING):
        cli_main([])
    captured = capsys.readouterr()
    assert "exceeds model limit" in caplog.text

    assert_scenario_completed(scenario)


def test_model_cli_arg_overrides_env(monkeypatch, capsys):
    scenario = mock_ollama_responses(content("pong"))

    monkeypatch.setenv("OCLA_MODEL", "env_model")

    captured = {}
    orig_chat = ocla.cli.ollama.chat

    def fake_chat(*args, **kwargs):
        captured["model"] = kwargs.get("model")
        return orig_chat(*args, **kwargs)

    monkeypatch.setattr(ocla.cli.ollama, "chat", fake_chat)

    monkeypatch.setattr(sys, "stdin", StringIO("ping"))

    cli_main(["-m", "cli_model"])

    assert captured.get("model") == "cli_model"

    assert_scenario_completed(scenario)


def test_thinking_cli_arg(monkeypatch):
    scenario = mock_ollama_responses(content("pong"))

    captured = {}
    orig_chat = ocla.cli.ollama.chat

    def fake_chat(*args, **kwargs):
        captured["think"] = kwargs.get("think")
        return orig_chat(*args, **kwargs)

    monkeypatch.setattr(ocla.cli.ollama, "chat", fake_chat)

    monkeypatch.setattr(sys, "stdin", StringIO("ping"))

    cli_main(["--thinking", "DISABLED"])

    assert captured.get("think") is False

    assert_scenario_completed(scenario)
