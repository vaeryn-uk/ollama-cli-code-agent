import hashlib
import json
import math
import os
import re
from typing import Dict, Iterable, List, Tuple

TOKEN_PATTERN = re.compile(r"\b\w+\b")
EMBED_DIM = 64


def _tokenize(text: str) -> Iterable[str]:
    return TOKEN_PATTERN.findall(text.lower())


def _iter_files(directory: str) -> Iterable[str]:
    for root, dirs, files in os.walk(directory):
        if ".git" in dirs:
            dirs.remove(".git")
        if ".venv" in dirs:
            dirs.remove(".venv")
        if "venv" in dirs:
            dirs.remove("venv")
        for name in files:
            if name.endswith((".py", ".md", ".txt")):
                yield os.path.join(root, name)


def _embed(text: str, dim: int = EMBED_DIM) -> List[float]:
    tokens = list(_tokenize(text))
    vec = [0.0] * dim
    if not tokens:
        return vec
    for token in tokens:
        h = hashlib.md5(token.encode()).digest()
        for i, byte in enumerate(h):
            vec[i % dim] += (byte / 255.0)
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def create_index(directory: str, index_path: str) -> None:
    """Create an embedding-based vector index of project files."""
    vectors: Dict[str, List[float]] = {}
    for path in _iter_files(directory):
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
        except Exception:
            continue
        vectors[path] = _embed(text)
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump({"dim": EMBED_DIM, "vectors": vectors}, f)


def _load_index(index_path: str) -> Dict[str, object]:
    with open(index_path, "r", encoding="utf-8") as f:
        return json.load(f)


def query_index(query: str, index_path: str, top_k: int = 5) -> List[Tuple[str, float]]:
    """Return the top matching files for *query* from the index."""
    data = _load_index(index_path)
    dim = data.get("dim", EMBED_DIM)
    vectors: Dict[str, List[float]] = data.get("vectors", {})
    q_vec = _embed(query, dim)
    q_norm = math.sqrt(sum(v * v for v in q_vec)) or 1.0
    results = []
    for path, vec in vectors.items():
        d_norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        dot = sum(q * d for q, d in zip(q_vec, vec))
        score = dot / (q_norm * d_norm)
        results.append((path, score))
    results.sort(key=lambda x: x[1], reverse=True)
    return results[:top_k]
