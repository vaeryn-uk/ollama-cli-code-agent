import dataclasses
import enum
from typing import Callable, Optional
import inspect
from ollama import Message
from .file_system import list_files, read_file, write_file, write_file_diff

class ToolSecurity(enum.Enum):
    PERMISSIBLE = "permissible"
    ASK = "ask"

@dataclasses.dataclass
class Tool:
    fn: Callable
    security: ToolSecurity = ToolSecurity.ASK
    prompt: Optional[Callable[[Message.ToolCall, str], str]] = None
    name: Optional[str] = None

    def __post_init__(self) -> None:
        self._sig = inspect.signature(self.fn)
        if self.name is None:
            self.name = self.fn.__name__


ALL: dict[str, Tool] = {
    "list_files": Tool(fn=list_files, security=ToolSecurity.PERMISSIBLE),
    "read_file": Tool(fn=read_file, security=ToolSecurity.PERMISSIBLE),
    "write_file": Tool(fn=write_file, security=ToolSecurity.ASK, prompt=write_file_diff),
}
