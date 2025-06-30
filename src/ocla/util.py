import re
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


def can_access_path(path: Path | str, *, forwrite: bool = False) -> bool:
    """Return ``True`` if ``path`` is allowed to be accessed.

    A path is considered inaccessible when it is absolute or if any of its
    segments represent a hidden directory (start with ``.``).  The ``forwrite``
    flag is currently unused but reserved for future policy changes.
    """

    p = Path(path)

    if p.is_absolute():
        return False

    for part in p.parts:
        if part in (".", ".."):
            continue
        if part.startswith("."):
            return False

    return True
