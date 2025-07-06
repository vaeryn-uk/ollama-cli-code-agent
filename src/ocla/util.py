import json
import re
import fnmatch, glob, os
from pathlib import Path


def pascal_to_snake(name: str) -> str:
    """
    Convert PascalCase or camelCase to snake_case.
    """
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def truncate(s: str, limit: int) -> str:
    if len(s) > limit:
        return s[:limit] + f"… (truncated, {len(s) - limit} chars more)"

    return s


def format_tool_arguments(call: dict) -> str:
    raw_args = call.get("function", {}).get("arguments")
    try:
        if isinstance(raw_args, (dict, list)):
            args = json.dumps(raw_args, separators=(",", ":"))
        else:
            args = str(raw_args)
    except TypeError:
        args = str(raw_args)

    return args


def can_access_path(path: Path | str, *, for_write: bool = False) -> bool:
    """True if *path* (after expanding `~` and resolving symlinks) stays inside CWD."""
    cwd = Path.cwd().resolve()

    # Expand user home, then make absolute relative to cwd, finally resolve symlinks
    try:
        original = Path(path).expanduser()
        resolved = (original if original.is_absolute() else cwd / original).resolve()
    except OSError:  # bad symlink or permission error while resolving
        return False

    # 1. Must live under cwd
    if cwd not in resolved.parents and resolved != cwd:
        return False

    # 2. Reject hidden components anywhere in the *unresolved* path
    if any(part.startswith(".") and part not in (".", "..") for part in original.parts):
        return False

    # 3. Ignore existence so long as path stays within cwd
    return True
