import os
import re
import json
import math
from collections import Counter
from typing import Dict, List, Tuple

TOKEN_PATTERN = re.compile(r"\b\w+\b")


def _tokenize(text: str) -> List[str]:
    return TOKEN_PATTERN.findall(text.lower())


def _iter_files(directory: str):
    for root, dirs, files in os.walk(directory):
        # skip typical non-source directories
        if ".git" in dirs:
            dirs.remove(".git")
        if ".venv" in dirs:
            dirs.remove(".venv")
        if "venv" in dirs:
            dirs.remove("venv")
        for name in files:
            if name.endswith((".py", ".md", ".txt")):
                yield os.path.join(root, name)


def create_index(directory: str, index_path: str) -> None:
    """Create a simple TF-IDF index of source files."""
    documents: Dict[str, Counter[str]] = {}
    df: Counter[str] = Counter()

    for path in _iter_files(directory):
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
        except Exception:
            continue
        tokens = _tokenize(text)
        if not tokens:
            continue
        counts = Counter(tokens)
        documents[path] = counts
        for w in counts.keys():
            df[w] += 1

    n_docs = len(documents) or 1
    idf: Dict[str, float] = {w: math.log(n_docs / (1 + c)) + 1 for w, c in df.items()}

    tfidf_docs: Dict[str, Dict[str, float]] = {}
    for path, counts in documents.items():
        total = sum(counts.values()) or 1
        tfidf_docs[path] = {w: (counts[w] / total) * idf[w] for w in counts}

    index = {"idf": idf, "documents": tfidf_docs}
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f)


def _load_index(index_path: str):
    with open(index_path, "r", encoding="utf-8") as f:
        return json.load(f)


def query_index(query: str, index_path: str, top_k: int = 5) -> List[Tuple[str, float]]:
    """Return the top matching files for *query* from the index."""
    data = _load_index(index_path)
    idf: Dict[str, float] = data.get("idf", {})
    docs: Dict[str, Dict[str, float]] = data.get("documents", {})
    n_docs = len(docs) or 1

    q_tokens = _tokenize(query)
    q_counts = Counter(q_tokens)
    total = sum(q_counts.values()) or 1
    q_vec: Dict[str, float] = {}
    for w, c in q_counts.items():
        idf_val = idf.get(w, math.log(n_docs / 1) + 1)
        q_vec[w] = (c / total) * idf_val

    q_norm = math.sqrt(sum(v * v for v in q_vec.values())) or 1.0

    results = []
    for path, vec in docs.items():
        dot = 0.0
        d_norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        for w, qv in q_vec.items():
            dot += qv * vec.get(w, 0.0)
        score = dot / (q_norm * d_norm)
        results.append((path, score))

    results.sort(key=lambda x: x[1], reverse=True)
    return results[:top_k]
