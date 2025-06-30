import logging
import os
import dataclasses
import json
from typing import Optional, Callable


@dataclasses.dataclass
class ConfigVar:
    name: str
    description: str
    env: Optional[str] = None
    config_file_property: Optional[str] = None
    default: Optional[str] = None
    validator_fn: Optional[Callable[[Optional[str]], str]] = None

    def get(self) -> str:
        if self.env and os.environ.get(self.env):
            return os.environ.get(self.env)

        if self.config_file_property:
            try:
                with open(CONFIG_FILE.get(), "r", encoding="utf-8") as f:
                    data = json.load(f)
                return str(data.get(self.config_file_property, self.default))
            except (json.JSONDecodeError, TypeError):
                logging.warning(f"Config file {CONFIG_FILE.get()} not valid JSON")
            except FileNotFoundError:
                pass

        return self.default


CONFIG_VARS: dict[str, ConfigVar] = {}


def _var(var: ConfigVar) -> ConfigVar:
    CONFIG_VARS[var.name] = var
    return var


CONFIG_FILE = _var(
    ConfigVar(
        name="config_file",
        description="Path to the config file",
        env="OCLA_CONFIG_FILE",
        config_file_property=None,
        default=os.path.join(".", ".ocla", "config.json"),
    )
)

CONTEXT_WINDOW = _var(
    ConfigVar(
        name="context_window",
        description="Context window size in tokens",
        env="OCLA_CONTEXT_WINDOW",
        config_file_property="contextWindow",
        default=str(8192 * 2),
        validator_fn=lambda x: "" if x.isdigit() else "must be a positive integer",
    )
)

MODEL = _var(
    ConfigVar(
        name="model",
        description="Model name",
        env="OCLA_MODEL",
        config_file_property="model",
        default="qwen3",
    )
)

LOG_LEVEL = _var(
    ConfigVar(
        name="log_level",
        description="Log level",
        env="OCLA_LOG_LEVEL",
        config_file_property="logLevel",
        default="WARNING",
        validator_fn=lambda x: (
            ""
            if x in logging.getLevelNamesMapping().keys()
            else "must be one of: " + str(logging.getLevelNamesMapping().keys())
        ),
    )
)

SESSION_DIR = _var(
    ConfigVar(
        name="session_dir",
        description="Path to the session directory",
        env="OCLA_SESSION_DIR",
        config_file_property="sessionDir",
        default=os.path.join(".", ".ocla", "sessions"),
    )
)

STATE_FILE = _var(
    ConfigVar(
        name="state_file",
        description="Path to the state file",
        env="OCLA_STATE_FILE",
        config_file_property="stateFile",
        default=os.path.join(".", ".ocla", "state.json"),
    )
)
