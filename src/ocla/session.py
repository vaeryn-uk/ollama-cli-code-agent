import json
import gzip
import logging
import os
import sys
import time
from datetime import timezone
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from .config import (
    SESSION_DIR,
    PROJECT_CONTEXT_FILE,
    SESSION_STORAGE_MODE,
    SESSION_STORAGE_MODE_PLAIN,
    SESSION_STORAGE_MODE_COMPRESS,
    SESSION_STORAGE_MODE_ENCRYPT,
)

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


def _encrypt_os(data: bytes) -> bytes:
    if sys.platform.startswith("win"):
        import ctypes
        from ctypes import wintypes

        class DATA_BLOB(ctypes.Structure):
            _fields_ = [
                ("cbData", wintypes.DWORD),
                ("pbData", ctypes.POINTER(ctypes.c_byte)),
            ]

        crypt32 = ctypes.windll.crypt32
        kernel32 = ctypes.windll.kernel32

        blob_in = DATA_BLOB(
            len(data),
            ctypes.cast(
                ctypes.create_string_buffer(data), ctypes.POINTER(ctypes.c_byte)
            ),
        )
        blob_out = DATA_BLOB()
        if not crypt32.CryptProtectData(
            ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out)
        ):
            raise ctypes.WinError()
        try:
            return ctypes.string_at(blob_out.pbData, blob_out.cbData)
        finally:
            kernel32.LocalFree(blob_out.pbData)
    raise RuntimeError("OS does not support encrypted sessions")


def _decrypt_os(data: bytes) -> bytes:
    if sys.platform.startswith("win"):
        import ctypes
        from ctypes import wintypes

        class DATA_BLOB(ctypes.Structure):
            _fields_ = [
                ("cbData", wintypes.DWORD),
                ("pbData", ctypes.POINTER(ctypes.c_byte)),
            ]

        crypt32 = ctypes.windll.crypt32
        kernel32 = ctypes.windll.kernel32

        blob_in = DATA_BLOB(
            len(data),
            ctypes.cast(
                ctypes.create_string_buffer(data), ctypes.POINTER(ctypes.c_byte)
            ),
        )
        blob_out = DATA_BLOB()
        if not crypt32.CryptUnprotectData(
            ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out)
        ):
            raise ctypes.WinError()
        try:
            return ctypes.string_at(blob_out.pbData, blob_out.cbData)
        finally:
            kernel32.LocalFree(blob_out.pbData)
    raise RuntimeError("OS does not support encrypted sessions")


def _encode_data(data: bytes, mode: str) -> bytes:
    """Encode *data* using the given *mode*."""
    if mode == SESSION_STORAGE_MODE_PLAIN:
        return data
    if mode == SESSION_STORAGE_MODE_COMPRESS:
        return gzip.compress(data)
    if mode == SESSION_STORAGE_MODE_ENCRYPT:
        enc = gzip.compress(data)
        return _encrypt_os(enc)
    raise ValueError(f"Unknown SESSION_STORAGE_MODE: {mode}")


def _decode_data(data: bytes, mode: str) -> bytes:
    """Reverse of :func:`_encode_data` for the given *mode*."""
    if mode == SESSION_STORAGE_MODE_PLAIN:
        return data
    if mode == SESSION_STORAGE_MODE_COMPRESS:
        return gzip.decompress(data)
    if mode == SESSION_STORAGE_MODE_ENCRYPT:
        dec = _decrypt_os(data)
        return gzip.decompress(dec)
    raise ValueError(f"Unknown SESSION_STORAGE_MODE: {mode}")


@dataclass
class Session:
    name: str
    path: str = field(init=False)
    meta_path: str = field(init=False)
    messages: List[Dict[str, Any]] = field(default_factory=list)
    storage_mode: str = field(init=False)

    def __post_init__(self):
        # file locations
        self.path = os.path.join(SESSION_DIR.get(), f"{self.name}.session")
        self.meta_path = os.path.join(SESSION_DIR.get(), f"{self.name}.meta")

        # (1) load metadata (if any) so we know how to decode the session file
        now_iso = datetime.now(timezone.utc).isoformat()
        if os.path.exists(self.meta_path):
            with open(self.meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            self.created = meta.get("created", now_iso)
            self.used = meta.get("used", now_iso)
            self.storage_mode = meta.get("storage_mode", SESSION_STORAGE_MODE.get())
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

    def _write_meta(self) -> None:
        os.makedirs(SESSION_DIR.get(), exist_ok=True)
        with open(self.meta_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "created": self.created,
                    "used": self.used,
                    "storage_mode": self.storage_mode,
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
