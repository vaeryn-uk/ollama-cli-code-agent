import json
import os
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from datetime import datetime

import ollama
from ocla.state import load_state, save_state

SESSION_DIR = os.path.join(".ocla", "sessions")


@dataclass
class Session:
    name: str
    path: str = field(init=False)
    messages: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        if not self.name.endswith(".session"):
            self.name += ".session"
        self.path = os.path.join(SESSION_DIR, self.name)
        if os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.messages = data.get("messages", [])

    def save(self):
        os.makedirs(SESSION_DIR, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump({"messages": self.messages}, f, indent=2)

    def add(self, message: Dict[str, Any]):
        if isinstance(message, ollama.Message):
            message = message.model_dump(mode="python", by_alias=True)

        self.messages.append(message)


def _ensure_dirs() -> None:
    os.makedirs(SESSION_DIR, exist_ok=True)


def list_sessions() -> List[str]:
    _ensure_dirs()
    return sorted(
        [f.removesuffix(".session") for f in os.listdir(SESSION_DIR) if f.endswith(".session")]
    )


def get_current_session_name() -> Optional[str]:
    return load_state().current_session


def set_current_session_name(name: str) -> None:
    state = load_state()
    state.current_session = name
    save_state(state)


def generate_session_name() -> str:
    return datetime.now().strftime("%Y%m%d%H%M%S") + ".session"
