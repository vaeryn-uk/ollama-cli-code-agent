import os
from ocla.session import Session, list_sessions


def test_session_token_count(monkeypatch, tmp_path):
    monkeypatch.setenv("OCLA_SESSION_DIR", str(tmp_path))
    s = Session("t1")
    s.add({"role": "user", "content": "hello world"})

    # reload session to ensure persistence
    s2 = Session("t1")
    assert s2.token_count() > 0

    infos = list_sessions()
    assert infos[0].tokens == s2.token_count()
