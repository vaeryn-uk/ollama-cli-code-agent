from __future__ import annotations

import os, logging
from typing import Iterable, Any, Optional
from openai import OpenAI, NotFoundError

from . import Provider, ModelInfo
from ..config import OPENAI_API_KEY

class ModelNotFound(RuntimeError):
    pass

class OpenAIProvider(Provider):
    name = "openai"
    _client: Optional[OpenAI] = None

    def _resolve_api_key(self) -> str | None:
        return (
            OPENAI_API_KEY.get()
            or os.environ.get("OPENAI_API_KEY")
            or None
        )

    def _client_obj(self):
        if self._client is None:
            self._client = OpenAI(api_key=self._resolve_api_key())
        return self._client

    def initialization_check(self, model: str) -> None:
        try:
            self.model_info(model)
        except ModelNotFound:
            available = [
                x.name
                for x
                in self.available_models()
            ]
            raise RuntimeError(f"OpenAI model '{model}' not found. Available models: {', '.join(available)}")
        except Exception as e:
            raise RuntimeError(f"Failed to find OpenAI model info for '{model}': {e}")

    def chat(
        self, messages: list[dict[str, Any]], tools: list[Any], thinking: bool, model: str, context_window: Optional[int]
    ) -> Iterable[dict[str, Any]]:  # pragma: no cover - placeholder
        raise NotImplementedError

    def available_models(self) -> list[ModelInfo]:  # pragma: no cover - placeholder
        try:
            response = self._client_obj().models.list()  # GET /v1/models
        except Exception as exc:  # network / auth errors, etc.
            raise RuntimeError(f"Could not list models: {exc}") from exc

        # `response.data` is a list of `Model` objects; each has an `id` attribute.
        return [ModelInfo(name=model.id) for model in response.data]

    def model_info(self, model: str) -> ModelInfo:
        try:
            data = self._client_obj().models.retrieve(model)
        except NotFoundError:
            raise ModelNotFound(f"OpenAI model '{model}' not found")
        except Exception as exc:  # pragma: no cover – network I/O
            raise RuntimeError(f"Unable to retrieve info for openai model '{model}': {exc}") from exc

        return ModelInfo(name=data.id)

