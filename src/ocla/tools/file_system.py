import io
from pathlib import Path
from difflib import unified_diff
from ocla.cli_io import info
from rich.syntax import Syntax
from rich.console import Console
from ocla.util import can_access_path

from . import Tool, ToolSecurity


class ListFiles(Tool):
    security = ToolSecurity.PERMISSIBLE
    description = "List all files and folders in the requested path"

    def execute(self, path: str = ".", recursive: bool = False) -> (list[str], str):
        root = Path(path)
        if not can_access_path(root):
            return [], f"OCLA cannot access: {path}"
        if not root.is_dir():
            return [], f"{path} is not a directory"

        try:
            entries = []
            paths = root.rglob("*") if recursive else root.iterdir()
            for p in paths:
                if can_access_path(p):
                    entries.append(
                        p.relative_to(root).as_posix() if recursive else p.name
                    )
            return sorted(entries), ""
        except PermissionError as e:
            return [], f"Access denied while scanning: {e}"


class ReadFile(Tool):
    security = ToolSecurity.PERMISSIBLE
    description = "Read the contents of a single file"

    def execute(self, path: str = ".", encoding: str = "utf-8") -> (str, str):
        file_path = Path(path)
        if not can_access_path(file_path):
            return "", f"OCLA cannot access: {path}"
        if not file_path.is_file():
            return "", f"File not found: {path}"
        return file_path.read_text(encoding=encoding) or "this file has no content", ""


class WriteFile(Tool):
    security = ToolSecurity.ASK
    description = "Overwrite the contents of the given file with new content"

    def execute(
        self, path: str, new_content: str, encoding: str = "utf-8"
    ) -> (str, str):
        file_path = Path(path)
        if not can_access_path(file_path, for_write=True):
            return "", f"OCLA cannot access: {path}"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(new_content, encoding=encoding)
        return f"written {len(new_content)} bytes to {path}", ""

    def prompt(self, call: dict, yes_no: str) -> str:
        args = call.get("function", {}).get("arguments", {}) or {}
        try:
            path = args["path"]
            new_content = args["new_content"]
        except KeyError as missing:
            raise ValueError(f"write_file_diff: missing argument {missing!s}") from None

        encoding = args.get("encoding", "utf-8")
        file_path = Path(path)

        if not can_access_path(file_path, for_write=True):
            return f"Access denied: {path}"

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
