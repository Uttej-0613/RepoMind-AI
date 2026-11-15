# RepoMind AI

**Local-first codebase intelligence with verifiable source citations.**

RepoMind indexes Python functions and classes with Python's AST, searches relevant symbols, and returns file paths and line numbers. The core engine runs without an API key or GPU.

## Features
- Python AST function/class extraction
- Deterministic lexical relevance ranking
- File and line-level citations
- Command-line interface and read-only FastAPI
- Bounded indexing, hidden-directory exclusions, no arbitrary path input over HTTP
- Automated unit and API tests, GitHub Actions CI

## Quick start

Requires Python 3.10+.

```bash
python -m pip install -e '.[dev]'
python -m pytest -q
repomind . --ask "where is authentication implemented?"
```

Start API after configuring a trusted local directory:

```bash
export REPOMIND_ROOT=/absolute/path/to/repository
uvicorn repomind.api:app --reload
```

Windows PowerShell: `$env:REPOMIND_ROOT="D:\\Projects\\MyRepo"`

Open `http://127.0.0.1:8000/docs` for interactive API documentation.

Example request:

```bash
curl -X POST http://127.0.0.1:8000/ask -H "Content-Type: application/json" -d '{"question":"find login validation"}'
```

## Architecture
`repository -> safe Python file discovery -> AST symbol extraction -> lexical search -> cited excerpts -> CLI/API`

## Limitations
This release is **not a generative RAG assistant**. Its response is evidence retrieval, not LLM-generated explanations. It currently supports Python source files only, uses in-memory indexing, and is intended for trusted local use. Do not expose the API publicly without authentication, rate limiting, and resource controls. Never index repositories containing secrets you do not intend to inspect.

## Roadmap
- Hybrid semantic + lexical retrieval with measurable evaluation
- Grounded LLM responses with citation validation
- JavaScript/TypeScript parsing
- Incremental indexing, repository isolation, authentication
- React frontend, deployment, observability

## License
MIT
