import json
from urllib import request

from ocla.cli import main as cli_main


def add_mapping(wiremock_url: str, mapping: dict) -> None:
    data = json.dumps(mapping).encode()
    req = request.Request(
        wiremock_url + "/__admin/mappings",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req):
        pass


def test_cli_simple_reply(wiremock_server, capsys):
    mapping = {
        "request": {"method": "POST", "url": "/api/chat"},
        "response": {
            "status": 200,
            "jsonBody": {"message": {"role": "assistant", "content": "pong"}},
        },
    }
    add_mapping(wiremock_server, mapping)

    cli_main(["-m", "test", "--session", "simple", "ping"])
    captured = capsys.readouterr()
    assert captured.out.strip() == "pong"


def test_cli_tool_called(monkeypatch, wiremock_server, capsys):
    first = {
        "request": {"method": "POST", "url": "/api/chat"},
        "response": {
            "status": 200,
            "jsonBody": {
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {"function": {"name": "ls", "arguments": "{}"}}
                    ],
                }
            },
        },
    }

    second = {
        "request": {"method": "POST", "url": "/api/chat"},
        "response": {
            "status": 200,
            "jsonBody": {"message": {"role": "assistant", "content": "done"}},
        },
    }

    add_mapping(wiremock_server, first)
    add_mapping(wiremock_server, second)

    monkeypatch.setattr("ocla.cli._confirm_tool", lambda call: True)
    cli_main(["-m", "test", "--session", "tool", "list"])
    captured = capsys.readouterr()
    assert captured.out.strip() == "done"

