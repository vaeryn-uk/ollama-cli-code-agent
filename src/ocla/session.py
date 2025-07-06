import functools
import json
import gzip
import logging
import os
import sys
import time

import tiktoken
from datetime import timezone
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from .config import (
    SESSION_DIR,
    PROJECT_CONTEXT_FILE,
    SESSION_STORAGE_MODE,
    SESSION_STORAGE_MODE_PLAIN,
    SESSION_STORAGE_MODE_COMPRESS,
    CONTEXT_WINDOW,
    PROVIDER,
)

from datetime import datetime
from pathlib import Path

from ocla.state import load_state, save_state

DEFAULT_SYSTEM_PROMPT = """
You are a software development agent named OCLA, helping users understand, write and debug code.
You are being invoked inside a directory that contains a software project that the user
is working on. You can only operate within this directory and attempt to use tools outside of this
space will be rejected. You will be asked to operate within their project and assist them as a
collaborator in the development process alongside them.
"""


class ContextWindowExceededError(RuntimeError):
    exceeds_message: str

    def __init__(self, exceeds_message: str):
        self.exceeds_message = exceeds_message


class ProviderMismatchError(RuntimeError):
    """Raised when an existing session was created with a different provider."""

    def __init__(self, name: str, expected: str, actual: str) -> None:
        super().__init__(
            f"Session {name} was created with provider '{expected}' but current provider is '{actual}'."
        )
        self.expected = expected
        self.actual = actual


def _encode_data(data: bytes, mode: str) -> bytes:
    """Encode *data* using the given *mode*."""
    if mode == SESSION_STORAGE_MODE_PLAIN:
        return data
    if mode == SESSION_STORAGE_MODE_COMPRESS:
        return gzip.compress(data)
    raise ValueError(f"Unknown SESSION_STORAGE_MODE: {mode}")


def _decode_data(data: bytes, mode: str) -> bytes:
    """Reverse of :func:`_encode_data` for the given *mode*."""
    if mode == SESSION_STORAGE_MODE_PLAIN:
        return data
    if mode == SESSION_STORAGE_MODE_COMPRESS:
        return gzip.decompress(data)
    raise ValueError(f"Unknown SESSION_STORAGE_MODE: {mode}")


@functools.lru_cache(maxsize=None)
def _get_token_encoder(model: str | None) -> tiktoken.Encoding | None:
    if model:
        try:
            return tiktoken.encoding_for_model(model)
        except Exception:
            pass

    logging.warning(
        f"Could not find a tokenizer for model {model}. Token counts maybe inaccurate. Falling back to cl100k_base"
    )

    try:
        return tiktoken.get_encoding("cl100k_base")
    except Exception:
        logging.warning(
            f"Failed to load default tokenizer cl100k_base. Token counts maybe inaccurate"
        )
        return None


def _estimate_tokens(text: str, model: str | None = None) -> int:
    enc = _get_token_encoder(model)
    if enc is None:
        return len(text.split())

    try:
        return len(enc.encode(text))
    except Exception:
        return len(text.split())


@dataclass
class Session:
    name: str
    path: str = field(init=False)
    meta_path: str = field(init=False)
    messages: List[Dict[str, Any]] = field(default_factory=list)
    storage_mode: str = field(init=False)
    provider: str = field(init=False)
    tokens: int = field(init=False, default=0)

    def __post_init__(self):
        # file locations
        self.path = os.path.join(SESSION_DIR.get(), f"{self.name}.session")
        self.meta_path = os.path.join(SESSION_DIR.get(), f"{self.name}.meta")

        # (1) load metadata (if any) so we know how to decode the session file
        now_iso = datetime.now(timezone.utc).isoformat()
        self.provider = PROVIDER.get()
        update_meta = False
        if os.path.exists(self.meta_path):
            with open(self.meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            self.created = meta.get("created", now_iso)
            self.used = meta.get("used", now_iso)
            self.storage_mode = meta.get("storage_mode", SESSION_STORAGE_MODE.get())
            self.tokens = int(meta.get("tokens", 0))
            meta_provider = meta.get("provider")
            if meta_provider:
                if meta_provider != self.provider:
                    raise ProviderMismatchError(self.name, meta_provider, self.provider)
                self.provider = meta_provider
            else:
                # Upgrade legacy sessions later once messages are loaded
                update_meta = True
        else:
            self.created = now_iso
            self.used = now_iso
            self.storage_mode = SESSION_STORAGE_MODE.get()
            self._write_meta()  # create the .meta file immediately

        # (2) load messages if the session file exists
        if os.path.exists(self.path):
            with open(self.path, "rb") as f:
                raw = f.read()
            decoded = _decode_data(raw, self.storage_mode)
            self.messages = json.loads(decoded.decode("utf-8")).get("messages", [])

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

        self.tokens = self.token_count()
        if update_meta:
            self._write_meta()

    def _write_meta(self) -> None:
        os.makedirs(SESSION_DIR.get(), exist_ok=True)
        with open(self.meta_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "created": self.created,
                    "used": self.used,
                    "storage_mode": self.storage_mode,
                    "tokens": self.token_count(),
                    "provider": self.provider,
                },
                f,
                indent=2,
            )

    def save(self) -> None:
        """Persist messages and bump 'used' timestamp."""
        os.makedirs(SESSION_DIR.get(), exist_ok=True)
        self.storage_mode = SESSION_STORAGE_MODE.get()
        data = json.dumps({"messages": self.messages}, indent=2).encode("utf-8")
        encoded = _encode_data(data, self.storage_mode)
        with open(self.path, "wb") as f:
            f.write(encoded)

        self.used = datetime.now(timezone.utc).isoformat()
        self.tokens = self.token_count()
        self._write_meta()

    def add(self, message: Dict[str, Any]) -> None:
        """Append a message and immediately save the session."""
        self.messages.append(message)

        if self.token_count() > int(CONTEXT_WINDOW.get()):
            raise ContextWindowExceededError(
                f"Context window exceeded ({self.token_count()} / {CONTEXT_WINDOW.get()}). Please start a new session"
            )

        self.save()

    def token_count(self) -> int:
        """Estimate how many tokens are contained in this session."""
        from .config import MODEL

        total = 0
        for m in self.messages:
            content = m.get("content", "")
            if content:
                total += _estimate_tokens(str(content), MODEL.get())
        return total


def _ensure_dirs() -> None:
    os.makedirs(SESSION_DIR.get(), exist_ok=True)


@dataclass
class SessionInfo:
    name: str
    created: datetime
    used: datetime
    tokens: int
    provider: str

    def usage_pct(self) -> str:
        pct = self.tokens / int(CONTEXT_WINDOW.get())

        if pct > 1:
            return f"{pct * 100:.0f}% (!)"

        return f"{pct * 100:.0f}%"


def load_session_meta(name: str) -> SessionInfo | None:
    _ensure_dirs()

    meta_path = os.path.join(SESSION_DIR.get(), name + ".meta")

    # --- load timestamps from the .meta file ------------------------------
    with open(meta_path, "r", encoding="utf-8") as fp:
        meta = json.load(fp)
    tokens = int(meta.get("tokens", 0))
    provider = meta.get("provider", PROVIDER.get())

    # ISO-8601 strings → aware datetimes (UTC)
    created = datetime.fromisoformat(meta["created"].replace("Z", "+00:00"))
    used = datetime.fromisoformat(meta["used"].replace("Z", "+00:00"))

    return SessionInfo(
        name=name,
        created=created,
        used=used,
        tokens=tokens,
        provider=provider,
    )


def list_sessions() -> List[SessionInfo]:
    _ensure_dirs()

    infos = []

    for f in os.listdir(SESSION_DIR.get() or "."):
        if not f.endswith(".meta"):
            continue

        if info := load_session_meta(f.removesuffix(".meta")):
            infos.append(info)

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
