import abc
import enum
import inspect
import json
import typing
from ollama import Message

from ..util import pascal_to_snake, format_tool_arguments, truncate


class ToolSecurity(enum.Enum):
    PERMISSIBLE = "permissible"
    ASK = "ask"


class Tool(abc.ABC):
    """Base class for tools used by the agent."""

    name: str
    security: ToolSecurity = ToolSecurity.ASK

    def __init__(self) -> None:
        self.name = pascal_to_snake(self.__class__.__name__)

        # ``ollama`` relies on ``__name__`` and ``inspect.signature`` when a
        # callable is passed in as a tool.  We provide both so that instances of
        # ``Tool`` subclasses behave like regular functions.
        self.__name__ = self.name
        self.__signature__ = inspect.signature(self.execute)

    @abc.abstractmethod
    def execute(self, *args, **kwargs) -> (typing.Any, str):
        """Execute the tool."""

    def prompt(self, call: Message.ToolCall, yes_no: str) -> str:
        return f"Run tool '{self.name}'? Arguments: {truncate(format_tool_arguments(call), 50)} {yes_no}"

    def __call__(self, *args, **kwargs):
        """Allow tools to be passed directly to Ollama."""
        return self.execute(*args, **kwargs)


# Import concrete tool implementations after defining the base class to avoid
# circular imports.
from .file_system import ListFiles, ReadFile, WriteFile
from .git import GitShowChanges, GitCommit, GitLog


ALL: dict[str, Tool] = {
    "list_files": ListFiles(),
    "read_file": ReadFile(),
    "write_file": WriteFile(),
    "git_show_changes": GitShowChanges(),
    "git_commit": GitCommit(),
    "git_log": GitLog(),
}
