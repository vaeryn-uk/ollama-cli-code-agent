import json
import logging
import os
import time
from datetime import timezone
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from .config import SESSION_DIR, PROJECT_CONTEXT_FILE

from datetime import datetime
from pathlib import Path

import ollama
from ocla.state import load_state, save_state

DEFAULT_SYSTEM_PROMPT = """
You are a software development agent named OCLA, helping users understand, write and debug code.
You are being invoked inside a directory that contains a software project that the user
is working on. You can only operate within this directory and attempt to use tools outside of this
space will be rejected. You will be asked to operate within their project and assist them as a
collaborator in the development process alongside them.
"""


@dataclass
class Session:
    name: str
    path: str = field(init=False)
    meta_path: str = field(init=False)
    messages: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        # file locations
        self.path = os.path.join(SESSION_DIR.get(), f"{self.name}.session")
        self.meta_path = os.path.join(SESSION_DIR.get(), f"{self.name}.meta")

        # (1) load messages if the session file exists
        if os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8") as f:
                self.messages = json.load(f).get("messages", [])

        # (2) load or create metadata
        now_iso = datetime.now(timezone.utc).isoformat()
        if os.path.exists(self.meta_path):
            with open(self.meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            self.created = meta.get("created", now_iso)
            self.used = meta.get("used", now_iso)
        else:
            self.created = now_iso
            self.used = now_iso
            self._write_meta()  # create the .meta file immediately

        if len(self.messages) == 0:
            self.add({"role": "system", "content": DEFAULT_SYSTEM_PROMPT})

            try:
                content = Path(PROJECT_CONTEXT_FILE.get()).read_text()
                if content:
                    self.add(
                        {
                            "role": "system",
                            "content": f"Additional project context:\n{content}",
                        }
                    )
                else:
                    logging.debug(
                        f"project context file {PROJECT_CONTEXT_FILE.get()} was empty"
                    )
            except Exception as e:
                logging.debug(
                    f"project context file {PROJECT_CONTEXT_FILE.get()} could not be read"
                )

    def _write_meta(self) -> None:
        os.makedirs(SESSION_DIR.get(), exist_ok=True)
        with open(self.meta_path, "w", encoding="utf-8") as f:
            json.dump({"created": self.created, "used": self.used}, f, indent=2)

    def save(self) -> None:
        """Persist messages and bump 'used' timestamp."""
        os.makedirs(SESSION_DIR.get(), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump({"messages": self.messages}, f, indent=2)

        self.used = datetime.now(timezone.utc).isoformat()
        self._write_meta()

    def add(self, message: Dict[str, Any]) -> None:
        """Append a message and immediately save the session."""
        if isinstance(message, ollama.Message):
            message = message.model_dump(mode="python", by_alias=True)

        self.messages.append(message)
        self.save()


def _ensure_dirs() -> None:
    os.makedirs(SESSION_DIR.get(), exist_ok=True)


@dataclass
class SessionInfo:
    name: str
    created: datetime
    used: datetime


def list_sessions() -> List[SessionInfo]:
    _ensure_dirs()

    infos = []

    for f in os.listdir(SESSION_DIR.get() or "."):
        if not f.endswith(".meta"):
            continue

        meta_path = os.path.join(SESSION_DIR.get(), f)

        # --- load timestamps from the .meta file ------------------------------
        with open(meta_path, "r", encoding="utf-8") as fp:
            meta = json.load(fp)

        # ISO-8601 strings → aware datetimes (UTC)
        created = datetime.fromisoformat(meta["created"].replace("Z", "+00:00"))
        used = datetime.fromisoformat(meta["used"].replace("Z", "+00:00"))

        infos.append(
            SessionInfo(
                name=f.removesuffix(".meta"),
                created=created,
                used=used,
            )
        )

    return sorted(infos, key=lambda s: [s.used], reverse=True)


def session_exists(name: str) -> bool:
    return any([x for x in list_sessions() if x.name == name])


def get_current_session_name() -> Optional[str]:
    return load_state().current_session


def set_current_session_name(name: str) -> None:
    state = load_state()
    state.current_session = name
    save_state(state)


def generate_session_name() -> str:
    return datetime.now().strftime("%Y%m%d%H%M%S")
