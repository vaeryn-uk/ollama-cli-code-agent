import io
from pathlib import Path
from difflib import unified_diff
from ocla.cli_io import info
from rich.syntax import Syntax
from rich.console import Console

import ollama

from . import Tool, ToolSecurity


class ListFiles(Tool):
    """Return a list of file names in the given directory."""

    security = ToolSecurity.PERMISSIBLE

    def execute(self, path: str = ".") -> (list[str], str):
        root = Path(path)
        if not root.is_dir():
            raise NotADirectoryError(path)
        # non-recursive: names only, no sub-dirs
        return sorted(p.name for p in root.iterdir() if p.is_file()), ""


class ReadFile(Tool):
    """Read the contents of a file."""

    security = ToolSecurity.PERMISSIBLE

    def execute(self, path: str = ".", encoding: str = "utf-8") -> (str, str):
        file_path = Path(path)
        if not file_path.is_file():
            return "", f"File not found: {path}"
        return file_path.read_text(encoding=encoding), ""


class WriteFile(Tool):
    security = ToolSecurity.ASK

    def execute(self, path: str, new_content: str, encoding: str = "utf-8") -> (str, str):
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(new_content, encoding=encoding)
        return f"written {len(new_content)} bytes to {path}", ""

    def prompt(self, call: ollama.Message.ToolCall, yes_no: str) -> str:
        args = call.function.arguments or {}
        try:
            path = args["path"]
            new_content = args["new_content"]
        except KeyError as missing:
            raise ValueError(f"write_file_diff: missing argument {missing!s}") from None

        encoding = args.get("encoding", "utf-8")
        file_path = Path(path)

        # Load existing content (empty if the file does not yet exist)
        old_lines = (
            file_path.read_text(encoding=encoding).splitlines(keepends=True)
            if file_path.is_file()
            else []
        )
        new_lines = new_content.splitlines(keepends=True)

        diff = "".join(
            unified_diff(
                old_lines,
                new_lines,
                fromfile=path,
                tofile=path,
                lineterm="",  # no extra newline per hunk line; keeps output clean
            )
        )

        if not diff:
            return ""

        console = Console(file=io.StringIO(), record=True, force_terminal=True)

        info(f"Ocla would like to apply the following changes to {path}:", con=console)

        console.print(Syntax(diff, "diff", theme="ansi_dark"))

        info(f"Do you want to proceed? {yes_no}", con=console)

        return console.export_text(styles=True)
