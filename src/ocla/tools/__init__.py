import dataclasses
from typing import Callable, Optional
import inspect
from .file_system import list_files, read_file, generate_patch, apply_patch, write_file


@dataclasses.dataclass
class Tool:
    fn: Callable
    name: Optional[str] = None

    def __post_init__(self) -> None:
        self._sig = inspect.signature(self.fn)
        if self.name is None:
            self.name = self.fn.__name__


ALL: dict[str, Tool] = {
    "list_files": Tool(fn=list_files),
    "read_file": Tool(fn=read_file),
    "write_file": Tool(fn=write_file),
}
