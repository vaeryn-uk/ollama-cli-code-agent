import argparse
import logging
import os
import dataclasses
import json
from typing import Optional, Callable

_have_logged_invalid_config = False
_cli_values: dict[str, str] = {}


@dataclasses.dataclass
class ConfigVar:
    name: str
    description: str
    env: Optional[str] = None
    config_file_property: Optional[str] = None
    default: Optional[str] = None
    validator_fn: Optional[Callable[[Optional[str]], str]] = None
    normalizer: Optional[Callable[[str], str]] = None
    allowed_values: Optional[dict[str, str]] = None
    cli: Optional[tuple[str, ...]] = None

    def get(self) -> str:
        global _have_logged_invalid_config

        value = None

        if self.name in _cli_values:
            value = _cli_values[self.name]
        elif self.env and os.environ.get(self.env):
            value = os.environ.get(self.env)
        elif self.config_file_property:
            try:
                with open(CONFIG_FILE.get(), "r", encoding="utf-8") as f:
                    data = json.load(f)
                value = str(data.get(self.config_file_property, self.default))
            except (json.JSONDecodeError, TypeError):
                if not _have_logged_invalid_config:
                    _have_logged_invalid_config = True
                    logging.warning(f"Config file {CONFIG_FILE.get()} not valid JSON")
            except FileNotFoundError:
                value = self.default
        else:
            value = self.default

        if value and self.normalizer:
            value = self.normalizer(value)

        return value

    def validate(self) -> Optional[str]:
        if self.validator_fn:
            return self.validator_fn(self.get())

        if self.allowed_values:
            if self.get() not in self.allowed_values.keys():
                return f"must be one of: {', '.join(self.allowed_values.keys())}"

        return None

    def is_valid(self) -> bool:
        return self.validate() is None


CONFIG_VARS: dict[str, ConfigVar] = {}


def add_cli_args(parser: argparse.ArgumentParser) -> None:
    """Register CLI arguments for all config variables that define them."""
    for var in CONFIG_VARS.values():
        if var.cli:
            parser.add_argument(
                *var.cli,
                dest=var.name,
                help=var.description,
                default=argparse.SUPPRESS,
                type=(
                    (lambda x, v=var: x if v.normalizer is None else v.normalizer(x))
                ),
                choices=list(var.allowed_values.keys()) if var.allowed_values else None,
            )


def apply_cli_args(args: argparse.Namespace) -> None:
    """Apply overrides from *args* returned by argparse."""
    overrides: dict[str, str] = {}
    for var in CONFIG_VARS.values():
        if var.cli and hasattr(args, var.name):
            overrides[var.name] = getattr(args, var.name)

    _cli_values.update(overrides)


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
        validator_fn=lambda x: (
            "" if x.isdigit() and int(x) > 0 else "must be a positive integer"
        ),
    )
)

MODEL = _var(
    ConfigVar(
        name="model",
        description="Model name",
        env="OCLA_MODEL",
        config_file_property="model",
        default="qwen3",
        cli=("-m", "--model"),
    )
)

LOG_LEVEL = _var(
    ConfigVar(
        name="log_level",
        description="Log level",
        env="OCLA_LOG_LEVEL",
        config_file_property="logLevel",
        default="WARNING",
        allowed_values={
            "CRITICAL": "",
            "ERROR": "",
            "WARNING": "",
            "INFO": "",
            "DEBUG": "",
        },
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

TOOL_PERMISSION_MODE_DEFAULT = "DEFAULT"
TOOL_PERMISSION_MODE_ALWAYS_ASK = "ALWAYS_ASK"
TOOL_PERMISSION_MODE_ALWAYS_ALLOW = "ALWAYS_ALLOW"
VALID_TOOL_PERMISSION_MODES = [
    TOOL_PERMISSION_MODE_DEFAULT,
    TOOL_PERMISSION_MODE_ALWAYS_ASK,
    TOOL_PERMISSION_MODE_ALWAYS_ALLOW,
]

TOOL_PERMISSION_MODE = _var(
    ConfigVar(
        name="tool_permission_mode",
        description="How tools request permission to run",
        env="OCLA_TOOL_PERMISSION_MODE",
        config_file_property="toolPermissionMode",
        default=TOOL_PERMISSION_MODE_DEFAULT,
        allowed_values={
            TOOL_PERMISSION_MODE_DEFAULT: "Ask for permission for non-trivial tools",
            TOOL_PERMISSION_MODE_ALWAYS_ASK: "Always ask for permission for all tools",
            TOOL_PERMISSION_MODE_ALWAYS_ALLOW: "Always run any tool; use with caution",
        },
    )
)

THINKING_DISABLED = "DISABLED"
THINKING_HIDDEN = "HIDDEN"
THINKING_ENABLED = "ENABLED"

THINKING = _var(
    ConfigVar(
        name="thinking",
        description="How to display assistant thinking output",
        env="OCLA_THINKING",
        config_file_property="displayThinking",
        default=THINKING_ENABLED,
        normalizer=lambda x: x.upper(),
        allowed_values={
            THINKING_DISABLED: "The model will not think and nothing is shown",
            THINKING_HIDDEN: "The model will think, but thinking output is not displayed",
            THINKING_ENABLED: "The model will think and ocla prints this output",
        },
        cli=("-t", "--thinking"),
    )
)

PROJECT_CONTEXT_FILE = _var(
    ConfigVar(
        name="project_context_file",
        description="the relative path to a file that gives ocla more context about your project (case-insensitive)",
        env="OCLA_PROJECT_CONTEXT_FILE",
        config_file_property="projectContextFiles",
        default="AGENTS.md",
    )
)


SESSION_STORAGE_MODE_PLAIN = "PLAIN"
SESSION_STORAGE_MODE_COMPRESS = "COMPRESS"
# SESSION_STORAGE_MODE_ENCRYPT = "ENCRYPT" # TODO: Implement in the future?
VALID_SESSION_STORAGE_MODE_MODES = [
    SESSION_STORAGE_MODE_PLAIN,
    SESSION_STORAGE_MODE_COMPRESS,
    # SESSION_STORAGE_MODE_ENCRYPT,
]


SESSION_STORAGE_MODE = _var(
    ConfigVar(
        name="session_storage_mode",
        description="how we store session data on disk",
        env="OCLA_SESSION_STORAGE_MODE",
        config_file_property="sessionStorageMode",
        default=SESSION_STORAGE_MODE_COMPRESS,
        allowed_values={
            SESSION_STORAGE_MODE_PLAIN: "Plain text (JSON). Can get large.",
            SESSION_STORAGE_MODE_COMPRESS: "Compressed via gzip",
        },
    )
)


PROMPT_MODE = _var(
    ConfigVar(
        name="prompt_mode",
        description="How you want to interact with the assistant",
        env="OCLA_SESSION_STORAGE_MODE",
        config_file_property="promptMode",
        default="INTERACTIVE",
        cli=("-p", "--prompt-mode"),
        normalizer=lambda x: x.upper(),
        allowed_values={
            "ONESHOT": "The program quits after a single prompt",
            "INTERACTIVE": "You issue prompts until quit",
        },
    )
)
