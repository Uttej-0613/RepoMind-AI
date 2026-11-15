"""Workspace management: local default or bounded, public GitHub ZIP import.

No git hooks, build scripts, or repository source code are executed.
"""
from __future__ import annotations

import io
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import threading
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import zipfile

from .core import EXTENSIONS, MAX_FILES, MAX_FILE_BYTES, MAX_TOTAL_BYTES, SKIP_DIRS, Index

MAX_ARCHIVE_BYTES = 12_000_000
MAX_ARCHIVE_ENTRIES = 10_000
GITHUB_URL = re.compile(r'^https://github\.com/([A-Za-z0-9][A-Za-z0-9-]{0,38})/([A-Za-z0-9_.-]{1,100})(?:/)?$')


class ImportErrorSafe(ValueError):
    """User-facing, non-sensitive import failure."""


def parse_github_url(url: str) -> tuple[str, str]:
    match = GITHUB_URL.fullmatch(url.strip())
    if not match:
        raise ImportErrorSafe('Enter a public repository URL like https://github.com/owner/repo')
    owner, name = match.groups()
    return owner, name.removesuffix('.git')


def download_github_archive(owner: str, repo: str) -> bytes:
    req = Request(f'https://api.github.com/repos/{owner}/{repo}/zipball', headers={'Accept': 'application/vnd.github+json', 'User-Agent': 'RepoMind-AI/2.0'})
    try:
        with urlopen(req, timeout=30) as response:
            content_length = response.headers.get('Content-Length')
            if content_length and int(content_length) > MAX_ARCHIVE_BYTES:
                raise ImportErrorSafe('Repository archive exceeds 12 MB compressed limit')
            data = response.read(MAX_ARCHIVE_BYTES + 1)
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise ImportErrorSafe('GitHub download failed. Check the public URL and your network connection.') from exc
    if len(data) > MAX_ARCHIVE_BYTES:
        raise ImportErrorSafe('Repository archive exceeds 12 MB compressed limit')
    return data


def extract_source_archive(data: bytes, target: Path) -> int:
    """Extract only bounded source files, rejecting traversal and archive symlinks."""
    target.mkdir(parents=True, exist_ok=True)
    imported = 0
    total_bytes = 0
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            members = archive.infolist()
            if len(members) > MAX_ARCHIVE_ENTRIES:
                raise ImportErrorSafe('Archive has too many entries')
            for member in members:
                if member.is_dir():
                    continue
                parts = Path(member.filename).parts
                if len(parts) < 2 or any(p in ('', '.', '..') for p in parts):
                    raise ImportErrorSafe('Unsafe archive path')
                relative = Path(*parts[1:])
                if relative.is_absolute() or any(p.startswith('.') or p in SKIP_DIRS for p in relative.parts):
                    continue
                if relative.suffix.lower() not in EXTENSIONS:
                    continue
                mode = (member.external_attr >> 16) & 0o170000
                if mode == 0o120000:
                    continue
                if member.file_size > MAX_FILE_BYTES:
                    continue
                if imported >= MAX_FILES or total_bytes + member.file_size > MAX_TOTAL_BYTES:
                    break
                destination = target / relative
                if not destination.resolve().is_relative_to(target.resolve()):
                    raise ImportErrorSafe('Unsafe archive path')
                destination.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member) as source, destination.open('wb') as output:
                    remaining = member.file_size + 1
                    while remaining:
                        block = source.read(min(64 * 1024, remaining))
                        if not block:
                            break
                        output.write(block)
                        remaining -= len(block)
                    if remaining <= 0:
                        destination.unlink(missing_ok=True)
                        raise ImportErrorSafe('Invalid archive entry size')
                imported += 1
                total_bytes += member.file_size
    except (zipfile.BadZipFile, OSError, RuntimeError) as exc:
        raise ImportErrorSafe('Invalid or unreadable GitHub repository archive') from exc
    if not imported:
        raise ImportErrorSafe('No supported Python, JavaScript, or TypeScript files found')
    return imported


class Workspace:
    def __init__(self, data_dir: Path | None = None):
        self.data_dir = (data_dir or Path(os.getenv('REPOMIND_DATA_DIR', '.repomind-data'))).expanduser().resolve()
        self._lock = threading.RLock()
        self._index: Index | None = None
        self._root: Path | None = None
        self._label: str | None = None

    def _resolve_root(self) -> tuple[Path, str]:
        if self._root is not None and self._label:
            return self._root, self._label
        meta = self.data_dir / 'active.json'
        if meta.is_file():
            try:
                info = json.loads(meta.read_text(encoding='utf-8'))
                owner, repo = parse_github_url(info['url'])
                root = (self.data_dir / 'repositories' / f'{owner}--{repo}').resolve()
                if root.is_dir():
                    return root, f'{owner}/{repo}'
            except (ValueError, OSError, KeyError, json.JSONDecodeError):
                pass
        root = Path(os.getenv('REPOMIND_ROOT', '.')).expanduser().resolve()
        if not root.is_dir():
            raise RuntimeError('REPOMIND_ROOT is not a directory')
        return root, root.name

    def index(self) -> Index:
        with self._lock:
            root, label = self._resolve_root()
            if self._index is None or self._index.root != root:
                self._index = Index(root)
            self._label = label
            return self._index

    def info(self) -> dict:
        with self._lock:
            index = self.index()
            return {**index.summary(), 'name': self._label, 'files': index.files[:MAX_FILES]}

    def reindex(self) -> dict:
        with self._lock:
            self._index = None
            return self.info()

    def import_github(self, url: str) -> dict:
        owner, repo = parse_github_url(url)
        data = download_github_archive(owner, repo)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        repos_dir = self.data_dir / 'repositories'
        repos_dir.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='import-', dir=self.data_dir) as temp:
            staging = Path(temp) / 'source'
            extract_source_archive(data, staging)
            new_index = Index(staging)
            destination = repos_dir / f'{owner}--{repo}'
            with self._lock:
                if destination.exists():
                    shutil.rmtree(destination)
                shutil.move(str(staging), str(destination))
                meta_temp = self.data_dir / 'active.tmp'
                meta_temp.write_text(json.dumps({'url': f'https://github.com/{owner}/{repo}'}), encoding='utf-8')
                os.replace(meta_temp, self.data_dir / 'active.json')
                self._root = destination.resolve()
                self._label = f'{owner}/{repo}'
                self._index = Index(self._root)
                return self.info()

    def use_local(self) -> dict:
        with self._lock:
            (self.data_dir / 'active.json').unlink(missing_ok=True)
            self._root = None
            self._label = None
            self._index = None
            return self.info()


workspace = Workspace()
