import json
import sys
import types
import urllib.request
import pytest

wiremock = pytest.importorskip("wiremock")
from wiremock.server import WireMockServer
from wiremock.resources.mappings import Mapping, MappingRequest, MappingResponse
from wiremock.resources.mappings.models import HttpMethods


@pytest.fixture

def wiremock_server():
    server = WireMockServer(port=0)
    server.start()
    try:
        yield server
    finally:
        server.stop()


@pytest.fixture(autouse=True)
def fake_ollama(monkeypatch, wiremock_server):
    base_url = f"http://localhost:{wiremock_server.port}"

    def chat(model: str, messages, tools=None):
        payload = {"model": model, "messages": messages}
        if tools:
            payload["tools"] = tools
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            base_url + "/api/chat",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())

    module = types.ModuleType("ollama")
    module.chat = chat

    class Message:
        pass

    module.Message = Message
    monkeypatch.setitem(sys.modules, "ollama", module)
    yield module
    monkeypatch.setitem(sys.modules, "ollama", None)

