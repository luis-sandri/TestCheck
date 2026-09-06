import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import './App.css'

type ApiStatus = 'checking' | 'online' | 'offline'
type AuthMode = 'login' | 'register'
type CurrentUser = { id: string; full_name: string; email: string; role: 'AUDITOR' | 'RESPONSIBLE' | 'ADMIN' }

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

function Dashboard({ apiStatus, user, onLogout }: { apiStatus: ApiStatus; user: CurrentUser; onLogout: () => void }) {
  const [notice, setNotice] = useState('')
  const startAudit = () => { setNotice('A criação da auditoria será implementada na próxima etapa.'); window.setTimeout(() => setNotice(''), 3600) }
  const roleLabel = user.role === 'AUDITOR' ? 'Auditor' : user.role === 'ADMIN' ? 'Administrador' : 'Responsável'

  return <div className="app-shell"><aside className="sidebar">
    <div className="brand"><span className="brand-mark" aria-hidden="true">✓</span><div><strong>TestCheck</strong><span>Qualidade de Software</span></div></div>
    <nav aria-label="Navegação principal">
      <a className="nav-item active" href="#dashboard"><span aria-hidden="true">◫</span> Visão geral</a>
      <a className="nav-item" href="#test-cases"><span aria-hidden="true">≡</span> Casos de teste</a>
      <a className="nav-item" href="#audits"><span aria-hidden="true">✓</span> Auditorias</a>
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
    <section className="content-grid"><article className="panel cases-panel" id="test-cases"><div className="panel-header"><div><h2>Casos auditados recentemente</h2><p>Últimos artefatos avaliados pela equipe.</p></div><button className="text-button" type="button">Ver todos →</button></div><div className="table-wrap"><table><thead><tr><th>Caso de teste</th><th>Responsável</th><th>Aderência</th><th>Estado</th></tr></thead><tbody>{testCases.map((testCase) => <tr key={testCase.code}><td><span className="case-code">{testCase.code}</span><strong>{testCase.title}</strong></td><td>{testCase.author}</td><td><div className="progress-row"><span className="progress-track"><span style={{ width: `${testCase.adherence}%` }} /></span><strong>{testCase.adherence}%</strong></div></td><td><span className={`status ${testCase.tone}`}>{testCase.status}</span></td></tr>)}</tbody></table></div></article>
      <aside className="panel next-panel"><div className="panel-header"><div><h2>Próximas ações</h2><p>Itens que precisam de atenção.</p></div></div><ul className="action-list"><li><span className="action-dot red" /><div><strong>NC-002 vence amanhã</strong><span>Dados de teste não informados</span></div><b>1d</b></li><li><span className="action-dot violet" /><div><strong>Correção para validar</strong><span>TC-012 · Cadastro duplicado</span></div><b>Hoje</b></li><li><span className="action-dot blue" /><div><strong>4 casos sem auditoria</strong><span>Projeto Portal Acadêmico</span></div><b>4</b></li></ul><ApiState status={apiStatus} /></aside>
    </section>{notice && <div className="toast" role="status">{notice}</div>}
  </main></div>
}

function App() {
  const [apiStatus, setApiStatus] = useState<ApiStatus>('checking')
  const [user, setUser] = useState<CurrentUser | null>(null)
  const [loadingSession, setLoadingSession] = useState(true)
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
  const logout = async () => { await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' }); setUser(null) }
  if (loadingSession) return <main className="loading-page">Carregando TestCheck…</main>
  if (!user) return <AuthScreen apiStatus={apiStatus} onAuthenticated={setUser} />
  return <Dashboard apiStatus={apiStatus} user={user} onLogout={logout} />
}

export default App
