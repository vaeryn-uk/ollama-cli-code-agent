import json
import os
import sys
import time
import types
import urllib.request

import pytest


@pytest.fixture(scope="session")
def wiremock_server():
    base_url = os.environ.get("WIREMOCK_URL", "http://localhost:8080")
    # wait for container to be ready
    for _ in range(30):
        try:
            urllib.request.urlopen(base_url + "/__admin/mappings")
            break
        except Exception:
            time.sleep(1)
    return base_url


@pytest.fixture(autouse=True)
def fake_ollama(monkeypatch, wiremock_server):
    base_url = wiremock_server

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

