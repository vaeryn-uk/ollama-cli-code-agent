from __future__ import annotations

from typing import Iterable, Any

from . import Provider


class OpenAIProvider(Provider):
    name = "openai"

    def __init__(self) -> None:
        try:
            import openai  # type: ignore

            self._client = openai.Client()
        except Exception:  # pragma: no cover - optional dep may be missing
            self._client = None

    def initialization_check(self) -> None:
        if self._client is None:
            raise RuntimeError("openai package not available")

    def context_limit(self, model: str) -> int | None:  # pragma: no cover - placeholder
        return None

    def supports_thinking(
        self, model: str
    ) -> bool | None:  # pragma: no cover - placeholder
        return False

    def chat(
        self, messages: list[dict[str, Any]], tools: list[Any]
    ) -> Iterable[dict[str, Any]]:  # pragma: no cover - placeholder
        raise NotImplementedError

    def available_models(self) -> list[str]:  # pragma: no cover - placeholder
        return []
