from typing import Optional
import os
import dataclasses
import json
from .config import STATE_FILE


@dataclasses.dataclass
class State:
    current_session: Optional[str] = None


def load_state() -> State:
    try:
        with open(STATE_FILE.get(), "r", encoding="utf-8") as f:
            data = json.load(f)
        return State(**data)
    except (FileNotFoundError, json.JSONDecodeError, TypeError):
        return State()


def save_state(state: State) -> None:
    os.makedirs(os.path.dirname(STATE_FILE.get()), exist_ok=True)
    data = {k: v for k, v in state.__dict__.items() if v not in (None, "", [], {}, ())}
    with open(STATE_FILE.get(), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
