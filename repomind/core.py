"""Safe, deterministic Python source indexing and lexical retrieval."""
from __future__ import annotations
import ast
import math
import re
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

IGNORED = {".git", ".venv", "venv", "node_modules", "__pycache__", "dist", "build"}
MAX_FILE_BYTES = 256_000
MAX_FILES = 1500
TOKEN = re.compile(r"[A-Za-z_][A-Za-z_0-9]*")

@dataclass
class Chunk:
    path: str
    start_line: int
    end_line: int
    kind: str
    name: str
    content: str

    def as_dict(self):
        return asdict(self)

def tokens(text: str) -> list[str]:
    return [s.lower() for s in TOKEN.findall(text)]

def index_repository(root: str | Path) -> list[Chunk]:
    root = Path(root).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Expected a directory")
    chunks = []
    count = 0
    for path in sorted(root.rglob("*.py")):
        if any(part in IGNORED or part.startswith(".") for part in path.relative_to(root).parts):
            continue
        if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_FILE_BYTES:
            continue
        count += 1
        if count > MAX_FILES:
            break
        source = path.read_text(encoding="utf-8", errors="replace")
        lines = source.splitlines()
        relative = path.relative_to(root).as_posix()
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        nodes = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
        if not nodes and lines:
            chunks.append(Chunk(relative, 1, min(len(lines), 100), "module", path.stem, "\n".join(lines[:100])))
        for node in nodes:
            start = node.lineno
            end = min(getattr(node, "end_lineno", start), len(lines))
            kind = "class" if isinstance(node, ast.ClassDef) else "function"
            chunks.append(Chunk(relative, start, end, kind, node.name, "\n".join(lines[start-1:end])))
    return chunks

def search(chunks: list[Chunk], query: str, limit: int = 5) -> list[dict]:
    if not 1 <= limit <= 25:
        raise ValueError("limit must be between 1 and 25")
    query_terms = Counter(tokens(query))
    if not query_terms:
        return []
    documents = [Counter(tokens(c.path + " " + c.name + " " + c.content)) for c in chunks]
    df = Counter()
    for doc in documents:
        df.update(doc.keys())
    n = len(chunks)
    results = []
    for chunk, doc in zip(chunks, documents):
        score = sum((1 + math.log(doc[t])) * math.log(1 + (n + 1) / (df[t] + 1)) * weight for t, weight in query_terms.items() if doc[t])
        if score:
            results.append((score, chunk))
    results.sort(key=lambda item: (-item[0], item[1].path, item[1].start_line))
    return [{"score": round(score, 4), **chunk.as_dict()} for score, chunk in results[:limit]]

def answer(root: str | Path, question: str, limit: int = 5) -> dict:
    matches = search(index_repository(root), question, limit)
    return {"question": question, "answer": ("Relevant source locations are listed below. Review these code excerpts to answer the question." if matches else "No matching Python symbols found."), "citations": matches}
