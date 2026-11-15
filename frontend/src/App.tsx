import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import {
  Activity, ArrowDownRight, ArrowLeft, ArrowRight, ArrowUpRight, BarChart3,
  BookOpen, Braces, Check, ChevronDown, ChevronRight, CircleHelp, Clipboard,
  Command, Database, ExternalLink, FileCode2, FileText, Files, Folder,
  GitBranch, GitFork, Github, Globe2, Layers3, LayoutDashboard, LockKeyhole,
  Menu, MessageSquareCode, Network, RefreshCw, Search,
  Send, Settings2, ShieldCheck, Sparkles, TerminalSquare, X, Zap
} from 'lucide-react'
import { type ChatResult, type Config, type Graph, type Overview, type SourceHit, request } from './api'

type Tab = 'overview' | 'assistant' | 'explorer' | 'dependencies' | 'settings'

const menu: { id: Tab; label: string; icon: typeof LayoutDashboard }[] = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  { id: 'assistant', label: 'AI Assistant', icon: MessageSquareCode },
  { id: 'explorer', label: 'Code Explorer', icon: Files },
  { id: 'dependencies', label: 'Dependencies', icon: Network },
  { id: 'settings', label: 'Settings', icon: Settings2 }
]
const suggestions = [
  { label: 'Authentication', query: 'Where is authentication and authorization handled?', icon: ShieldCheck },
  { label: 'Architecture', query: 'What are the main entry points and API routes?', icon: Layers3 },
  { label: 'Error handling', query: 'How are errors and exceptions handled?', icon: Activity },
  { label: 'Data access', query: 'Where is data read, validated, and stored?', icon: Database }
]
const format = (number: number) => new Intl.NumberFormat('en-US').format(number)

function shortPath(path: string, max = 48) { return path.length > max ? `…${path.slice(-max)}` : path }
function languageBadge(language: string) { return language === 'python' ? 'PY' : language === 'typescript' ? 'TS' : 'JS' }
function copyText(text: string) { return navigator.clipboard?.writeText(text).catch(() => undefined) }

function Pill({ children, variant = 'blue' }: { children: ReactNode; variant?: 'blue' | 'green' | 'muted' | 'amber' }) {
  return <span className={`pill pill-${variant}`}>{children}</span>
}

function IconTile({ children, tone = 'blue' }: { children: ReactNode; tone?: string }) {
  return <span className={`icon-tile tone-${tone}`}>{children}</span>
}

function SectionHeader({ eyebrow, title, description, action }: { eyebrow: string; title: string; description?: string; action?: ReactNode }) {
  return <div className="section-header"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1>{description && <p className="section-description">{description}</p>}</div>{action}</div>
}

function SourceCard({ hit, onOpen }: { hit: SourceHit; onOpen: (path: string) => void }) {
  const [copied, setCopied] = useState(false)
  const copy = async () => { await copyText(hit.citation); setCopied(true); window.setTimeout(() => setCopied(false), 1600) }
  return <article className="source-card">
    <div className="source-card-heading"><div className="source-title"><span className="file-icon"><Braces size={15} /></span><strong>{hit.qualified_name}</strong><span className="symbol-kind">{hit.kind}</span></div><span className="relevance">{hit.score.toFixed(2)} score</span></div>
    <div className="source-path">{hit.path}<span className="source-path-accent">:L{hit.line}–L{hit.end_line}</span></div>
    {hit.docstring && <p className="source-doc">{hit.docstring}</p>}
    <pre className="snippet"><code>{hit.snippet}</code></pre>
    <div className="source-actions"><button className="text-btn" type="button" onClick={() => onOpen(hit.path)}><FileCode2 size={14} /> Open source <ArrowUpRight size={13} /></button><button type="button" className="text-btn muted-btn" onClick={copy}>{copied ? <Check size={14} /> : <Clipboard size={14} />}{copied ? 'Copied' : 'Copy citation'}</button></div>
  </article>
}

function EmptyState({ icon, title, description }: { icon: ReactNode; title: string; description: string }) {
  return <div className="empty-state"><span className="empty-icon">{icon}</span><h3>{title}</h3><p>{description}</p></div>
}

export default function App() {
  const [tab, setTab] = useState<Tab>('overview')
  const [apiKey, setApiKey] = useState(() => sessionStorage.getItem('repomind_api_key') || '')
  const [overview, setOverview] = useState<Overview | null>(null)
  const [config, setConfig] = useState<Config | null>(null)
  const [graph, setGraph] = useState<Graph | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState('')
  const [mobileOpen, setMobileOpen] = useState(false)
  const [importOpen, setImportOpen] = useState(false)
  const [githubUrl, setGithubUrl] = useState('https://github.com/Uttej-0613/RepoMind-AI')
  const [query, setQuery] = useState('')
  const [conversation, setConversation] = useState<{ question: string; response: ChatResult }[]>([])
  const [fileFilter, setFileFilter] = useState('')
  const [selectedFile, setSelectedFile] = useState<string | null>(null)
  const [preview, setPreview] = useState<{ path: string; content: string; lines: number } | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [dependencyFilter, setDependencyFilter] = useState('')

  const refresh = useCallback(async () => {
    try {
      const [nextOverview, nextConfig] = await Promise.all([
        request<Overview>('/api/overview', apiKey),
        request<Config>('/api/config', apiKey)
      ])
      setOverview(nextOverview); setConfig(nextConfig); setError('')
    } catch (e) { setError((e as Error).message) }
  }, [apiKey])

  useEffect(() => { void refresh() }, [refresh])
  useEffect(() => {
    if (tab !== 'dependencies') return
    request<Graph>('/api/graph', apiKey).then(setGraph).catch(e => setError((e as Error).message))
  }, [tab, apiKey, overview?.name])
  useEffect(() => {
    if (!selectedFile) { setPreview(null); return }
    let cancelled = false
    setPreviewLoading(true)
    request<{ path: string; content: string; lines: number }>(`/api/file?path=${encodeURIComponent(selectedFile)}`, apiKey)
      .then(result => { if (!cancelled) { setPreview(result); setError('') } })
      .catch(e => { if (!cancelled) { setPreview(null); setError((e as Error).message) } })
      .finally(() => { if (!cancelled) setPreviewLoading(false) })
    return () => { cancelled = true }
  }, [selectedFile, apiKey, overview?.name])

  const openSource = (path: string) => { setSelectedFile(path); setTab('explorer'); setMobileOpen(false) }
  const go = (id: Tab) => { setTab(id); setMobileOpen(false); setError('') }
  const saveApiKey = (key: string) => { setApiKey(key); sessionStorage.setItem('repomind_api_key', key) }

  const perform = async (name: string, task: () => Promise<unknown>) => {
    setBusy(name); setError('')
    try { await task() } catch (e) { setError((e as Error).message) } finally { setBusy('') }
  }

  const importRepo = () => void perform('import', async () => {
    const next = await request<Overview>('/api/import-github', apiKey, { method: 'POST', body: JSON.stringify({ url: githubUrl.trim() }) })
    setOverview(next); setSelectedFile(null); setPreview(null); setGraph(null); setConversation([]); setImportOpen(false); setTab('overview')
  })
  const localRepo = () => void perform('local', async () => {
    const next = await request<Overview>('/api/use-local', apiKey, { method: 'POST' })
    setOverview(next); setSelectedFile(null); setGraph(null); setConversation([]); setTab('overview')
  })
  const reindex = () => void perform('reindex', async () => {
    const next = await request<Overview>('/api/reindex', apiKey, { method: 'POST' })
    setOverview(next); setGraph(null)
  })

  const ask = (question = query) => {
    const text = question.trim(); if (text.length < 2 || busy) return
    setQuery(text); setTab('assistant')
    void perform('chat', async () => {
      const response = await request<ChatResult>('/api/chat', apiKey, { method: 'POST', body: JSON.stringify({ question: text, limit: 8 }) })
      setConversation(previous => [{ question: text, response }, ...previous].slice(0, 12))
      setQuery('')
    })
  }

  const filteredFiles = useMemo(() => (overview?.files || []).filter(file => file.path.toLowerCase().includes(fileFilter.toLowerCase())), [overview, fileFilter])
  const filteredEdges = useMemo(() => (graph?.edges || []).filter(edge => `${edge.source} ${edge.target}`.toLowerCase().includes(dependencyFilter.toLowerCase())), [graph, dependencyFilter])
  const languageEntries = useMemo(() => Object.entries(overview?.languages || {}).sort((a, b) => b[1] - a[1]), [overview])
  const symbols = overview?.symbols_indexed ?? 0
  const allFiles = overview?.files || []

  return <div className="app-shell">
    <aside className={`sidebar ${mobileOpen ? 'sidebar-open' : ''}`}>
      <div className="brand"><div className="brand-mark"><Braces size={23} strokeWidth={2.6} /></div><div><div className="brand-name">RepoMind<span>AI</span></div><div className="brand-sub">CODE INTELLIGENCE</div></div><button className="sidebar-close mobile-only" aria-label="Close menu" onClick={() => setMobileOpen(false)}><X size={19}/></button></div>
      <div className="sidebar-group-label">WORKSPACE</div>
      <nav aria-label="Main navigation" className="sidebar-nav">{menu.map(({ id, label, icon: Icon }) => <button type="button" key={id} className={`nav-link ${tab === id ? 'active' : ''}`} onClick={() => go(id)}><Icon size={18} strokeWidth={1.9}/><span>{label}</span>{id === 'assistant' && <span className="nav-new">AI</span>}</button>)}</nav>
      <div className="sidebar-project"><div className="sidebar-group-label">ACTIVE REPOSITORY</div><div className="project-picker"><span className="project-avatar"><GitBranch size={18}/></span><div><strong title={overview?.name || ''}>{overview?.name || 'No repository'}</strong><span>{overview ? `${format(overview.files_scanned)} indexed files` : 'Not connected'}</span></div><button aria-label="Import GitHub repository" onClick={() => setImportOpen(true)}><ChevronDown size={17}/></button></div></div>
      <div className="sidebar-spacer" />
      <div className="sidebar-note"><div className="sidebar-note-icon"><ShieldCheck size={17}/></div><strong>Privacy by default</strong><p>Code stays local unless you explicitly enable a hosted model.</p></div>
      <div className="sidebar-footer"><span className="status-dot"/> <span>{overview ? 'Index online' : 'Awaiting connection'}</span><span className="version">v2.0</span></div>
    </aside>
    {mobileOpen && <div className="mobile-shade" onClick={() => setMobileOpen(false)} />}

    <div className="main-shell">
      <header className="topbar"><div className="topbar-location"><button className="icon-button mobile-only" onClick={() => setMobileOpen(true)} aria-label="Open menu"><Menu size={21}/></button><span className="breadcrumb-home">Workspace</span><ChevronRight size={15}/><span className="breadcrumb-active">{menu.find(x => x.id === tab)?.label}</span></div><div className="topbar-right"><span className="topbar-chip"><span className="status-dot" /> LOCAL-FIRST</span><a className="icon-button" href="https://github.com/Uttej-0613/RepoMind-AI" target="_blank" rel="noopener noreferrer" aria-label="GitHub repository"><Github size={19}/></a><button className="avatar" onClick={() => go('settings')} aria-label="Settings">UB</button></div></header>
      <main className="main-content">
        {error && <div role="alert" className="alert"><span><CircleHelp size={17}/>{error}</span><button aria-label="Dismiss error" onClick={() => setError('')}><X size={17}/></button></div>}

        {tab === 'overview' && <>
          <SectionHeader eyebrow="REPOSITORY INTELLIGENCE / 01" title="Codebase overview" description="A complete picture of your repository. Explore the structure, surface critical code, and investigate dependencies." action={<button className="button secondary" onClick={reindex} disabled={Boolean(busy)}><RefreshCw size={16} className={busy === 'reindex' ? 'spin' : ''}/> Re-index</button>}/>
          <div className="hero"><div className="hero-glow"/><div className="hero-copy"><div className="hero-label"><Sparkles size={14}/> YOUR AI ENGINEERING WORKSPACE</div><h2>Go from codebase to<br/><span>clarity.</span></h2><p>Ask questions about your repository, trace logic to its source, and understand complex code with evidence you can verify.</p><div className="hero-actions"><button className="button primary" onClick={() => go('assistant')}>Ask your codebase <ArrowRight size={17}/></button><button className="button ghost" onClick={() => setImportOpen(true)}><Github size={17}/> Import repository</button></div></div><div className="hero-visual" aria-hidden="true"><div className="hero-visual-top"><span className="terminal-dots">● ● ●</span><span>repo_analysis.py</span></div><div className="hero-visual-lines"><p><span>01</span> <i>def</i> <b>understand_code</b>(repo):</p><p><span>02</span> &nbsp;&nbsp; index = <em>analyze</em>(repo)</p><p><span>03</span> &nbsp;&nbsp; context = <em>retrieve</em>(index)</p><p><span>04</span> &nbsp;&nbsp; <i>return</i> <b>explain</b>(context)</p></div><div className="hero-analysis"><span className="analysis-mark"><Check size={13}/></span><div><strong>Analysis complete</strong><span>Source-grounded intelligence</span></div><Sparkles size={17}/></div></div></div>
          <div className="stats-grid"><div className="stat-card"><div className="stat-top"><span>Total files</span><IconTile><FileCode2 size={18}/></IconTile></div><div className="stat-value">{overview ? format(overview.files_scanned) : '—'}</div><div className="stat-bottom">Source files analyzed <ArrowUpRight size={13}/></div></div><div className="stat-card"><div className="stat-top"><span>Indexed symbols</span><IconTile tone="purple"><Braces size={18}/></IconTile></div><div className="stat-value">{overview ? format(symbols) : '—'}</div><div className="stat-bottom">Functions, classes & modules</div></div><div className="stat-card"><div className="stat-top"><span>Dependencies</span><IconTile tone="teal"><GitFork size={18}/></IconTile></div><div className="stat-value">{overview ? format(overview.imports_found) : '—'}</div><div className="stat-bottom">Python import references</div></div><div className="stat-card"><div className="stat-top"><span>Languages</span><IconTile tone="amber"><Layers3 size={18}/></IconTile></div><div className="stat-value">{overview ? languageEntries.length : '—'}</div><div className="stat-bottom">Across indexed source files</div></div></div>
          <div className="overview-grid"><section className="panel"><div className="panel-heading"><div><h3>Language breakdown</h3><p>Distribution of indexed source files</p></div><BarChart3 size={18}/></div>{languageEntries.length ? <div className="language-list">{languageEntries.map(([name, count], index) => <div key={name} className="language-item"><div className="language-label"><span className={`language-color color-${index % 3}`}/><strong>{name[0].toUpperCase() + name.slice(1)}</strong><span>{format(count)} files</span></div><div className="progress-track"><div className={`progress-fill progress-${index % 3}`} style={{width: `${Math.max(2, (count / (overview?.files_scanned || 1)) * 100)}%`}}/></div></div>)}</div> : <EmptyState icon={<BarChart3 size={26}/>} title="No language data" description="Index a source repository to get started."/>}<div className="panel-foot"><span>Indexed {overview ? (overview.bytes_scanned / 1024).toFixed(0) : '0'} KB of source</span><button className="text-btn" onClick={() => go('explorer')}>Explore files <ArrowRight size={14}/></button></div></section>
            <section className="panel"><div className="panel-heading"><div><h3>Repository files</h3><p>Your most discoverable source files</p></div><button className="text-btn" onClick={() => go('explorer')}>View all <ArrowRight size={14}/></button></div><div className="recent-list">{allFiles.slice(0, 6).map(file => <button key={file.path} className="recent-file" onClick={() => openSource(file.path)}><span className="recent-file-icon"><FileCode2 size={17}/></span><span><strong title={file.path}>{shortPath(file.path, 35)}</strong><small>{file.symbols} symbols · {file.lines} lines</small></span><ArrowUpRight size={15}/></button>)}{!allFiles.length && <EmptyState icon={<Files size={24}/>} title="No files yet" description="Import a public GitHub repository or use a local directory."/>}</div></section></div>
          {overview?.parse_errors.length ? <div className="notice"><CircleHelp size={16}/><span>{overview.parse_errors.length} files could not be analyzed. Check the API overview for details.</span></div> : null}
          <div className="bottom-prompt"><span className="bottom-prompt-icon"><Zap size={18}/></span><span><strong>Need an answer from the code?</strong><small>Ask a natural language question and inspect supporting source citations.</small></span><button className="button outline" onClick={() => go('assistant')}>Open assistant <ArrowRight size={15}/></button></div>
        </>}

        {tab === 'assistant' && <>
          <SectionHeader eyebrow="INTELLIGENT CODE SEARCH / 02" title="Ask RepoMind" description="Explore your repository with source-grounded answers. Every result links back to real code." action={<Pill variant={config?.llm_enabled ? 'green' : 'amber'}><span className="status-dot"/>{config?.llm_enabled ? 'LLM configured' : 'Evidence mode'}</Pill>}/>
          <div className="assistant-frame"><div className="assistant-welcome"><div className="assistant-orbit"><Sparkles size={30}/></div><h2>What would you like to understand?</h2><p>Ask about architecture, function behavior, data flow, or implementation details. RepoMind retrieves the most relevant source code.</p></div><div className="question-composer"><textarea id="question-composer" aria-label="Ask a repository question" rows={3} placeholder="e.g. Where is authentication handled in this codebase?" value={query} maxLength={500} onChange={e => setQuery(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); ask() } }}/><div className="composer-bottom"><span><Command size={13}/> Ctrl + Enter to send</span><button className="button primary" onClick={() => ask()} disabled={busy === 'chat' || query.trim().length < 2}>{busy === 'chat' ? <RefreshCw className="spin" size={16}/> : <Send size={16}/>} {busy === 'chat' ? 'Analyzing…' : 'Ask RepoMind'}</button></div></div></div>
          {conversation.length === 0 ? <><div className="suggestion-header">SUGGESTED QUESTIONS</div><div className="suggestions">{suggestions.map(({ label, query: value, icon: Icon }) => <button key={label} className="suggestion" onClick={() => ask(value)}><span><Icon size={19}/></span><strong>{label}</strong><small>{value}</small><ArrowUpRight className="suggestion-arrow" size={16}/></button>)}</div></> : <div className="conversation">{conversation.map((item, index) => <section className="conversation-item" key={`${item.question}-${index}`}><div className="question-line"><span className="question-avatar">UB</span><h3>{item.question}</h3></div><div className="answer-panel"><div className="answer-heading"><span className="answer-logo"><Sparkles size={17}/></span><strong>RepoMind</strong><Pill variant={item.response.mode === 'llm' ? 'green' : 'amber'}>{item.response.mode === 'llm' ? 'Grounded AI response' : 'Evidence retrieval'}</Pill></div><div className="answer-body">{item.response.answer}</div><p className="answer-disclaimer">{item.response.mode === 'llm' ? 'Generated interpretations can be inaccurate. Verify claims in the citations below.' : 'No hosted model was used. These are ranked source locations, not a generated explanation.'}</p><div className="sources-label"><BookOpen size={16}/> SOURCES <span>{item.response.results.length}</span></div><div className="sources-grid">{item.response.results.length ? item.response.results.map(hit => <SourceCard key={hit.citation + hit.qualified_name} hit={hit} onOpen={openSource}/>) : <EmptyState icon={<Search size={22}/>} title="No relevant source found" description="Try function names, module paths, or a more focused question."/>}</div></div></section>)}</div>}
        </>}

        {tab === 'explorer' && <>
          <SectionHeader eyebrow="SOURCE NAVIGATION / 03" title="Code explorer" description="Browse indexed files and inspect source with precise line numbers and symbol counts." action={<Pill>{format(allFiles.length)} source files</Pill>}/>
          <div className="explorer-layout"><section className="panel files-panel"><div className="panel-heading"><div><h3>File explorer</h3><p>Indexed source files</p></div><Folder size={18}/></div><label className="mini-search"><Search size={15}/><input aria-label="Filter files" value={fileFilter} placeholder="Filter by path…" onChange={e => setFileFilter(e.target.value)}/></label><div className="file-list">{filteredFiles.map(file => <button key={file.path} title={file.path} className={`file-row ${selectedFile === file.path ? 'selected' : ''}`} onClick={() => setSelectedFile(file.path)}><span className={`file-ext ${file.language}`}>{languageBadge(file.language)}</span><span className="file-row-name">{file.path}</span><ChevronRight size={14}/></button>)}{filteredFiles.length === 0 && <p className="file-empty">No matching files.</p>}</div><div className="files-panel-footer">Showing {filteredFiles.length} of {allFiles.length} files</div></section>
            <section className="panel preview-panel">{selectedFile ? <><div className="preview-heading"><div><div className="preview-title"><FileText size={18}/><strong title={selectedFile}>{shortPath(selectedFile, 75)}</strong></div><p>{preview ? `${preview.lines} lines · read-only source` : 'Loading source...'}</p></div><button className="icon-button" title="Copy source path" onClick={() => void copyText(selectedFile)}><Clipboard size={17}/></button></div>{previewLoading ? <div className="preview-placeholder">Loading source…</div> : preview ? <div className="code-viewer" role="region" aria-label="Source preview">{preview.content.split('\n').map((line, index) => <div className="code-line" key={index}><span className="line-number">{index + 1}</span><code>{line || ' '}</code></div>)}</div> : <EmptyState icon={<FileText size={26}/>} title="File unavailable" description="Select another indexed file."/>}</> : <EmptyState icon={<FileCode2 size={33}/>} title="Select a file to inspect" description="Choose a file from the explorer to view its full source with line numbers."/>}</section></div>
        </>}

        {tab === 'dependencies' && <>
          <SectionHeader eyebrow="STATIC DEPENDENCY INTELLIGENCE / 04" title="Dependency explorer" description="Discover relationships through Python import statements and navigate modules involved in your architecture." action={<Pill variant="muted">Static import map</Pill>}/>
          <div className="dependency-top"><div className="panel dependency-summary"><IconTile tone="teal"><GitFork size={19}/></IconTile><strong>{format(graph?.edges.length || 0)}</strong><span>Import references visible</span></div><div className="panel dependency-summary"><IconTile tone="purple"><FileCode2 size={19}/></IconTile><strong>{format(graph?.nodes.length || 0)}</strong><span>Indexed source files</span></div><div className="panel dependency-summary"><IconTile tone="amber"><Network size={19}/></IconTile><strong>{graph?.truncated ? 'Yes' : 'No'}</strong><span>Results truncated</span></div></div>
          <section className="panel dependencies-panel"><div className="panel-heading"><div><h3>Import relationships</h3><p>Each row represents a syntactic import declaration in a Python source file.</p></div><GitBranch size={20}/></div><label className="mini-search"><Search size={15}/><input aria-label="Filter dependencies" value={dependencyFilter} placeholder="Filter module or import…" onChange={e => setDependencyFilter(e.target.value)}/></label><div className="dependency-table"><div className="table-head"><span>SOURCE MODULE</span><span>IMPORTED MODULE</span><span>LINE</span></div>{filteredEdges.length ? filteredEdges.slice(0, 200).map((edge, index) => <button key={`${edge.source}-${edge.target}-${index}`} className="dependency-row" onClick={() => openSource(edge.source)}><span><FileCode2 size={15}/>{shortPath(edge.source, 45)}</span><span><ArrowDownRight size={14}/>{edge.target}</span><span>L{edge.line}</span></button>) : <EmptyState icon={<Network size={25}/>} title="No matching imports" description="Import references are extracted from Python source AST nodes."/>}</div><p className="dependency-note"><CircleHelp size={16}/> {graph?.note || 'This view shows static Python imports only, not a resolved runtime dependency graph.'}</p></section>
        </>}

        {tab === 'settings' && <>
          <SectionHeader eyebrow="WORKSPACE CONFIGURATION / 05" title="Settings" description="Manage your active repository, API authentication, and development setup."/>
          <div className="settings-grid"><section className="panel settings-panel"><div className="panel-heading"><div><h3>Active repository</h3><p>Index local source or import a public GitHub repository.</p></div><GitBranch size={19}/></div><div className="setting-current"><span className="setting-current-icon"><Folder size={19}/></span><span><strong>{overview?.name || 'Not available'}</strong><small>{overview?.root || 'Workspace not configured'}</small></span></div><div className="setting-actions"><button className="button primary" onClick={() => setImportOpen(true)}><Github size={16}/> Import GitHub URL</button><button className="button secondary" onClick={localRepo} disabled={Boolean(busy)}><ArrowLeft size={16}/> Use local</button></div><p className="setting-help">Public imports are bounded by file count, source size, and archive size. GitHub sources are treated as untrusted text, never executed.</p></section>
            <section className="panel settings-panel"><div className="panel-heading"><div><h3>API authentication</h3><p>Only needed when REPOMIND_API_KEY is configured.</p></div><LockKeyhole size={19}/></div><label className="setting-label" htmlFor="api-key">Access key (this browser tab only)</label><input id="api-key" className="setting-input" type="password" value={apiKey} onChange={e => saveApiKey(e.target.value)} placeholder="Paste configured API key" autoComplete="off"/><p className="setting-help">Stored in sessionStorage for this tab. Never put your LLM provider key in the browser; configure it only on the backend.</p><div className="setting-actions"><button className="button secondary" onClick={() => void refresh()}><RefreshCw size={15}/> Test connection</button></div></section>
            <section className="panel settings-panel"><div className="panel-heading"><div><h3>LLM provider</h3><p>Optional OpenAI-compatible hosted explanation.</p></div><Sparkles size={19}/></div><div className="setting-status"><Pill variant={config?.llm_enabled ? 'green' : 'amber'}>{config?.llm_enabled ? 'Provider enabled' : 'No provider key'}</Pill><span>Without a key, the assistant returns ranked evidence without generating answers.</span></div><div className="code-setting">REPOMIND_LLM_API_KEY=your_server_side_key<br/>REPOMIND_LLM_MODEL=gpt-4o-mini</div><p className="setting-help">When enabled, up to five retrieved snippets are transmitted to the provider. Do not use confidential code without authorization.</p></section>
            <section className="panel settings-panel"><div className="panel-heading"><div><h3>Developer resources</h3><p>Inspect the API schema and project documentation.</p></div><TerminalSquare size={19}/></div><a className="resource-link" href="/docs" target="_blank" rel="noreferrer"><span><BookOpen size={17}/> Interactive API documentation</span><ExternalLink size={15}/></a><a className="resource-link" href="https://github.com/Uttej-0613/RepoMind-AI" target="_blank" rel="noreferrer"><span><Github size={17}/> Source repository & README</span><ExternalLink size={15}/></a><div className="settings-divider"/><p className="setting-help"><Globe2 size={14}/> API defaults to localhost. Authentication, HTTPS, monitoring and additional isolation are required for an internet deployment.</p></section></div>
        </>}
        <footer className="main-footer"><span>© 2026 RepoMind AI · Built for developers who value evidence.</span><span><ShieldCheck size={14}/> No repository code is executed</span></footer>
      </main>
    </div>
    {importOpen && <div className="modal-backdrop" role="presentation" onMouseDown={e => { if (e.target === e.currentTarget) setImportOpen(false) }}><div className="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title"><div className="modal-heading"><span className="modal-icon"><Github size={22}/></span><button aria-label="Close" className="icon-button" onClick={() => setImportOpen(false)}><X size={19}/></button></div><div className="eyebrow">CONNECT REPOSITORY</div><h2 id="modal-title">Import from GitHub</h2><p>Analyze a public GitHub repository without cloning or executing its dependencies. The source archive is scanned locally.</p><label htmlFor="github-url" className="setting-label">Public repository URL</label><div className="modal-input-wrap"><Github size={17}/><input id="github-url" value={githubUrl} onChange={e => setGithubUrl(e.target.value)} placeholder="https://github.com/owner/repository" onKeyDown={e => { if (e.key === 'Enter') importRepo() }}/></div><div className="modal-detail"><ShieldCheck size={16}/> Python, JavaScript and TypeScript source only. Size and traversal limits enforced.</div><div className="modal-actions"><button className="button secondary" onClick={() => setImportOpen(false)}>Cancel</button><button className="button primary" disabled={Boolean(busy)} onClick={importRepo}>{busy === 'import' ? <RefreshCw className="spin" size={16}/> : <ArrowRight size={16}/>} {busy === 'import' ? 'Importing…' : 'Analyze repository'}</button></div></div></div>}
  </div>
}
