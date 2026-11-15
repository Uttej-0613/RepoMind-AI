"""Read-only API for locally configured repository analysis.

Never accept arbitrary filesystem roots from HTTP clients.
"""
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from .core import answer, index_repository

app = FastAPI(title="RepoMind AI", version="1.0.0")

class Query(BaseModel):
    question: str = Field(min_length=2, max_length=1000)
    limit: int = Field(default=5, ge=1, le=25)

def configured_root() -> Path:
    raw = os.getenv("REPOMIND_ROOT")
    if not raw:
        raise HTTPException(status_code=503, detail="REPOMIND_ROOT is not configured")
    root = Path(raw).expanduser().resolve()
    if not root.is_dir():
        raise HTTPException(status_code=503, detail="Configured repository is unavailable")
    return root

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/symbols")
def symbols():
    return {"symbols": [chunk.as_dict() for chunk in index_repository(configured_root())]}

@app.post("/ask")
def ask(query: Query):
    return answer(configured_root(), query.question, query.limit)
