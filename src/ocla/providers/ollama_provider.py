from __future__ import annotations

import logging
import os
from typing import Iterable, Any, Optional
import ollama

from ocla.config import OLLAMA_HOST_OVERRIDE
from . import Provider, ModelInfo


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
            self._client = ollama.Client(host=self._resolve_host())
        return self._client

    def initialization_check(self, model: str) -> None:
        import ollama

        try:
            model = self._client_obj().show(model)
        except ConnectionError:
            raise RuntimeError(f"Cannot connect to Ollama at {self._resolve_host()}")
        except ollama.ResponseError:
            raise RuntimeError(
                f"Failed to find ollama model info for '{model}'\nAvailable models: {', '.join([x.name for x in self.available_models()])}"
            )

    def model_info(self, model: str) -> ModelInfo:
        info = self._client_obj().show(model)
        context_length = None
        for key in info.modelinfo:
            if "context_length" in key or "num_ctx" in key:
                if (
                        isinstance(info.modelinfo[key], str)
                        and info.modelinfo[key].isdigit()
                ):
                    context_length = int(info.modelinfo[key])
                    break
                if type(info.modelinfo[key]) is int:
                    context_length = info.modelinfo[key]
                    break

        return ModelInfo(
            name=model,
            supports_thinking="thinking" in info.capabilities,
            context_length=context_length,
        )

    def chat(
        self, messages: list[dict[str, Any]], tools: list[Any], thinking: bool, model: str, context_window: Optional[int],
    ) -> Iterable[dict[str, Any]]:
        opts = {}

        if context_window is not None:
            opts["num_ctx"] = context_window

        for chunk in self._client_obj().chat(
            model=model,
            messages=messages,
            tools=[t.describe() for t in tools],
            stream=True,
            think=thinking,
            options=opts,
        ):
            yield chunk

    def available_models(self) -> list[ModelInfo]:
        try:
            data = self._client_obj().list()
        except Exception as e:  # pragma: no cover - network errors
            logging.debug(f"failed to list models: {e}")
            return []

        out = []

        for model in data.models or []:
            try:
                out.append(self.model_info(model.model))
            except Exception as e:  # pragma: no cover - network errors
                logging.debug(f"failed to query model info: {e}")
                continue

        return out