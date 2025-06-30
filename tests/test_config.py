import json
import os
from ocla.config import load_config, save_config, CONFIG_FILE, Config


def test_config_defaults(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg = load_config()
    assert cfg.model == "qwen3"
    assert cfg.context_window == 8192 * 2
    assert cfg.log_level == "DEBUG"


def test_config_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump({"model": "llama", "context_window": 1234, "log_level": "INFO"}, f)

    cfg = load_config()
    assert cfg.model == "llama"
    assert cfg.context_window == 1234
    assert cfg.log_level == "INFO"


def test_config_env_overrides(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump({"model": "llama", "context_window": 1234, "log_level": "INFO"}, f)

    monkeypatch.setenv("OCLA_MODEL", "mistral")
    monkeypatch.setenv("OCLA_CONTEXT_WINDOW", "2048")
    monkeypatch.setenv("OCLA_LOG_LEVEL", "WARNING")

    cfg = load_config()
    assert cfg.model == "mistral"
    assert cfg.context_window == 2048
    assert cfg.log_level == "WARNING"
