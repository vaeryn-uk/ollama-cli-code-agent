import os
import pytest
from ocla.session import Session, ProviderMismatchError


def test_provider_mismatch(monkeypatch, tmp_path):
    monkeypatch.setenv("OCLA_SESSION_DIR", str(tmp_path))
    # create session with default provider 'ollama'
    monkeypatch.setenv("OCLA_PROVIDER", "ollama")
    s = Session("p1")
    s.add({"role": "user", "content": "hi"})

    # now switch provider and expect error when loading
    monkeypatch.setenv("OCLA_PROVIDER", "openai")
    with pytest.raises(ProviderMismatchError):
        Session("p1")

