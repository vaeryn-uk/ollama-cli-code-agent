import json
import typing
import uuid
from urllib.request import Request, urlopen

import pytest

from .conftest import WIREMOCK_BASE_URL

SCENARIO_COMPLETE_STATE = "Completed"


def content(text: str) -> dict:
    return {"message": {"role": "assistant", "content": text}}


def tool_call(call: dict) -> dict:
    return {"message": {"role": "assistant", "content": "", "tool_calls": [call]}}


def permit_all_tool_calls(monkeypatch, allow: bool = True):
    monkeypatch.setattr("ocla.cli._confirm_tool", lambda call: allow)


def assert_scenario_completed(scenario: str):
    req = Request(f"{WIREMOCK_BASE_URL.rstrip('/')}/__admin/scenarios")
    with urlopen(req) as resp:
        data = json.load(resp)

    found = None
    for sc in data.get("scenarios", []):
        if sc["name"] == scenario:
            found = sc["state"]

    if found is None:
        pytest.fail(f"Scenario '{scenario}' not found in WireMock")
    elif found != SCENARIO_COMPLETE_STATE:
        pytest.fail(
            f"Scenario '{scenario}' ended in state '{found}', not '{SCENARIO_COMPLETE_STATE}'"
        )


def mock_ollama_responses(
    *bodies: dict,
) -> str:
    """
    Register responses that will be returned in the given order.
    Each call to POST <url_path> advances the scenario state.
    """
    scenario = f"ollama-{uuid.uuid4()}"
    state = "Started"

    for idx, body in enumerate(bodies, 1):
        new_state = SCENARIO_COMPLETE_STATE if idx == len(bodies) else f"step-{idx}"

        mapping: dict[str, typing.Any] = {
            "scenarioName": scenario,
            "requiredScenarioState": state,
            "newScenarioState": new_state,
            "request": {"method": "POST", "urlPath": "/api/chat"},
            "response": {
                "status": 200,
                "jsonBody": body,
                "headers": {"Content-Type": "application/json"},
            },
        }
        state = new_state

        req = Request(
            f"{WIREMOCK_BASE_URL.rstrip('/')}/__admin/mappings",
            data=json.dumps(mapping).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(req):
            pass

    return scenario
