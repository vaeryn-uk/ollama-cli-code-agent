import os
import dataclasses
import json
from typing import Optional

CONFIG_FILE = os.path.join(".ocla", "config.json")


@dataclasses.dataclass
class Config:
    model: str = "qwen3"
    context_window: int = 8192 * 2
    log_level: str = "DEBUG"


def load_config() -> Config:
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, TypeError):
        data = {}

    config = Config(**data)

    if env_model := os.environ.get("OCLA_MODEL"):
        config.model = env_model

    if env_ctx := os.environ.get("OCLA_CONTEXT_WINDOW"):
        try:
            config.context_window = int(env_ctx)
        except ValueError:
            pass

    if env_level := os.environ.get("OCLA_LOG_LEVEL"):
        config.log_level = env_level

    return config


def save_config(config: Config) -> None:
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    data = {k: v for k, v in dataclasses.asdict(config).items() if v is not None}
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
