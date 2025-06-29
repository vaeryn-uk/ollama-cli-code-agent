import enum
import inspect
from typing import Callable, Optional

from ollama import Message


class ToolSecurity(enum.Enum):
    PERMISSIBLE = "permissible"
    ASK = "ask"


class Tool:
    """Base class for tools used by the agent."""

    security: ToolSecurity = ToolSecurity.ASK
    prompt: Optional[Callable[[Message.ToolCall, str], str]] = None

    def __init__(self, name: Optional[str] = None) -> None:
        self.name = name or self.__class__.__name__
        # ``ollama`` relies on ``__name__`` and ``inspect.signature`` when a
        # callable is passed in as a tool.  We provide both so that instances of
        # ``Tool`` subclasses behave like regular functions.
        self.__name__ = self.name
        self.__signature__ = inspect.signature(self.execute)

    def execute(self, *args, **kwargs):  # pragma: no cover - abstract
        raise NotImplementedError

    def __call__(self, *args, **kwargs):  # pragma: no cover - compatibility
        """Allow tools to be passed directly to Ollama."""
        return self.execute(*args, **kwargs)


# Import concrete tool implementations after defining the base class to avoid
# circular imports.
from .file_system import ListFiles, ReadFile, WriteFile


ALL: dict[str, Tool] = {
    "list_files": ListFiles(),
    "read_file": ReadFile(),
    "write_file": WriteFile(),
}
