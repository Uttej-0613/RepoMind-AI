# RepoMind AI

**An end-to-end, local-first codebase intelligence workbench.**

RepoMind helps developers understand unfamiliar Python, JavaScript, and TypeScript repositories through symbol discovery, grounded code retrieval, source navigation, and optional hosted-model explanations. It contains a **React + TypeScript frontend**, **FastAPI backend**, safe public-GitHub import, unit/API/security tests, Docker Compose, and GitHub Actions CI.

> **Privacy and accuracy:** The analysis engine runs on CPU without an API key. When no hosted model is configured, the assistant transparently returns ranked code evidence instead of claiming to generate an AI answer. With an LLM API key, selected source snippets leave your machine. Review all model responses against their source citations.

## Application

| Area | Functionality |
| --- | --- |
| Overview | File counts, indexed symbols, import references, language distribution, recent files |
| AI Assistant | Ask natural-language questions, see relevant code and file-line citations; optional grounded hosted LLM |
| Code Explorer | Browse indexed source files, filter paths, and inspect source with line numbers |
| Dependencies | Explore static Python import declarations, filter and jump to source |
| Repository Import | Load bounded source files from a **public** GitHub repository archive without executing them |
| Settings | Switch to local repository, configure session-only API access key, view API/LLM status |

**Supported source extensions:** `.py`, `.js`, `.jsx`, `.ts`, `.tsx`.

Python functions, methods and classes are parsed with `ast`; JavaScript/TypeScript declaration discovery is **best-effort heuristic parsing**, not an AST-based language service. Search uses explainable BM25-inspired lexical ranking; this release does **not** claim embedding/vector search or autonomous code modification.

## Requirements

- Python **3.10+**, Node.js **20.19+ / 22+**, npm, Git
- No GPU required. A laptop with **8 GB RAM** is sufficient for the core workload.
- Internet is required to install packages, import public GitHub repositories, or use hosted inference.

## Windows PowerShell — run the entire application

```powershell
cd D:\Projects
git clone https://github.com/Uttej-0613/RepoMind-AI.git
cd RepoMind-AI
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m uvicorn repomind.api:app --host 127.0.0.1 --port 8000 --reload
```

Keep the backend terminal running. Open **a second PowerShell terminal**:

```powershell
cd D:\Projects\RepoMind-AI\frontend
npm install
npm run dev
```

Open **http://127.0.0.1:5173** for the React app. The development server proxies API requests to `http://127.0.0.1:8000`. Interactive API documentation is at **http://127.0.0.1:8000/docs**.

The default local repository is the directory you launched the backend from. To analyze another authorized local folder, set this in the backend terminal **before launching uvicorn**:

```powershell
$env:REPOMIND_ROOT = "D:\Projects\StockAI"
```

Or click **Import repository** in the UI to index a public GitHub URL. GitHub imports are cached in `.repomind-data` within your backend working directory and persist across restarts. Click **Use local** in Settings to switch back.

### Production-style local build (single port)

```powershell
cd D:\Projects\RepoMind-AI\frontend
npm install
npm run build
cd ..
.\.venv\Scripts\python.exe -m uvicorn repomind.api:app --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000**. FastAPI serves the built React assets from `frontend/dist`. Without built assets, the repository includes a small fallback HTML explorer; the React UI is the primary frontend.

### Docker Compose

```powershell
cd D:\Projects\RepoMind-AI
docker compose up --build
```

The Docker image builds React in a Node stage, serves the production UI from FastAPI, drops root privileges, mounts the selected local repository **read-only**, and retains imported source in a named `/data` volume. The server is published to **127.0.0.1:8000 only**. Set `REPO_PATH` in `.env` if you want Docker to inspect a different host folder. Docker Desktop must be installed separately.

## API

| Endpoint | Method | Purpose |
| --- | --- | --- |
| `/api/health` | GET | Health and version |
| `/api/config` | GET | Safe feature flags (no keys exposed) |
| `/api/overview` | GET | Workspace stats and indexed files |
| `/api/files` | GET | Indexed file list |
| `/api/file?path=...` | GET | Read an indexed source file |
| `/api/search?q=...&limit=8` | GET | Ranked source symbols |
| `/api/chat` | POST | Retrieved code evidence with optional hosted explanation |
| `/api/graph` | GET | Python import declarations |
| `/api/import-github` | POST | Import public GitHub source archive (`{"url":"https://github.com/owner/repo"}`) |
| `/api/use-local` | POST | Revert to configured local source directory |
| `/api/reindex` | POST | Rebuild current index |

Example question:

```json
{"question":"Where is token validation performed?","limit":6}
```

The chat response has `mode` (`evidence` or `llm`), `answer`, `citations`, and `results` containing snippets, symbols, scores, paths, and line spans.

## Optional hosted LLM

Backend environment variables (never put these in React source code):

```dotenv
REPOMIND_LLM_API_KEY=YOUR_PROVIDER_KEY
REPOMIND_LLM_MODEL=gpt-4o-mini
REPOMIND_LLM_URL=https://api.openai.com/v1/chat/completions
```

The provider must offer an **HTTPS OpenAI-compatible chat-completions endpoint**. The model receives the question and up to five retrieved code snippets, not the entire repository. The prompt instructs the model to treat repository text as untrusted data. **Model claims are not formally verified**, so citations should be reviewed by the developer. The app does not use or require a local GPU model.

If you configure `REPOMIND_API_KEY`, type the matching key in the React Settings page. It is held in browser session storage only; the LLM API key must remain on the backend.

## CLI

```powershell
.\.venv\Scripts\python.exe -m repomind.cli D:\Projects\StockAI --ask "where is the request handler"
.\.venv\Scripts\python.exe -m repomind.cli D:\Projects\StockAI --graph
```

## Architecture

```text
Frontend (React + TypeScript / Vite)
   │  /api/* (development proxy or same-origin production assets)
   ▼
FastAPI: config, repository import, overview, files, search, chat, graph
   │
   ├── Workspace: approved local root OR bounded public GitHub ZIP importer
   ├── Index: bounded source traversal → AST / JS/TS declaration heuristics
   ├── Retrieval: lexical BM25-inspired ranking → cited code snippets
   ├── LLM adapter (optional): HTTPS chat completion with constrained context
   └── Persistence: imported source snapshot, no user-account database
```

See [Engineering architecture and threat model](docs/ARCHITECTURE.md) for detailed decisions and operational limits.

## Quality, safety and limitations

- `python -m pytest -q` executes backend/API/security regression tests.
- `cd frontend && npm run build` performs TypeScript checking and Vite compilation.
- GitHub Actions checks Python 3.10, 3.12, 3.13 and builds the frontend on Node 22.
- Public GitHub archive imports are limited by compressed size, extracted source bytes, file count, per-file size, filename controls, and symlink traversal checks.
- The backend should **not be publicly exposed without** authentication, HTTPS, rate limits, audit logging, and additional sandboxing. Intended for personal, trusted development workstations.
- The importer supports only public GitHub repositories; private repositories, webhooks, collaborative workspaces, and real-time incremental sync are out of scope.
- No code execution, auto-fix, code editing, vector database, guaranteed semantic recall, full compiler-level JS/TS parsing, or resolved call graphs are claimed.
- Only known indexed source paths can be previewed. The UI renders code as text, not executable HTML.

## Suggested demonstration

1. Import `https://github.com/Uttej-0613/RepoMind-AI` in the UI.
2. Ask “Where are GitHub archives checked for unsafe paths?”
3. Open the returned source citation in Code Explorer and inspect its line numbers.
4. Open Dependencies to trace Python imports and use Settings to switch back to the local repository.

## License

MIT — see [LICENSE](LICENSE). Built by Bhasuru Uttej.
