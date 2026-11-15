export interface SourceHit {
  path: string
  qualified_name: string
  kind: string
  line: number
  end_line: number
  signature: string
  docstring: string
  snippet: string
  language: string
  score: number
  citation: string
}
export interface FileEntry {
  path: string
  language: string
  lines: number
  bytes: number
  symbols: number
}
export interface Overview {
  root: string
  name: string
  files_scanned: number
  bytes_scanned: number
  symbols_indexed: number
  imports_found: number
  languages: Record<string, number>
  parse_errors: string[]
  files: FileEntry[]
}
export interface ChatResult {
  mode: 'evidence' | 'llm'
  answer: string
  citations: string[]
  results: SourceHit[]
}
export interface Graph {
  nodes: string[]
  edges: { source: string; target: string; line: number }[]
  truncated: boolean
  note: string
}
export interface Config {
  llm_enabled: boolean
  auth_enabled: boolean
  supported_extensions: string[]
}

export async function request<T>(path: string, apiKey = '', init: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      ...(init.body ? { 'Content-Type': 'application/json' } : {}),
      ...(apiKey ? { 'X-API-Key': apiKey } : {}),
      ...init.headers
    }
  })
  const data: unknown = await response.json().catch(() => null)
  if (!response.ok) {
    const detail = (data && typeof data === 'object' && 'detail' in data) ? String((data as {detail: unknown}).detail) : `HTTP ${response.status}`
    throw new Error(detail)
  }
  return data as T
}
