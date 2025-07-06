from __future__ import annotations

import abc
import dataclasses
from typing import Iterable, Any, Optional

from ocla.config import PROVIDER

@dataclasses.dataclass
class ModelInfo:
    name: str
    context_length: Optional[int] = None
    supports_thinking: Optional[bool] = None

class Provider(abc.ABC):
    """Abstract base class for model providers."""

    name: str

    @abc.abstractmethod
    def initialization_check(self, model: str) -> None:
        """Optional provider specific initialization checks."""

    def model_info(self, model: str) -> ModelInfo:
        """Get info for the given model."""

    @abc.abstractmethod
    def chat(
        self,messages: list[dict[str, Any]], tools: list[Tool], thinking: bool, model: str, context_window: Optional[int]
    ) -> Iterable[dict[str, Any]]:
        pass

    @abc.abstractmethod
    def available_models(self) -> list[ModelInfo]:
        """Return a list of available models."""


from .ollama_provider import OllamaProvider  # noqa: E402
from .openai_provider import OpenAIProvider  # noqa: E402

_PROVIDERS: dict[str, Provider] = {
    OllamaProvider.name: OllamaProvider(),
    OpenAIProvider.name: OpenAIProvider(),
}


def get_provider() -> Provider:
    """Return the active provider instance based on configuration."""
    return _PROVIDERS[PROVIDER.get()]
