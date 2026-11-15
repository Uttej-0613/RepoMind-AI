# Engineering Notes — RepoMind AI v2

## Architecture and data lifecycle

RepoMind is a **single-user, local-first code intelligence application**. The React/Vite client makes JSON requests to the FastAPI server. The backend owns the source-index lifecycle and optional LLM provider call; no provider secret is ever returned to the browser.

- **Local mode:** an explicitly configured `REPOMIND_ROOT` directory (default `.`) is read-only to the analyzer. No repository code is imported or executed.
- **Public GitHub import:** the UI sends a strict `https://github.com/{owner}/{repo}` URL. The backend fetches the public GitHub ZIP from a fixed API host, applies compressed/extracted size and path controls, and stores only supported source files under `.repomind-data/repositories`.
- **Indexing:** `os.walk` excludes dependencies, hidden build directories, and symlinks. Python symbols use built-in `ast`, with qualified method names. JS/TS symbols use regex heuristics; this is not sound parsing.
- **Search:** a bounded BM25-inspired lexical ranking scores names, signatures, paths, docstrings and snippets. Only positive matches are returned, with explicit file + line span citations.
- **Chat:** optional hosted LLM answers use up to five retrieved snippets in a fixed system prompt. Without a key, the same endpoint returns evidence mode. The code intentionally does **not** claim hallucination-proof results.
- **Files:** previews require a path in the index's allowlist and a non-symlink source that remains inside the configured root.

## Threat model

| Risk | Control / residual risk |
| --- | --- |
| Directory traversal through HTTP file preview | Resolve only exact, previously indexed paths; reject symlinks and out-of-root files. TOCTOU races remain possible under concurrent malicious local filesystem writes. |
| ZipSlip / malicious GitHub repository archive | Strict GitHub URL parser and fixed API host; reject `..`, skip symlinks, size-bound extraction, ignore unsupported source formats. Requires trusted GitHub TLS and download infrastructure. |
| Zip bombs and memory exhaustion | Limit compressed download to 12 MB, archive entries to 10,000, individual source files to 256 KB, indexed source to 16 MB, source file count to 1,500. In-memory index still consumes memory proportional to stored symbols. |
| Code execution / dependency installation | No runtime import of indexed Python, no Git checkout, no hooks, no `npm install` in imported repositories. |
| Prompt injection from repository contents | Code appears in a delimited *untrusted evidence* section; system prompt instructs model to ignore repository instructions. Not a formal guarantee. |
| Accidental sharing of sensitive source | Hosted inference disabled by default; no outbound inference call without backend key. Users are responsible for the repositories and snippets they choose to send. |
| API exposure | Bind API to localhost, optional constant-time API key check, no wildcard CORS. No rate limiting or SSO; do not expose to untrusted networks. |
| UI XSS through source code | React renders source as escaped text, never through `dangerouslySetInnerHTML`. |
| Long-running indexing/import | Fixed file/byte limits; synchronous import currently blocks the request until complete. No distributed queue or per-user quotas. |

## Design tradeoffs

1. **Lexical retrieval instead of heavyweight embeddings:** deterministic and compatible with an 8 GB CPU laptop. Semantic recall across renamed/indirect concepts is limited.
2. **In-memory index instead of vector DB:** simpler, bounded, easy to reason about, no extra infrastructure. Rebuilding is needed after changes and is not incremental.
3. **Optional hosted LLM:** clean separation of evidence retrieval from generated interpretation. External inference has cost, latency, and privacy implications.
4. **GitHub ZIP instead of `git clone`:** read-only source snapshot without hooks, faster for small public repos and simple to size-bound. No Git history, branches, or private auth.
5. **Hybrid source parsing quality:** Python AST is robust; JS/TS regex is not a complete parser. A planned upgrade could use Tree-sitter with language-specific tests.
6. **Frontend built separately for local dev:** React HMR on 5173, FastAPI on 8000, same-origin in production. Docker multistage build includes the compiled bundle.

## Operational limits

- Browser session-only API key; no persistent login system.
- One active repository per server process. Multi-worker deployments would need shared state/index and concurrency control.
- Imported source is stored in a managed local data directory. Treat it as potentially untrusted data and do not execute it.
- Only the highest-ranked evidence is submitted to the hosted provider. The answer may omit relevant code that ranking did not retrieve.
- README examples assume Git is installed and that `D:\Projects` exists on Windows.

## Planned technical extensions

- Source-aware AST for JS/TS using Tree-sitter and tests for JSX/TSX.
- Incremental indexing and file watch / snapshot versioning.
- Retrieval evaluation with labeled repository questions and coverage metrics.
- Embedding-based optional hybrid retrieval with privacy controls.
- Authenticated multi-user isolation and rate limiting for public deployment.
- End-to-end browser tests and visual regression snapshots.

**Verification discipline:** report backend unit/API tests separately from frontend build tests, real API-provider integration, security audits, and deployment checks. Do not describe unperformed checks as passed.
