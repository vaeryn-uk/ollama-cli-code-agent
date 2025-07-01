import os
import pytest
from ocla.session import Session


def _roundtrip(monkeypatch, tmp_path, write_mode, read_mode=None):
    """Write a session using *write_mode* then read it back in *read_mode*."""
    monkeypatch.setenv("OCLA_SESSION_DIR", str(tmp_path))
    monkeypatch.setenv("OCLA_SESSION_STORAGE_MODE", write_mode)

    s = Session("test")
    s.add({"role": "user", "content": "hello"})

    if read_mode:
        monkeypatch.setenv("OCLA_SESSION_STORAGE_MODE", read_mode)

    s2 = Session("test")
    assert s2.messages[-1]["content"] == "hello"


def test_session_plain(monkeypatch, tmp_path):
    _roundtrip(monkeypatch, tmp_path, "PLAIN")


def test_session_compress(monkeypatch, tmp_path):
    _roundtrip(monkeypatch, tmp_path, "COMPRESS")


def test_mode_switch(monkeypatch, tmp_path):
    """Sessions encoded in one mode can be read after changing the config."""
    _roundtrip(monkeypatch, tmp_path, "PLAIN", read_mode="COMPRESS")
