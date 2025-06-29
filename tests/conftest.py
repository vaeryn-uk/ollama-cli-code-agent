import os
import time
import urllib.request

import pytest

WIREMOCK_BASE_URL = os.environ.get("WIREMOCK_BASE_URL", "http://localhost:8080")
os.environ["OLLAMA_HOST"] = WIREMOCK_BASE_URL


@pytest.fixture(scope="session", autouse=True)
def _wiremock_ready():
    # wait for container to be ready
    ok = False
    for _ in range(5):
        try:
            urllib.request.urlopen(WIREMOCK_BASE_URL + "/__admin/mappings")
            ok = True
            break
        except Exception:
            time.sleep(1)

    if not ok:
        raise RuntimeError("Wiremock unavailable")

    yield


def _reset_wiremock():
    """Remove all stubs and recorded requests."""
    # DELETE /__admin/mappings clears mappings
    req = urllib.request.Request(
        f"{WIREMOCK_BASE_URL}/__admin/mappings", method="DELETE"
    )
    urllib.request.urlopen(req)

    urllib.request.urlopen(
        urllib.request.Request(
            f"{WIREMOCK_BASE_URL}/__admin/scenarios/reset", method="POST"
        )
    )

    urllib.request.urlopen(
        urllib.request.Request(f"{WIREMOCK_BASE_URL}/__admin/requests", method="DELETE")
    )


@pytest.fixture(autouse=True)
def _wiremock_reset(_wiremock_ready):
    """Clear WireMock before each test runs."""
    _reset_wiremock()
    yield
