from __future__ import annotations

import os, logging
from typing import Iterable, Any, Optional

from ollama import ChatResponse, Message
from openai import OpenAI, NotFoundError

from . import Provider, ModelInfo
from ocla.tools import Tool
from ..config import OPENAI_API_KEY
import json

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
        self, messages: list[dict[str, Any]], tools: list[Tool], thinking: bool, model: str, context_window: Optional[int]
    ) -> Iterable[ChatResponse]:  # pragma: no cover - placeholder

        # Fix JSON encoding of tools' arguments back to openai
        for msg in messages:
            if "tool_calls" not in msg:  # key check, not hasattr
                continue

            for tc in msg["tool_calls"]:
                args = tc["function"]["arguments"]
                if not isinstance(args, str):  # only encode dict/other types
                    tc["function"]["arguments"] = json.dumps(args, separators=(",", ":"))

        request: Dict[str, Any] = {
            "model": model or self._default_model,
            "messages": [
                m
                for m
                in messages
            ],
        }

        if tools:
            request["tools"] = []
            for tool in tools:
                request["tools"].append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.describe().function.parameters,
                    }
                })

        try:
            tool_call_json: dict[int, dict[str, str]] = {}
            for chunk in self._client.chat.completions.create(stream=True, **request):
                delta = chunk.choices[0].delta  # type: ignore[attr-defined]

                for tc in (getattr(delta, "tool_calls", []) or []):
                    logging.debug(tc)
                    if tc.index not in tool_call_json:
                        tool_call_json[tc.index] = {"name": None, "args": "", "id": ""}
                    logging.debug(tool_call_json)
                    if tc.function.name:
                        tool_call_json[tc.index]["name"] = tc.function.name
                    if tc.function.arguments:
                        tool_call_json[tc.index]["args"] += tc.function.arguments
                    if tc.id:
                        tool_call_json[tc.index]["id"] += tc.id

                if len(tool_call_json) > 0 and chunk.choices[0].finish_reason in ["tool_calls", "stop"]:
                    yield {
                        "message": {
                            "role": "assistant",
                            "content": "",
                            "tool_calls": [
                                {
                                    "id": tc["id"],
                                    "type": "function",
                                    "function": {
                                        "name": tc["name"],
                                        "arguments": json.loads(tc["args"]),
                                    }
                                }
                                for tc
                                in tool_call_json.values()
                            ]
                        }
                    }
                    tool_call_json.clear()

                # Emit only meaningful deltas (text or function-call updates).
                if delta.content:
                    yield ChatResponse(
                        message={
                            "role": "assistant",
                            "content": delta.content or "",
                        },
                    )
        except Exception as exc:  # pragma: no cover – network I/O
            raise RuntimeError(f"OpenAI streaming chat failed: {exc}") from exc

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

