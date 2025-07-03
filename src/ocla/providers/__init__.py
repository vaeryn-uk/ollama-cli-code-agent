from __future__ import annotations

import abc
from typing import Iterable, Any

from ocla.config import PROVIDER


class Provider(abc.ABC):
    """Abstract base class for model providers."""

    name: str

    @abc.abstractmethod
    def initialization_check(self) -> None:
        """Optional provider specific initialization checks."""

    @abc.abstractmethod
    def context_limit(self, model: str) -> int | None:
        pass

    @abc.abstractmethod
    def supports_thinking(self, model: str) -> bool | None:
        pass

    @abc.abstractmethod
    def chat(
        self, messages: list[dict[str, Any]], tools: list[Any]
    ) -> Iterable[dict[str, Any]]:
        pass

    @abc.abstractmethod
    def available_models(self) -> list[str]:
        """Return a list of available model identifiers."""
        pass


from .ollama import OllamaProvider  # noqa: E402
from .openai import OpenAIProvider  # noqa: E402

_PROVIDERS: dict[str, Provider] = {
    "ollama": OllamaProvider(),
    "openai": OpenAIProvider(),
}


def get_provider() -> Provider:
    """Return the active provider instance based on configuration."""
    return _PROVIDERS[PROVIDER.get()]
