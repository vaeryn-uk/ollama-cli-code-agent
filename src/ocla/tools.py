from pathlib import Path

def ls(path: str = ".") -> str:
    return [entry.name for entry in Path(path).iterdir()]