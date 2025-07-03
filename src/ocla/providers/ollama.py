from __future__ import annotations

import logging
import os
from typing import Iterable, Any

from ocla.config import (
    CONTEXT_WINDOW,
    MODEL,
    OLLAMA_HOST_OVERRIDE,
    THINKING,
    THINKING_DISABLED,
)
from . import Provider


class OllamaProvider(Provider):
    name = "ollama"

    def __init__(self) -> None:
        self._client = None

    def _resolve_host(self) -> str | None:
        return (
            OLLAMA_HOST_OVERRIDE.get()
            or os.environ.get("OLLAMA_HOST")
            or "http://localhost:11434"
        )

    def _client_obj(self):
        if self._client is None:
            import ollama

            self._client = ollama.Client(host=self._resolve_host())
        return self._client

    def initialization_check(self) -> None:
        import ollama

        model = MODEL.get()
        try:
            available = self.available_models()
        except (ollama.ResponseError, ConnectionError):
            raise RuntimeError(f"Cannot connect to Ollama at {self._resolve_host()}")

        if model not in available:
            raise RuntimeError(
                f"Ollama does not have the requested model '{model}'. Available models: {', '.join(available)}"
            )

    def context_limit(self, model: str) -> int | None:
        try:
            response = self._client_obj().show(model)
        except Exception as e:  # pragma: no cover - network errors
            logging.debug(f"failed to query model info: {e}")
            return None

        for key in response.modelinfo:
            if "context_length" in key or "num_ctx" in key:
                if (
                    isinstance(response.modelinfo[key], str)
                    and response.modelinfo[key].isdigit()
                ):
                    return int(response.modelinfo[key])
                if type(response.modelinfo[key]) is int:
                    return response.modelinfo[key]
        return None

    def supports_thinking(self, model: str) -> bool | None:
        try:
            response = self._client_obj().show(model)
        except Exception as e:  # pragma: no cover - network errors
            logging.debug(f"failed to query model info: {e}")
            return None

        if response.capabilities and "thinking" in response.capabilities:
            return True
        return False

    def chat(
        self, messages: list[dict[str, Any]], tools: list[Any]
    ) -> Iterable[dict[str, Any]]:
        think_mode = THINKING.get()
        enable_think = think_mode != THINKING_DISABLED and self.supports_thinking(
            MODEL.get()
        )
        for chunk in self._client_obj().chat(
            model=MODEL.get(),
            messages=messages,
            tools=tools,
            stream=True,
            think=enable_think,
            options={"num_ctx": int(CONTEXT_WINDOW.get())},
        ):
            yield chunk

    def available_models(self) -> list[str]:
        try:
            data = self._client_obj().list()
        except Exception as e:  # pragma: no cover - network errors
            logging.debug(f"failed to list models: {e}")
            return []
        return [m.model for m in data.models if m.model]
