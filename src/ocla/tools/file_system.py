from pathlib import Path
from difflib import unified_diff


def list_files(path: str = ".", recursive: bool = False) -> list[str]:
    root = Path(path)

    if not root.is_dir():
        raise NotADirectoryError(path)

    if recursive:
        # rglob returns all descendants; keep files only and make them relative
        return sorted(
            str(p.relative_to(root).as_posix()) for p in root.rglob("*") if p.is_file()
        )

    # non-recursive: names only, no sub-dirs
    return sorted(p.name for p in root.iterdir() if p.is_file())


def read_file(path: str = ".", encoding="utf-8") -> str:
    file_path = Path(path)

    if not file_path.is_file():
        raise FileNotFoundError(f"{path!r} is not an existing file")

    return file_path.read_text(encoding=encoding)


def generate_patch(path: str, new_content: str, encoding: str = "utf-8") -> str:
    """Return a unified diff patch from ``path`` to ``new_content``."""
    file_path = Path(path)

    if not file_path.is_file():
        raise FileNotFoundError(f"{path!r} is not an existing file")

    old_lines = file_path.read_text(encoding=encoding).splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)
    return "".join(unified_diff(old_lines, new_lines, fromfile=path, tofile=path))
