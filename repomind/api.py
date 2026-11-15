"""RepoMind FastAPI application; intended for trusted, loopback-first development."""
from __future__ import annotations

from functools import lru_cache
import hmac
import os
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import __version__
from .llm import LLMUnavailable, answer
from .workspace import ImportErrorSafe, workspace

app = FastAPI(title='RepoMind AI', version=__version__, description='Evidence-first repository intelligence and optional grounded LLM answers')


class Question(BaseModel):
    question: str = Field(min_length=2, max_length=500)
    limit: int = Field(default=6, ge=1, le=12)


class GitHubImport(BaseModel):
    url: str = Field(min_length=20, max_length=250)


def authorize(x_api_key: str | None = Header(default=None)) -> None:
    required = os.getenv('REPOMIND_API_KEY', '')
    if required and (not x_api_key or not hmac.compare_digest(required, x_api_key)):
        raise HTTPException(status_code=401, detail='Invalid API key')


def safe_index():
    try:
        return workspace.index()
    except (RuntimeError, ValueError, OSError) as exc:
        raise HTTPException(status_code=503, detail='Workspace unavailable. Check REPOMIND_ROOT.') from exc


@app.get('/api/health')
@app.get('/health', include_in_schema=False)
def health():
    return {'status': 'ok', 'version': __version__}


@app.get('/api/config', dependencies=[Depends(authorize)])
def config():
    return {'llm_enabled': bool(os.getenv('REPOMIND_LLM_API_KEY', '').strip()), 'auth_enabled': bool(os.getenv('REPOMIND_API_KEY')), 'supported_extensions': ['.py', '.js', '.jsx', '.ts', '.tsx']}


@app.get('/api/overview', dependencies=[Depends(authorize)])
@app.get('/summary', dependencies=[Depends(authorize)], include_in_schema=False)
def overview():
    try:
        return workspace.info()
    except (RuntimeError, ValueError, OSError) as exc:
        raise HTTPException(status_code=503, detail='Workspace unavailable. Check REPOMIND_ROOT.') from exc


@app.get('/api/files', dependencies=[Depends(authorize)])
def files():
    return {'files': safe_index().files}


@app.get('/api/file', dependencies=[Depends(authorize)])
def file_content(path: str = Query(min_length=1, max_length=500)):
    try:
        return safe_index().file_content(path)
    except (OSError, UnicodeError, ValueError):
        raise HTTPException(status_code=404, detail='File not available')


@app.get('/api/search', dependencies=[Depends(authorize)])
@app.get('/search', dependencies=[Depends(authorize)], include_in_schema=False)
def search(q: str = Query(min_length=2, max_length=500), limit: int = Query(default=8, ge=1, le=30)):
    return {'query': q, 'results': safe_index().search(q, limit)}


@app.get('/api/graph', dependencies=[Depends(authorize)])
@app.get('/graph', dependencies=[Depends(authorize)], include_in_schema=False)
def graph(limit: int = Query(default=200, ge=1, le=500)):
    return safe_index().graph(limit)


@app.post('/api/chat', dependencies=[Depends(authorize)])
@app.post('/ask', dependencies=[Depends(authorize)], include_in_schema=False)
def chat(request: Question):
    hits = safe_index().search(request.question, request.limit)
    try:
        return answer(request.question, hits)
    except LLMUnavailable as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post('/api/reindex', dependencies=[Depends(authorize)])
@app.post('/reindex', dependencies=[Depends(authorize)], include_in_schema=False)
def reindex():
    try:
        return workspace.reindex()
    except (RuntimeError, ValueError, OSError) as exc:
        raise HTTPException(status_code=503, detail='Index rebuild failed') from exc


@app.post('/api/import-github', dependencies=[Depends(authorize)])
def import_github(request: GitHubImport):
    try:
        return workspace.import_github(request.url)
    except ImportErrorSafe as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post('/api/use-local', dependencies=[Depends(authorize)])
def use_local():
    return workspace.use_local()


ROOT = Path(__file__).parent
DIST = ROOT.parent / 'frontend' / 'dist'
STATIC = ROOT / 'static'
if (DIST / 'assets').is_dir():
    app.mount('/assets', StaticFiles(directory=DIST / 'assets'), name='assets')


@app.get('/', include_in_schema=False)
def home():
    return FileResponse(DIST / 'index.html' if (DIST / 'index.html').is_file() else STATIC / 'index.html')


@app.get('/{path:path}', include_in_schema=False)
def spa(path: str):
    if path.startswith(('api/', 'docs', 'redoc', 'openapi.json', 'assets/')):
        raise HTTPException(status_code=404)
    return home()
