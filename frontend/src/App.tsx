import { useEffect, useState } from 'react'
import type { FormEvent, KeyboardEvent } from 'react'
import './App.css'

type ApiStatus = 'checking' | 'online' | 'offline'
type AuthMode = 'login' | 'register'
type CurrentUser = { id: string; full_name: string; email: string; role: 'AUDITOR' | 'RESPONSIBLE' | 'ADMIN' }
type TestCaseData = {
  id: string; code: string; title: string; description: string; preconditions: string; steps: string
  test_data: string; expected_result: string; approval_criteria: string; author_name: string; responsible_email: string
}
type TestCaseForm = Omit<TestCaseData, 'id' | 'code' | 'author_name'>
type AuditItemData = { checklist_code: string; checklist_label: string; result: 'CONFORMING' | 'NONCONFORMING' | 'NOT_APPLICABLE' | null; note: string | null }
type AuditData = {
  id: string; test_case_id: string; test_case_code: string; test_case_title: string; auditor_name: string
  status: 'DRAFT' | 'COMPLETED'; adherence_percentage: number | null; nonconformity_count: number
  items: AuditItemData[]; created_at: string; completed_at: string | null
}

const blankTestCase = (responsibleEmail = ''): TestCaseForm => ({
  title: '', responsible_email: responsibleEmail, description: '', preconditions: '', steps: '', test_data: '', expected_result: '', approval_criteria: '',
})

const testCases = [
  { code: 'TC-014', title: 'Login com senha incorreta', author: 'André Murilo', adherence: 67, status: 'Não conforme', tone: 'danger' },
  { code: 'TC-013', title: 'Recuperação de acesso', author: 'Marcelo Bellon', adherence: 100, status: 'Conforme', tone: 'success' },
  { code: 'TC-012', title: 'Cadastro com e-mail existente', author: 'Matheus Pamplona', adherence: 83, status: 'Em correção', tone: 'warning' },
]

function initials(name: string) {
  return name.split(' ').filter(Boolean).slice(0, 2).map((part) => part[0]).join('').toUpperCase()
}

function ApiState({ status }: { status: ApiStatus }) {
  return <div className={`api-state ${status}`}><span />
    {status === 'checking' && 'Verificando conexão com a API…'}
    {status === 'online' && 'API e banco de dados conectados'}
    {status === 'offline' && 'Não foi possível conectar à API'}
  </div>
}

function AuthScreen({ apiStatus, onAuthenticated }: { apiStatus: ApiStatus; onAuthenticated: (user: CurrentUser) => void }) {
  const [mode, setMode] = useState<AuthMode>('login')
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      const response = await fetch(`/api/auth/${mode === 'login' ? 'login' : 'register'}`, {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(mode === 'login' ? { email, password } : { full_name: fullName, email, password }),
      })
      const payload = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(payload.detail || 'Não foi possível continuar.')
      onAuthenticated(payload as CurrentUser)
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Ocorreu um erro inesperado.')
    } finally { setSubmitting(false) }
  }

  return <main className="auth-page"><section className="auth-card">
    <div className="auth-brand"><span className="brand-mark" aria-hidden="true">✓</span><div><strong>TestCheck</strong><span>Qualidade de Software</span></div></div>
    <p className="eyebrow">ACESSO À PLATAFORMA</p>
    <h1>{mode === 'login' ? 'Entre na sua conta' : 'Crie sua conta'}</h1>
    <p className="subtitle">{mode === 'login' ? 'Acompanhe suas auditorias e não conformidades.' : 'Use seu e-mail para receber atribuições e notificações.'}</p>
    <form className="auth-form" onSubmit={submit}>
      {mode === 'register' && <label>Nome completo<input value={fullName} onChange={(event) => setFullName(event.target.value)} placeholder="Seu nome" minLength={3} required /></label>}
      <label>E-mail<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="nome@exemplo.com" required /></label>
      <label>Senha<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Mínimo de 8 caracteres" minLength={8} required /></label>
      {error && <p className="form-error" role="alert">{error}</p>}
      <button className="primary-button auth-submit" type="submit" disabled={submitting || apiStatus !== 'online'}>{submitting ? 'Aguarde…' : mode === 'login' ? 'Entrar' : 'Criar conta'}</button>
    </form>
    <p className="auth-switch">{mode === 'login' ? 'Ainda não tem conta?' : 'Já possui uma conta?'} <button type="button" onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError('') }}>{mode === 'login' ? 'Cadastre-se' : 'Entrar'}</button></p>
    <ApiState status={apiStatus} />
  </section></main>
}

function TestCasesPage({ apiStatus, user, onBack, onOpenAudits, onLogout }: { apiStatus: ApiStatus; user: CurrentUser; onBack: () => void; onOpenAudits: () => void; onLogout: () => void }) {
  const [cases, setCases] = useState<TestCaseData[]>([])
  const [form, setForm] = useState<TestCaseForm>(() => blankTestCase(user.email))
  const [editingId, setEditingId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')

  const loadCases = async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/test-cases', { credentials: 'include' })
      if (!response.ok) throw new Error()
      setCases(await response.json() as TestCaseData[])
    } catch { setMessage('Não foi possível carregar os casos de teste.') } finally { setLoading(false) }
  }

  useEffect(() => { void loadCases() }, [])
  const setField = (field: keyof TestCaseForm, value: string) => setForm((current) => ({ ...current, [field]: value }))
  const nextStepNumber = (steps: string) => {
    const numbers = [...steps.matchAll(/(?:^|\n)\s*(\d+)\.\s/g)].map((match) => Number(match[1]))
    return Math.max(0, ...numbers) + 1
  }
  const startSteps = () => {
    if (!form.steps.trim()) setField('steps', '1. ')
  }
  const addStep = () => {
    setForm((current) => {
      const steps = current.steps.trimEnd()
      return { ...current, steps: steps ? `${steps}\n${nextStepNumber(steps)}. ` : '1. ' }
    })
  }
  const handleStepKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key !== 'Enter' || event.shiftKey) return
    event.preventDefault()
    const target = event.currentTarget
    const position = target.selectionStart
    const before = target.value.slice(0, position)
    const after = target.value.slice(target.selectionEnd)
    const insertion = `\n${nextStepNumber(before)}. `
    setField('steps', `${before}${insertion}${after}`)
    window.requestAnimationFrame(() => target.setSelectionRange(position + insertion.length, position + insertion.length))
  }
  const edit = (testCase: TestCaseData) => {
    const { id, code, author_name, ...values } = testCase
    setEditingId(id)
    setForm(values)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }
  const reset = () => { setEditingId(null); setForm(blankTestCase(user.email)); setMessage('') }
  const save = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setSaving(true)
    setMessage('')
    try {
      const response = await fetch(editingId ? `/api/test-cases/${editingId}` : '/api/test-cases', {
        method: editingId ? 'PUT' : 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(form),
      })
      const payload = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(payload.detail || 'Não foi possível salvar.')
      reset()
      await loadCases()
      setMessage(editingId ? 'Caso de teste atualizado.' : 'Caso de teste criado.')
    } catch (error) { setMessage(error instanceof Error ? error.message : 'Não foi possível salvar.') } finally { setSaving(false) }
  }
  const remove = async (testCase: TestCaseData) => {
    if (!window.confirm(`Excluir ${testCase.code} — ${testCase.title}?`)) return
    const response = await fetch(`/api/test-cases/${testCase.id}`, { method: 'DELETE', credentials: 'include' })
    if (response.ok) { if (editingId === testCase.id) reset(); await loadCases(); setMessage('Caso de teste excluído.') }
    else { const payload = await response.json().catch(() => ({})); setMessage(payload.detail || 'Não foi possível excluir.') }
  }

  return <div className="app-shell"><aside className="sidebar">
    <div className="brand"><span className="brand-mark" aria-hidden="true">✓</span><div><strong>TestCheck</strong><span>Qualidade de Software</span></div></div>
    <nav aria-label="Navegação principal"><a className="nav-item" href="#dashboard" onClick={(event) => { event.preventDefault(); onBack() }}><span aria-hidden="true">◫</span> Visão geral</a><a className="nav-item active" href="#test-cases"><span aria-hidden="true">≡</span> Casos de teste</a><a className="nav-item" href="#audits" onClick={(event) => { event.preventDefault(); onOpenAudits() }}><span aria-hidden="true">✓</span> Auditorias</a><a className="nav-item" href="#nonconformities"><span aria-hidden="true">!</span> Não conformidades</a></nav>
    <div className="sidebar-footer"><div className="avatar">{initials(user.full_name)}</div><div><strong>{user.full_name}</strong><span>Responsável</span></div><button className="logout-button" onClick={onLogout} type="button">Sair</button></div>
  </aside><main>
    <header className="topbar"><div><p className="eyebrow">ARTEFATOS DE SOFTWARE</p><h1>Casos de teste</h1><p className="subtitle">Cadastre os casos que serão avaliados pela auditoria.</p></div><button className="primary-button" type="button" onClick={reset}>＋ Novo caso</button></header>
    <section className="case-workspace"><form className="panel case-form" onSubmit={save}>
      <div className="panel-header"><div><h2>{editingId ? 'Editar caso de teste' : 'Novo caso de teste'}</h2><p>Campos em branco poderão ser identificados na auditoria.</p></div></div>
      <div className="form-fields"><label>Título *<input value={form.title} onChange={(event) => setField('title', event.target.value)} placeholder="Ex.: Login com credenciais válidas" minLength={3} required /></label><label>Responsável pela correção * <span className="field-hint">Receberá a NC automaticamente, se houver.</span><input type="email" value={form.responsible_email} onChange={(event) => setField('responsible_email', event.target.value)} placeholder="responsavel@exemplo.com" required /></label><label>Objetivo<textarea value={form.description} onChange={(event) => setField('description', event.target.value)} placeholder="O que este caso valida?" /></label><label>Pré-condições<textarea value={form.preconditions} onChange={(event) => setField('preconditions', event.target.value)} placeholder="Ex.: Usuário já cadastrado" /></label><label>Passos de teste <span className="field-hint">Pressione Enter para numerar o próximo passo.</span><textarea className="steps-editor" value={form.steps} onFocus={startSteps} onKeyDown={handleStepKeyDown} onChange={(event) => setField('steps', event.target.value)} placeholder="1. Acessar a tela" /></label><button className="add-step-button" type="button" onClick={addStep}>＋ Adicionar passo</button><label>Dados de teste<textarea value={form.test_data} onChange={(event) => setField('test_data', event.target.value)} placeholder="E-mail e senha utilizados" /></label><label>Resultado esperado<textarea value={form.expected_result} onChange={(event) => setField('expected_result', event.target.value)} placeholder="O sistema deve liberar o acesso" /></label><label>Critério de aprovação<textarea value={form.approval_criteria} onChange={(event) => setField('approval_criteria', event.target.value)} placeholder="Acesso à página inicial sem mensagens de erro" /></label></div>
      <div className="form-actions"><button className="text-button" type="button" onClick={reset}>Cancelar</button><button className="primary-button" disabled={saving} type="submit">{saving ? 'Salvando…' : editingId ? 'Salvar alterações' : 'Criar caso'}</button></div>
      {message && <p className="case-message" role="status">{message}</p>}
    </form>
    <section className="panel case-list"><div className="panel-header"><div><h2>Casos cadastrados</h2><p>{loading ? 'Carregando…' : `${cases.length} caso(s) no banco compartilhado.`}</p></div></div>
      <div className="case-list-content">{!loading && cases.length === 0 && <p className="empty-state">Ainda não há casos de teste. Crie o primeiro usando o formulário.</p>}{cases.map((testCase) => <article className="case-summary" key={testCase.id}><div><span className="case-code">{testCase.code}</span><h3>{testCase.title}</h3><p>Autor: {testCase.author_name}</p><p>Responsável: {testCase.responsible_email}</p></div><div className="case-summary-actions"><button className="text-button" type="button" onClick={() => edit(testCase)}>Editar</button><button className="danger-button" type="button" onClick={() => void remove(testCase)}>Excluir</button></div></article>)}</div>
      <ApiState status={apiStatus} />
    </section></section>
  </main></div>
}

function AuditPage({ apiStatus, user, onBack, onOpenCases, onLogout }: { apiStatus: ApiStatus; user: CurrentUser; onBack: () => void; onOpenCases: () => void; onLogout: () => void }) {
  const [cases, setCases] = useState<TestCaseData[]>([])
  const [audits, setAudits] = useState<AuditData[]>([])
  const [loading, setLoading] = useState(true)
  const [runningId, setRunningId] = useState<string | null>(null)
  const [message, setMessage] = useState('')

  const loadData = async () => {
    setLoading(true)
    try {
      const [casesResponse, auditsResponse] = await Promise.all([
        fetch('/api/test-cases', { credentials: 'include' }), fetch('/api/audits', { credentials: 'include' }),
      ])
      if (!casesResponse.ok || !auditsResponse.ok) throw new Error()
      setCases(await casesResponse.json() as TestCaseData[])
      setAudits(await auditsResponse.json() as AuditData[])
    } catch { setMessage('Não foi possível carregar as auditorias.') } finally { setLoading(false) }
  }

  useEffect(() => { void loadData() }, [])
  const runAudit = async (testCase: TestCaseData) => {
    setRunningId(testCase.id)
    setMessage('')
    try {
      const response = await fetch('/api/audits', { method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ test_case_id: testCase.id }) })
      const audit = await response.json().catch(() => ({})) as Partial<AuditData> & { detail?: string }
      if (!response.ok) throw new Error(audit.detail || 'Não foi possível executar a auditoria.')
      setMessage(`Auditoria concluída: ${audit.adherence_percentage}% de aderência e ${audit.nonconformity_count} NC(s) gerada(s).`)
      await loadData()
    } catch (error) { setMessage(error instanceof Error ? error.message : 'Não foi possível executar a auditoria.') } finally { setRunningId(null) }
  }

  return <div className="app-shell"><aside className="sidebar">
    <div className="brand"><span className="brand-mark" aria-hidden="true">✓</span><div><strong>TestCheck</strong><span>Qualidade de Software</span></div></div>
    <nav aria-label="Navegação principal"><a className="nav-item" href="#dashboard" onClick={(event) => { event.preventDefault(); onBack() }}><span aria-hidden="true">◫</span> Visão geral</a><a className="nav-item" href="#test-cases" onClick={(event) => { event.preventDefault(); onOpenCases() }}><span aria-hidden="true">≡</span> Casos de teste</a><a className="nav-item active" href="#audits"><span aria-hidden="true">✓</span> Auditorias</a><a className="nav-item" href="#nonconformities"><span aria-hidden="true">!</span> Não conformidades</a></nav>
    <div className="sidebar-footer"><div className="avatar">{initials(user.full_name)}</div><div><strong>{user.full_name}</strong><span>Auditor</span></div><button className="logout-button" onClick={onLogout} type="button">Sair</button></div>
  </aside><main>
    <header className="topbar"><div><p className="eyebrow">AUDITORIA AUTOMATIZADA</p><h1>Auditorias de casos de teste</h1><p className="subtitle">Avalie os campos essenciais e gere não conformidades automaticamente.</p></div></header>
    <section className="audit-workspace"><section className="panel audit-run"><div className="panel-header"><div><h2>Executar nova auditoria</h2><p>O checklist verifica objetivo, pré-condições, passos, dados, resultado e critério de aprovação.</p></div></div><div className="audit-case-list">{!loading && cases.length === 0 && <p className="empty-state">Cadastre um caso de teste antes de iniciar a auditoria.</p>}{cases.map((testCase) => <article className="audit-case" key={testCase.id}><div><span className="case-code">{testCase.code}</span><h3>{testCase.title}</h3><p>Responsável da futura NC: {testCase.responsible_email}</p></div><button className="primary-button" type="button" disabled={runningId === testCase.id} onClick={() => void runAudit(testCase)}>{runningId === testCase.id ? 'Auditando…' : 'Auditar'}</button></article>)}</div>{message && <p className="case-message" role="status">{message}</p>}<ApiState status={apiStatus} /></section>
      <section className="panel audit-history"><div className="panel-header"><div><h2>Histórico</h2><p>{loading ? 'Carregando…' : `${audits.length} auditoria(s) realizada(s).`}</p></div></div><div className="audit-history-list">{!loading && audits.length === 0 && <p className="empty-state">Nenhuma auditoria realizada ainda.</p>}{audits.map((audit) => <article className="audit-summary" key={audit.id}><div><span className="case-code">{audit.test_case_code}</span><h3>{audit.test_case_title}</h3><p>{audit.auditor_name} · {audit.nonconformity_count} NC(s)</p><details><summary>Ver checklist</summary><ul>{audit.items.map((item) => <li key={item.checklist_code}><span className={item.result === 'CONFORMING' ? 'audit-result conforming' : 'audit-result nonconforming'}>{item.result === 'CONFORMING' ? 'Conforme' : 'NC'}</span>{item.checklist_label}</li>)}</ul></details></div><strong className="adherence-value">{audit.adherence_percentage ?? 0}%</strong></article>)}</div></section></section>
  </main></div>
}

function Dashboard({ apiStatus, user, onLogout, onOpenCases, onOpenAudits }: { apiStatus: ApiStatus; user: CurrentUser; onLogout: () => void; onOpenCases: () => void; onOpenAudits: () => void }) {
  const startAudit = () => { onOpenAudits() }
  const roleLabel = user.role === 'AUDITOR' ? 'Auditor' : user.role === 'ADMIN' ? 'Administrador' : 'Responsável'

  return <div className="app-shell"><aside className="sidebar">
    <div className="brand"><span className="brand-mark" aria-hidden="true">✓</span><div><strong>TestCheck</strong><span>Qualidade de Software</span></div></div>
    <nav aria-label="Navegação principal">
      <a className="nav-item active" href="#dashboard"><span aria-hidden="true">◫</span> Visão geral</a>
      <a className="nav-item" href="#test-cases" onClick={(event) => { event.preventDefault(); onOpenCases() }}><span aria-hidden="true">≡</span> Casos de teste</a>
      <a className="nav-item" href="#audits" onClick={(event) => { event.preventDefault(); onOpenAudits() }}><span aria-hidden="true">✓</span> Auditorias</a>
      <a className="nav-item" href="#nonconformities"><span aria-hidden="true">!</span> Não conformidades</a>
    </nav>
    <div className="sidebar-footer"><div className="avatar">{initials(user.full_name)}</div><div><strong>{user.full_name}</strong><span>{roleLabel}</span></div><button className="logout-button" onClick={onLogout} type="button">Sair</button></div>
  </aside><main id="dashboard">
    <header className="topbar"><div><p className="eyebrow">PROJETO CHECKOUT</p><h1>Visão geral da qualidade</h1><p className="subtitle">Acompanhe auditorias, aderência e correções dos casos de teste.</p></div><button className="primary-button" type="button" onClick={startAudit}><span aria-hidden="true">＋</span> Nova auditoria</button></header>
    <section className="metrics" aria-label="Indicadores">
      <article className="metric-card"><span className="metric-icon blue">≡</span><div><strong>12</strong><span>Casos de teste</span></div><small>3 adicionados nesta semana</small></article>
      <article className="metric-card"><span className="metric-icon violet">✓</span><div><strong>4</strong><span>Auditorias pendentes</span></div><small>2 com prazo próximo</small></article>
      <article className="metric-card"><span className="metric-icon red">!</span><div><strong>3</strong><span>NCs abertas</span></div><small>1 aguardando validação</small></article>
      <article className="metric-card"><span className="metric-icon green">↗</span><div><strong>86%</strong><span>Aderência média</span></div><small className="positive">+8% desde a última rodada</small></article>
    </section>
    <section className="content-grid"><article className="panel cases-panel" id="test-cases"><div className="panel-header"><div><h2>Casos auditados recentemente</h2><p>Últimos artefatos avaliados pela equipe.</p></div><button className="text-button" type="button" onClick={onOpenCases}>Ver todos →</button></div><div className="table-wrap"><table><thead><tr><th>Caso de teste</th><th>Responsável</th><th>Aderência</th><th>Estado</th></tr></thead><tbody>{testCases.map((testCase) => <tr key={testCase.code}><td><span className="case-code">{testCase.code}</span><strong>{testCase.title}</strong></td><td>{testCase.author}</td><td><div className="progress-row"><span className="progress-track"><span style={{ width: `${testCase.adherence}%` }} /></span><strong>{testCase.adherence}%</strong></div></td><td><span className={`status ${testCase.tone}`}>{testCase.status}</span></td></tr>)}</tbody></table></div></article>
      <aside className="panel next-panel"><div className="panel-header"><div><h2>Próximas ações</h2><p>Itens que precisam de atenção.</p></div></div><ul className="action-list"><li><span className="action-dot red" /><div><strong>NC-002 vence amanhã</strong><span>Dados de teste não informados</span></div><b>1d</b></li><li><span className="action-dot violet" /><div><strong>Correção para validar</strong><span>TC-012 · Cadastro duplicado</span></div><b>Hoje</b></li><li><span className="action-dot blue" /><div><strong>4 casos sem auditoria</strong><span>Projeto Portal Acadêmico</span></div><b>4</b></li></ul><ApiState status={apiStatus} /></aside>
    </section>
  </main></div>
}

function App() {
  const [apiStatus, setApiStatus] = useState<ApiStatus>('checking')
  const [user, setUser] = useState<CurrentUser | null>(null)
  const [loadingSession, setLoadingSession] = useState(true)
  const [view, setView] = useState<'dashboard' | 'test-cases' | 'audits'>('dashboard')
  useEffect(() => {
    const loadSession = async () => {
      try {
        const health = await fetch('/api/health', { credentials: 'include' })
        if (!health.ok) throw new Error('API indisponível')
        setApiStatus('online')
        const me = await fetch('/api/auth/me', { credentials: 'include' })
        if (me.ok) setUser(await me.json() as CurrentUser)
      } catch { setApiStatus('offline') } finally { setLoadingSession(false) }
    }
    void loadSession()
  }, [])
  const logout = async () => { await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' }); setUser(null); setView('dashboard') }
  if (loadingSession) return <main className="loading-page">Carregando TestCheck…</main>
  if (!user) return <AuthScreen apiStatus={apiStatus} onAuthenticated={setUser} />
  if (view === 'test-cases') return <TestCasesPage apiStatus={apiStatus} user={user} onBack={() => setView('dashboard')} onOpenAudits={() => setView('audits')} onLogout={logout} />
  if (view === 'audits') return <AuditPage apiStatus={apiStatus} user={user} onBack={() => setView('dashboard')} onOpenCases={() => setView('test-cases')} onLogout={logout} />
  return <Dashboard apiStatus={apiStatus} user={user} onLogout={logout} onOpenCases={() => setView('test-cases')} onOpenAudits={() => setView('audits')} />
}

export default App
