import json
from urllib import request

import pytest

from ocla.session import Session
from ocla.cli import chat_with_tools, _confirm_tool

wiremock = pytest.importorskip("wiremock")
from wiremock.resources.mappings import Mapping, MappingRequest, MappingResponse
from wiremock.resources.mappings.models import HttpMethods


def test_chat_with_tools_simple_reply(wiremock_server):
    mapping = Mapping(
        request=MappingRequest(method=HttpMethods.POST, url="/api/chat"),
        response=MappingResponse(
            status=200,
            json_body={"message": {"role": "assistant", "content": "pong"}}
        ),
    )
    wiremock_server.mappings.create_mapping(mapping)

    session = Session("simple")
    out = chat_with_tools("test", session, "ping")
    assert out == "pong"


def test_chat_with_tools_tool_called(monkeypatch, wiremock_server):
    first = Mapping(
        request=MappingRequest(method=HttpMethods.POST, url="/api/chat"),
        response=MappingResponse(
            status=200,
            json_body={
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {"function": {"name": "ls", "arguments": "{}"}}
                    ],
                }
            },
        ),
    )

    second = Mapping(
        request=MappingRequest(method=HttpMethods.POST, url="/api/chat"),
        response=MappingResponse(
            status=200,
            json_body={"message": {"role": "assistant", "content": "done"}},
        ),
    )

    wiremock_server.mappings.create_mapping(first)
    wiremock_server.mappings.create_mapping(second)

    monkeypatch.setattr("ocla.cli._confirm_tool", lambda call: True)

    session = Session("tool")
    out = chat_with_tools("test", session, "list")
    assert out == "done"

