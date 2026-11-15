"""Bounded source-code index with Python AST extraction and explainable BM25 search.

This library deliberately reads code as *data*: it does not import modules or run
commands from repositories. JS/TS extraction is best effort and not a full parser.
"""
from __future__ import annotations

import ast
from collections import Counter
from dataclasses import asdict, dataclass
import math
import os
from pathlib import Path
import re
from typing import Iterable

SKIP_DIRS = {'.git', '.venv', 'venv', 'node_modules', '__pycache__', 'dist', 'build', '.next', '.pytest_cache', 'coverage', '.mypy_cache', '.tox', '.idea', '.vscode', 'vendor', '.turbo'}
EXTENSIONS = {'.py', '.js', '.jsx', '.ts', '.tsx'}
MAX_FILE_BYTES = 256_000
MAX_TOTAL_BYTES = 16_000_000
MAX_FILES = 1500
TOKEN = re.compile(r'[A-Za-z_][A-Za-z_0-9]*')
JS_PATTERN = re.compile(r'^\s*(?:(?:export|default|async|declare|public|private|static)\s+)*(?:(?:function|class|interface|type|enum)\s+([A-Za-z_$][\w$]*)|(?:const|let)\s+([A-Za-z_$][\w$]*)\s*(?::[^=\n]+)?=\s*(?:async\s*)?(?:\([^)]*\)|[A-Za-z_$][\w$]*)\s*=>)', re.MULTILINE)
STOP = {'the', 'is', 'a', 'an', 'to', 'where', 'how', 'do', 'does', 'in', 'for', 'of', 'and', 'from', 'with', 'my', 'code', 'find', 'show', 'me', 'which', 'what', 'are', 'this', 'that', 'i', 'can', 'it'}


def tokens(value: str) -> list[str]:
    value = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', value).replace('_', ' ')
    return [word.lower() for word in TOKEN.findall(value) if len(word) > 1 and word.lower() not in STOP]


@dataclass(frozen=True)
class Symbol:
    path: str
    qualified_name: str
    kind: str
    line: int
    end_line: int
    signature: str
    docstring: str
    snippet: str
    language: str

    def public(self) -> dict:
        return asdict(self)

    @property
    def citation(self) -> str:
        return f'{self.path}:L{self.line}-L{self.end_line}'


def walk_python(tree: ast.AST, relative: str, lines: list[str]) -> Iterable[Symbol]:
    def visit(node: ast.AST, parents: tuple[str, ...] = ()) -> Iterable[Symbol]:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                name = '.'.join((*parents, child.name))
                kind = 'class' if isinstance(child, ast.ClassDef) else ('async function' if isinstance(child, ast.AsyncFunctionDef) else 'function')
                end = child.end_lineno or child.lineno
                snippet = '\n'.join(lines[child.lineno - 1:min(end, child.lineno + 17)])
                yield Symbol(relative, name, kind, child.lineno, end, lines[child.lineno - 1].strip()[:280], (ast.get_docstring(child) or '')[:550], snippet[:2000], 'python')
                yield from visit(child, (*parents, child.name))
            else:
                yield from visit(child, parents)
    yield from visit(tree)


class Index:
    """Read-only, bounded code index; never traverses symlinks or hidden build trees."""

    def __init__(self, root: str | Path):
        self.root = Path(root).expanduser().resolve(strict=True)
        if not self.root.is_dir():
            raise ValueError('Repository root must be a directory')
        self.symbols: list[Symbol] = []
        self.files: list[dict] = []
        self.files_scanned = 0
        self.bytes_scanned = 0
        self.parse_errors: list[str] = []
        self.imports: list[dict] = []
        self._docs: list[Counter[str]] = []
        self._df: Counter[str] = Counter()
        self._avg_length = 1.0
        self._index()

    def _paths(self) -> Iterable[Path]:
        for directory, directories, filenames in os.walk(self.root, followlinks=False):
            directories[:] = sorted(d for d in directories if d not in SKIP_DIRS and not d.startswith('.') and not (Path(directory) / d).is_symlink())
            for name in sorted(filenames):
                path = Path(directory) / name
                if not name.startswith('.') and path.suffix.lower() in EXTENSIONS and not path.is_symlink() and path.is_file():
                    yield path

    def _index(self) -> None:
        for path in self._paths():
            if self.files_scanned >= MAX_FILES or self.bytes_scanned >= MAX_TOTAL_BYTES:
                self.parse_errors.append('Index size limit reached; some files were not scanned')
                break
            try:
                size = path.stat().st_size
                if size > MAX_FILE_BYTES or size + self.bytes_scanned > MAX_TOTAL_BYTES:
                    continue
                content = path.read_text(encoding='utf-8')
                relative = path.relative_to(self.root).as_posix()
                lines = content.splitlines()
                before = len(self.symbols)
                if path.suffix.lower() == '.py':
                    tree = ast.parse(content, filename=relative)
                    self.symbols.extend(walk_python(tree, relative, lines))
                    self._read_imports(tree, relative)
                    language = 'python'
                else:
                    language = 'typescript' if path.suffix.lower() in {'.ts', '.tsx'} else 'javascript'
                    for match in JS_PATTERN.finditer(content):
                        name = match.group(1) or match.group(2)
                        line = content.count('\n', 0, match.start()) + 1
                        self.symbols.append(Symbol(relative, name, 'declaration', line, line, lines[line - 1].strip()[:280], '', '\n'.join(lines[line - 1:line + 11])[:1800], language))
                if len(self.symbols) == before and lines:
                    self.symbols.append(Symbol(relative, path.stem, 'module', 1, min(18, len(lines)), lines[0][:180], '', '\n'.join(lines[:18])[:1800], language))
                self.files.append({'path': relative, 'language': language, 'lines': len(lines), 'bytes': size, 'symbols': len(self.symbols) - before})
                self.files_scanned += 1
                self.bytes_scanned += size
            except (UnicodeError, OSError, SyntaxError, ValueError) as exc:
                self.parse_errors.append(f'{path.relative_to(self.root).as_posix()}: {type(exc).__name__}')
        self._docs = [Counter(tokens(' '.join([sym.qualified_name] * 4 + [sym.path] * 2 + [sym.signature, sym.docstring, sym.snippet]))) for sym in self.symbols]
        self._df = Counter(word for doc in self._docs for word in doc)
        self._avg_length = sum(sum(doc.values()) for doc in self._docs) / max(1, len(self._docs))

    def _read_imports(self, tree: ast.AST, path: str) -> None:
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for item in node.names:
                    self.imports.append({'source': path, 'target': item.name, 'line': node.lineno})
            elif isinstance(node, ast.ImportFrom):
                self.imports.append({'source': path, 'target': '.' * node.level + (node.module or ''), 'line': node.lineno})

    def search(self, question: str, limit: int = 6) -> list[dict]:
        if not 1 <= limit <= 30:
            raise ValueError('limit must be between 1 and 30')
        terms = set(tokens(question[:500]))
        if not terms:
            return []
        results = []
        n = len(self._docs)
        for sym, doc in zip(self.symbols, self._docs):
            length = sum(doc.values())
            score = 0.0
            for term in terms:
                if not doc[term]:
                    continue
                idf = math.log(1 + (n - self._df[term] + 0.5) / (self._df[term] + 0.5))
                tf = doc[term]
                score += idf * (tf * 2.2) / (tf + 1.2 * (0.25 + 0.75 * length / self._avg_length))
            if score:
                results.append((score, sym))
        results.sort(key=lambda result: (-result[0], result[1].path, result[1].line))
        return [{**sym.public(), 'score': round(score, 4), 'citation': sym.citation} for score, sym in results[:limit]]

    def file_content(self, relative: str) -> dict:
        """Only return previously indexed, non-symlink source files."""
        if relative not in {item['path'] for item in self.files}:
            raise FileNotFoundError('File is not indexed')
        path = self.root / relative
        if any(part.is_symlink() for part in (path, *path.parents) if part != self.root.parent):
            raise FileNotFoundError('Symlinked source unavailable')
        if not path.resolve().is_relative_to(self.root):
            raise FileNotFoundError('File is outside the repository')
        if path.stat().st_size > MAX_FILE_BYTES:
            raise FileNotFoundError('File exceeds preview size limit')
        content = path.read_text(encoding='utf-8')
        return {'path': relative, 'content': content, 'lines': len(content.splitlines())}

    def graph(self, limit: int = 200) -> dict:
        if not 1 <= limit <= 500:
            raise ValueError('limit must be between 1 and 500')
        return {'nodes': sorted(item['path'] for item in self.files), 'edges': self.imports[:limit], 'truncated': len(self.imports) > limit, 'note': 'Python import declarations only; resolution and runtime dependencies are not inferred.'}

    def summary(self) -> dict:
        languages = Counter(item['language'] for item in self.files)
        return {'root': str(self.root), 'files_scanned': self.files_scanned, 'bytes_scanned': self.bytes_scanned, 'symbols_indexed': len(self.symbols), 'languages': dict(languages), 'imports_found': len(self.imports), 'parse_errors': self.parse_errors[:30]}
