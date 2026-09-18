import { useEffect, useId, useRef, useState } from 'react'
import type { FormEvent, MouseEvent } from 'react'
import './App.css'

type ApiStatus = 'checking' | 'online' | 'offline'
type AuthMode = 'login' | 'register'
type PageName = 'dashboard' | 'test-cases' | 'audits' | 'nonconformities'
type AuditStatusFilter = 'ALL' | 'PENDING' | 'WAITING_REVIEW' | 'COMPLETED' | 'MISSING_ROLES'
type NonconformityFilter = 'ALL' | 'OPEN' | 'IN_CORRECTION' | 'WAITING_VALIDATION' | 'ESCALATED' | 'RESOLVED'
type OrganizationData = { id: string; name: string; role: 'OWNER' | 'MEMBER' }
type PublicOrganizationData = { id: string; name: string }
type CurrentUser = { id: string; full_name: string; email: string; role: 'AUDITOR' | 'RESPONSIBLE' | 'ADMIN'; active_organization: OrganizationData | null; organizations: OrganizationData[] }
type TestCaseData = {
  id: string; code: string; zephyr_key: string | null; title: string; description: string; preconditions: string; steps: string
  test_data: string; expected_result: string; author_name: string; responsible_email: string; reviewer_email: string; supervisor_email: string; scenario_id: string | null; scenario_name: string | null
}
type TestCaseForm = Omit<TestCaseData, 'id' | 'code' | 'zephyr_key' | 'author_name' | 'scenario_name'> & { case_number: string }
type ScenarioData = { id: string; name: string; zephyr_folder: string; reviewer_email: string; supervisor_email: string; test_case_count: number; created_at: string }
type ZephyrImportResult = { imported_cases?: number; scenarios?: ScenarioData[]; detail?: string }
type SiteSelectOption = { value: string; label: string; description?: string }
type AuditItemData = { checklist_code: string; checklist_label: string; field_value: string | null; result: 'CONFORMING' | 'NONCONFORMING' | 'NOT_APPLICABLE' | null; suggested_result: 'CONFORMING' | 'NONCONFORMING' | 'NOT_APPLICABLE' | null; final_result: 'CONFORMING' | 'NONCONFORMING' | 'NOT_APPLICABLE' | null; note: string | null }
type AuditData = {
  id: string; test_case_id: string; test_case_code: string; test_case_title: string; scenario_id: string | null; scenario_name: string | null; auditor_name: string
  status: 'DRAFT' | 'COMPLETED'; adherence_percentage: number | null; original_adherence_percentage: number | null; nonconformity_count: number
  items: AuditItemData[]; created_at: string; completed_at: string | null; can_review: boolean
}
type EvidenceData = { id: string; description: string | null; resource_url: string | null; evidence_type: 'CORRECTION' | 'CONTESTATION'; status: 'SUBMITTED' | 'APPROVED' | 'REJECTED'; submitted_by_name: string; submitted_at: string; reviewer_comment: string | null }
type NonconformityHistoryData = { id: string; actor_email: string | null; event_type: string; previous_status: string | null; new_status: string | null; message: string; created_at: string }
type NonconformityData = {
  id: string; code: string; test_case_code: string; test_case_title: string; scenario_id: string | null; scenario_name: string | null; description: string; severity: 'LOW' | 'MEDIUM' | 'HIGH'; status: 'OPEN' | 'IN_CORRECTION' | 'WAITING_VALIDATION' | 'CONTESTED' | 'ESCALATED' | 'RESOLVED'; due_date: string | null; assignee_email: string | null; supervisor_email: string | null; resolution_due_at: string | null; review_due_at: string | null; escalation_due_at: string | null; supervisor_decision_due_at: string | null; escalated_at: string | null; final_decision: string | null; can_submit_evidence: boolean; can_review: boolean; can_decide_final: boolean; evidences: EvidenceData[]; history: NonconformityHistoryData[]
}

const blankTestCase = (responsibleEmail = ''): TestCaseForm => ({
  title: '', scenario_id: '', case_number: '', responsible_email: responsibleEmail, reviewer_email: responsibleEmail, supervisor_email: '', description: '', preconditions: '', steps: '', test_data: '', expected_result: '',
})
const apiReadOptions = { credentials: 'include' as const, cache: 'no-store' as const }

function initials(name: string) {
  return name.split(' ').filter(Boolean).slice(0, 2).map((part) => part[0]).join('').toUpperCase()
}

function ApiState({ status }: { status: ApiStatus }) {
  if (status === 'online') return null
  return <div className={`api-state ${status}`}><span />
    {status === 'checking' && 'Verificando conexão com a API…'}
    {status === 'offline' && 'Não foi possível conectar à API'}
  </div>
}

function SiteSelect({ value, options, onChange, ariaLabel, className = '' }: { value: string; options: SiteSelectOption[]; onChange: (value: string) => void; ariaLabel: string; className?: string }) {
  const [isOpen, setIsOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)
  const listboxId = useId()
  const selected = options.find((option) => option.value === value) || options[0]

  useEffect(() => {
    if (!isOpen) return
    const closeOnOutsideClick = (event: PointerEvent) => {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) setIsOpen(false)
    }
    document.addEventListener('pointerdown', closeOnOutsideClick)
    return () => document.removeEventListener('pointerdown', closeOnOutsideClick)
  }, [isOpen])

  return <div className={`site-select ${isOpen ? 'is-open' : ''} ${className}`} ref={rootRef}>
    <button className="select-trigger" type="button" aria-label={ariaLabel} aria-haspopup="listbox" aria-expanded={isOpen} aria-controls={listboxId} onClick={() => setIsOpen((current) => !current)} onKeyDown={(event) => { if (event.key === 'Escape') setIsOpen(false); if (event.key === 'ArrowDown' || event.key === 'ArrowUp') { event.preventDefault(); setIsOpen(true) } }}>
      <span className="select-trigger-value" title={selected?.label}>{selected?.label}</span>
      <svg viewBox="0 0 20 20" aria-hidden="true"><path d="m5 7.5 5 5 5-5" /></svg>
    </button>
    {isOpen && <div className="select-menu" id={listboxId} role="listbox" aria-label={ariaLabel}>
      {options.map((option) => <button className={`select-option ${option.value === value ? 'is-selected' : ''}`} type="button" role="option" aria-selected={option.value === value} key={option.value} onClick={() => { onChange(option.value); setIsOpen(false) }}>
        <span><strong>{option.label}</strong>{option.description && <small>{option.description}</small>}</span>{option.value === value && <b aria-label="Selecionado">✓</b>}
      </button>)}
    </div>}
  </div>
}

function ScenarioFilter({ scenarios, value, onChange }: { scenarios: ScenarioData[]; value: string; onChange: (value: string) => void }) {
  return <label className="scenario-filter">
    <span>Filtrar cenário</span>
    <SiteSelect value={value} onChange={onChange} ariaLabel="Filtrar por cenário" options={[{ value: '', label: 'Todos os cenários', description: 'Exibe casos de todos os cenários.' }, ...scenarios.map((scenario) => ({ value: scenario.id, label: scenario.name, description: `${scenario.test_case_count} caso(s) de teste` }))]} />
  </label>
}

function NavIcon({ name }: { name: PageName }) {
  if (name === 'dashboard') return <svg className="nav-icon" viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /></svg>
  if (name === 'test-cases') return <svg className="nav-icon" viewBox="0 0 24 24" aria-hidden="true"><rect x="5" y="3" width="14" height="18" rx="2" /><path d="M9 8h6M9 12h6M9 16h3M7.5 8h.01M7.5 12h.01M7.5 16h.01" /></svg>
  if (name === 'audits') return <svg className="nav-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3 19 6v5c0 4.6-3 7.9-7 10-4-2.1-7-5.4-7-10V6l7-3Z" /><path d="m9 12 2 2 4-4" /></svg>
  return <svg className="nav-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3 2.8 20h18.4L12 3Z" /><path d="M12 9v4M12 17h.01" /></svg>
}

function ConfirmationModal({ isOpen, title, description, confirmLabel, tone = 'primary', busy = false, onCancel, onConfirm }: {
  isOpen: boolean; title: string; description: string; confirmLabel: string; tone?: 'primary' | 'danger'; busy?: boolean; onCancel: () => void; onConfirm: () => void
}) {
  if (!isOpen) return null
  return <div className="modal-backdrop" role="presentation">
    <section className="confirmation-modal" role="dialog" aria-modal="true" aria-labelledby="confirmation-title" aria-describedby="confirmation-description">
      <div className={`modal-icon ${tone}`} aria-hidden="true">{tone === 'danger' ? '!' : '✓'}</div>
      <h2 id="confirmation-title">{title}</h2>
      <p id="confirmation-description">{description}</p>
      <div className="modal-actions">
        <button className="secondary-button" type="button" disabled={busy} onClick={onCancel}>Cancelar</button>
        <button className={tone === 'danger' ? 'danger-solid-button' : 'primary-button'} type="button" disabled={busy} onClick={onConfirm}>{busy ? 'Aguarde…' : confirmLabel}</button>
      </div>
    </section>
  </div>
}

type ToastTone = 'success' | 'info' | 'warning' | 'error'

function getToastFeedback(message: string): { tone: ToastTone; label: string; icon: string } {
  const normalized = message.toLocaleLowerCase('pt-BR')
  const isError = /não foi possível|recusou|falh|erro|inválid|obrigat|diferente|somente|precisa|não pode|não possui|não encontrado|nenhum caso|descreva|selecione|defina|registre|informe/.test(normalized)
  if (isError) return { tone: 'error', label: 'Não foi possível concluir', icon: '!' }

  const isWarning = /devolvid[ao]|ação necessária|prazo|confirmada\(s\)/.test(normalized) && !/0 nc\(s\) confirmada\(s\)/.test(normalized)
  if (isWarning) return { tone: 'warning', label: 'Ação necessária', icon: '!' }

  const isInfo = /sugestões automáticas|enviad[ao].*(validação|análise)|aguardando|identificadores de owner|revisão finalizada/.test(normalized)
  if (isInfo) return { tone: 'info', label: 'Próxima etapa', icon: 'i' }

  return { tone: 'success', label: 'Concluído', icon: '✓' }
}

function Toast({ message, onDismiss }: { message: string; onDismiss: () => void }) {
  const [isLeaving, setIsLeaving] = useState(false)
  useEffect(() => {
    if (!message) return
    setIsLeaving(false)
    const timeout = window.setTimeout(() => setIsLeaving(true), 5000)
    return () => window.clearTimeout(timeout)
  }, [message])

  if (!message) return null
  const { tone, label, icon } = getToastFeedback(message)
  const needsImmediateAttention = tone === 'error' || tone === 'warning'
  return <div className={`toast-notification ${tone} ${isLeaving ? 'is-leaving' : ''}`} role={needsImmediateAttention ? 'alert' : 'status'} aria-live={needsImmediateAttention ? 'assertive' : 'polite'} aria-atomic="true" onAnimationEnd={() => { if (isLeaving) onDismiss() }}>
    <span className="toast-icon" aria-hidden="true">{icon}</span>
    <div><strong>{label}</strong><p>{message}</p></div>
    <button type="button" aria-label="Fechar aviso" onClick={onDismiss}>×</button>
  </div>
}

function Sidebar({ active, user, onDashboard, onCases, onAudits, onNonconformities, onLogout, onOrganizationChange }: {
  active: PageName; user: CurrentUser; onDashboard: () => void; onCases: () => void; onAudits: () => void; onNonconformities: () => void; onLogout: () => void; onOrganizationChange: (organizationId: string) => void
}) {
  const [isOpen, setIsOpen] = useState(() => {
    const savedState = window.sessionStorage.getItem('testcheck-sidebar-open')
    return savedState === null ? window.matchMedia('(min-width: 761px)').matches : savedState === 'true'
  })
  const [accountMenuOpen, setAccountMenuOpen] = useState(false)
  useEffect(() => { window.sessionStorage.setItem('testcheck-sidebar-open', String(isOpen)) }, [isOpen])
  const navigate = (callback: () => void) => (event: MouseEvent<HTMLAnchorElement>) => {
    event.preventDefault()
    if (!window.matchMedia('(min-width: 761px)').matches) setIsOpen(false)
    callback()
  }

  return <>
    <button className={`mobile-menu-toggle ${isOpen ? 'is-hidden' : ''}`} type="button" aria-expanded={isOpen} aria-controls="main-navigation" onClick={() => setIsOpen(true)}>
      <span aria-hidden="true">☰</span><span className="sr-only">Abrir menu</span>
    </button>
    {isOpen && <button className="sidebar-backdrop" type="button" aria-label="Fechar menu" onClick={() => setIsOpen(false)} />}
    <aside className={`sidebar ${isOpen ? 'is-open' : 'is-collapsed'}`} id="main-navigation">
      <div className="brand"><span className="brand-mark" aria-hidden="true">✓</span><div><strong>TestCheck</strong><span>Qualidade de Software</span></div><button className="sidebar-toggle" type="button" aria-expanded={isOpen} aria-label={isOpen ? 'Recolher menu' : 'Expandir menu'} onClick={() => setIsOpen((current) => !current)}>{isOpen ? '×' : '☰'}</button></div>
      <nav aria-label="Navegação principal">
        <a className={`nav-item ${active === 'dashboard' ? 'active' : ''}`} href="#dashboard" onClick={navigate(onDashboard)}><NavIcon name="dashboard" /> Visão geral</a>
        <a className={`nav-item ${active === 'test-cases' ? 'active' : ''}`} href="#test-cases" onClick={navigate(onCases)}><NavIcon name="test-cases" /> Cenários e casos</a>
        <a className={`nav-item ${active === 'audits' ? 'active' : ''}`} href="#audits" onClick={navigate(onAudits)}><NavIcon name="audits" /> Auditorias</a>
        <a className={`nav-item ${active === 'nonconformities' ? 'active' : ''}`} href="#nonconformities" onClick={navigate(onNonconformities)}><NavIcon name="nonconformities" /> Não conformidades</a>
      </nav>
      <div className="sidebar-footer">
        <button className="account-menu-trigger" type="button" aria-expanded={accountMenuOpen} aria-label="Abrir opções da conta e organização" onClick={() => setAccountMenuOpen((current) => !current)}><span className="avatar">{initials(user.full_name)}</span><span className="account-user-details"><strong>{user.full_name}</strong><span>{user.active_organization?.name || 'Sem organização'}</span></span><span className="account-menu-chevron" aria-hidden="true">⌄</span></button>
        {accountMenuOpen && <div className="account-menu"><strong>{user.full_name}</strong><span className="account-menu-label">Organização ativa</span>{user.active_organization && <SiteSelect value={user.active_organization.id} ariaLabel="Trocar organização" onChange={onOrganizationChange} options={user.organizations.map((organization) => ({ value: organization.id, label: organization.name, description: organization.role === 'OWNER' ? 'Você é proprietário' : 'Você participa' }))} />}<button type="button" onClick={onLogout}>Sair da conta <span aria-hidden="true">↗</span></button></div>}
      </div>
    </aside>
    <MobileNavigation active={active} user={user} onDashboard={onDashboard} onCases={onCases} onAudits={onAudits} onNonconformities={onNonconformities} onLogout={onLogout} onOrganizationChange={onOrganizationChange} />
  </>
}

function MobileNavigation({ active, user, onDashboard, onCases, onAudits, onNonconformities, onLogout, onOrganizationChange }: {
  active: PageName; user: CurrentUser; onDashboard: () => void; onCases: () => void; onAudits: () => void; onNonconformities: () => void; onLogout: () => void; onOrganizationChange: (organizationId: string) => void
}) {
  const [profileOpen, setProfileOpen] = useState(false)
  const navigate = (callback: () => void) => (event: MouseEvent<HTMLAnchorElement>) => {
    event.preventDefault()
    setProfileOpen(false)
    callback()
  }
  const changeOrganization = (organizationId: string) => {
    setProfileOpen(false)
    onOrganizationChange(organizationId)
  }
  const logout = () => {
    setProfileOpen(false)
    onLogout()
  }

  return <>
    {profileOpen && <button className="mobile-account-backdrop" type="button" aria-label="Fechar opções do perfil" onClick={() => setProfileOpen(false)} />}
    {profileOpen && <section className="mobile-account-sheet" id="mobile-account-sheet" role="dialog" aria-modal="true" aria-labelledby="mobile-account-title">
      <div className="mobile-sheet-handle" aria-hidden="true" />
      <div className="mobile-account-heading"><div><p>CONTA E ORGANIZAÇÃO</p><h2 id="mobile-account-title">Seu perfil</h2></div><button className="modal-close" type="button" aria-label="Fechar opções do perfil" onClick={() => setProfileOpen(false)}>×</button></div>
      <div className="mobile-account-user"><span className="avatar">{initials(user.full_name)}</span><div><strong>{user.full_name}</strong><span>{user.email}</span></div></div>
      {user.active_organization && <label className="mobile-organization-select"><span>Organização ativa</span><SiteSelect value={user.active_organization.id} ariaLabel="Trocar organização" onChange={changeOrganization} options={user.organizations.map((organization) => ({ value: organization.id, label: organization.name, description: organization.role === 'OWNER' ? 'Você é proprietário' : 'Você participa' }))} /></label>}
      <button className="mobile-logout-button" type="button" onClick={logout}>Sair da conta <span aria-hidden="true">↗</span></button>
    </section>}
    <nav className="mobile-bottom-nav" aria-label="Navegação principal no celular">
      <a className={`mobile-nav-item ${active === 'dashboard' ? 'active' : ''}`} href="#dashboard" onClick={navigate(onDashboard)}><NavIcon name="dashboard" /><span>Início</span></a>
      <a className={`mobile-nav-item ${active === 'test-cases' ? 'active' : ''}`} href="#test-cases" onClick={navigate(onCases)}><NavIcon name="test-cases" /><span>Casos</span></a>
      <a className={`mobile-nav-item ${active === 'audits' ? 'active' : ''}`} href="#audits" onClick={navigate(onAudits)}><NavIcon name="audits" /><span>Auditorias</span></a>
      <a className={`mobile-nav-item ${active === 'nonconformities' ? 'active' : ''}`} href="#nonconformities" onClick={navigate(onNonconformities)}><NavIcon name="nonconformities" /><span>NCs</span></a>
      <button className={`mobile-nav-item mobile-profile-item ${profileOpen ? 'active' : ''}`} type="button" aria-expanded={profileOpen} aria-controls="mobile-account-sheet" onClick={() => setProfileOpen((current) => !current)}><span className="mobile-profile-avatar">{initials(user.full_name)}</span><span>Perfil</span></button>
    </nav>
  </>
}

function OrganizationChoiceFields({ organizations, mode, organizationName, organizationId, onModeChange, onNameChange, onOrganizationChange }: {
  organizations: PublicOrganizationData[]; mode: 'create' | 'join'; organizationName: string; organizationId: string; onModeChange: (mode: 'create' | 'join') => void; onNameChange: (name: string) => void; onOrganizationChange: (organizationId: string) => void
}) {
  return <fieldset className="organization-choice"><legend>Organização</legend><p>Os dados ficam separados por organização.</p><div className="organization-choice-actions"><button type="button" className={mode === 'create' ? 'choice-button is-selected' : 'choice-button'} onClick={() => onModeChange('create')}>Criar organização</button><button type="button" className={mode === 'join' ? 'choice-button is-selected' : 'choice-button'} onClick={() => onModeChange('join')} disabled={organizations.length === 0}>Entrar em existente</button></div>{mode === 'create' ? <label>Nome da organização<input value={organizationName} onChange={(event) => onNameChange(event.target.value)} placeholder="Ex.: Equipe Portal Acadêmico" minLength={3} required /></label> : <label>Organização existente<SiteSelect value={organizationId} onChange={onOrganizationChange} ariaLabel="Selecionar organização" options={[{ value: '', label: 'Selecione uma organização', description: 'Escolha a organização da qual deseja participar.' }, ...organizations.map((organization) => ({ value: organization.id, label: organization.name }))]} /></label>}</fieldset>
}

function AuthScreen({ apiStatus, onAuthenticated }: { apiStatus: ApiStatus; onAuthenticated: (user: CurrentUser) => void }) {
  const [mode, setMode] = useState<AuthMode>('login')
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [organizations, setOrganizations] = useState<PublicOrganizationData[]>([])
  const [organizationMode, setOrganizationMode] = useState<'create' | 'join'>('create')
  const [organizationName, setOrganizationName] = useState('')
  const [organizationId, setOrganizationId] = useState('')

  useEffect(() => { void fetch('/api/organizations/public', apiReadOptions).then(async (response) => { if (response.ok) setOrganizations(await response.json() as PublicOrganizationData[]) }).catch(() => undefined) }, [])

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError('')
    if (mode === 'register' && organizationMode === 'join' && !organizationId) { setError('Selecione a organização à qual deseja entrar.'); return }
    setSubmitting(true)
    try {
      const response = await fetch(`/api/auth/${mode === 'login' ? 'login' : 'register'}`, {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(mode === 'login' ? { email, password } : { full_name: fullName, email, password, ...(organizationMode === 'create' ? { organization_name: organizationName } : { organization_id: organizationId }) }),
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
      {mode === 'register' && <OrganizationChoiceFields organizations={organizations} mode={organizationMode} organizationName={organizationName} organizationId={organizationId} onModeChange={setOrganizationMode} onNameChange={setOrganizationName} onOrganizationChange={setOrganizationId} />}
      {error && <p className="form-error" role="alert">{error}</p>}
      <button className="primary-button auth-submit" type="submit" disabled={submitting || apiStatus !== 'online'}>{submitting ? 'Aguarde…' : mode === 'login' ? 'Entrar' : 'Criar conta'}</button>
    </form>
    <p className="auth-switch">{mode === 'login' ? 'Ainda não tem conta?' : 'Já possui uma conta?'} <button type="button" onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError('') }}>{mode === 'login' ? 'Cadastre-se' : 'Entrar'}</button></p>
    <ApiState status={apiStatus} />
  </section></main>
}

function OrganizationSetupScreen({ user, onReady, onLogout }: { user: CurrentUser; onReady: (user: CurrentUser) => void; onLogout: () => void }) {
  const [organizations, setOrganizations] = useState<PublicOrganizationData[]>([])
  const [mode, setMode] = useState<'create' | 'join'>('create')
  const [organizationName, setOrganizationName] = useState('')
  const [organizationId, setOrganizationId] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  useEffect(() => { void fetch('/api/organizations/public', apiReadOptions).then(async (response) => { if (response.ok) setOrganizations(await response.json() as PublicOrganizationData[]) }).catch(() => setError('Não foi possível carregar as organizações.')) }, [])
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setError('')
    if (mode === 'join' && !organizationId) { setError('Selecione a organização à qual deseja entrar.'); return }
    setSubmitting(true)
    try {
      const response = await fetch(mode === 'create' ? '/api/organizations' : '/api/organizations/join', { method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(mode === 'create' ? { name: organizationName } : { organization_id: organizationId }) })
      const payload = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(payload.detail || 'Não foi possível definir a organização.')
      onReady(payload as CurrentUser)
    } catch (requestError) { setError(requestError instanceof Error ? requestError.message : 'Não foi possível definir a organização.') } finally { setSubmitting(false) }
  }
  return <main className="auth-page"><section className="auth-card organization-setup-card"><div className="auth-brand"><span className="brand-mark" aria-hidden="true">✓</span><div><strong>TestCheck</strong><span>Qualidade de Software</span></div></div><p className="eyebrow">PRIMEIRO ACESSO</p><h1>Escolha sua organização</h1><p className="subtitle">Olá, {user.full_name}. Crie uma organização para sua equipe ou entre em uma já existente.</p><form className="auth-form" onSubmit={submit}><OrganizationChoiceFields organizations={organizations} mode={mode} organizationName={organizationName} organizationId={organizationId} onModeChange={setMode} onNameChange={setOrganizationName} onOrganizationChange={setOrganizationId} />{error && <p className="form-error" role="alert">{error}</p>}<button className="primary-button auth-submit" type="submit" disabled={submitting}>{submitting ? 'Aguarde…' : mode === 'create' ? 'Criar e continuar' : 'Entrar na organização'}</button></form><p className="auth-switch"><button type="button" onClick={onLogout}>Sair da conta</button></p></section></main>
}

function TestCasesPage({ apiStatus, user, selectedScenarioId, onScenarioChange, onScenariosChanged, onBack, onOpenAudits, onOpenNonconformities, onLogout, onOrganizationChange }: { apiStatus: ApiStatus; user: CurrentUser; selectedScenarioId: string; onScenarioChange: (value: string) => void; onScenariosChanged: () => Promise<void>; onBack: () => void; onOpenAudits: () => void; onOpenNonconformities: () => void; onLogout: () => void; onOrganizationChange: (organizationId: string) => void }) {
  const [cases, setCases] = useState<TestCaseData[]>([])
  const [scenarios, setScenarios] = useState<ScenarioData[]>([])
  const [form, setForm] = useState<TestCaseForm>(() => blankTestCase(user.email))
  const [editingId, setEditingId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')
  const [caseToDelete, setCaseToDelete] = useState<TestCaseData | null>(null)
  const [zephyrFiles, setZephyrFiles] = useState<File[]>([])
  const [responsibleEmail, setResponsibleEmail] = useState(user.email)
  const [reviewerEmail, setReviewerEmail] = useState(user.email)
  const [supervisorEmail, setSupervisorEmail] = useState('')
  const [importing, setImporting] = useState(false)
  const [showCaseEditor, setShowCaseEditor] = useState(false)
  const [showImportPanel, setShowImportPanel] = useState(false)
  const importPanelRef = useRef<HTMLFormElement>(null)

  const loadCases = async () => {
    setLoading(true)
    try {
      const [casesResponse, scenariosResponse] = await Promise.all([
        fetch('/api/test-cases', apiReadOptions),
        fetch('/api/scenarios', apiReadOptions),
      ])
      if (!casesResponse.ok || !scenariosResponse.ok) throw new Error()
      setCases(await casesResponse.json() as TestCaseData[])
      setScenarios(await scenariosResponse.json() as ScenarioData[])
    } catch { setMessage('Não foi possível carregar os casos de teste.') } finally { setLoading(false) }
  }

  useEffect(() => { void loadCases() }, [])
  const importZephyr = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (zephyrFiles.length === 0) { setMessage('Selecione ao menos um arquivo .xlsx, .xml ou .csv exportado pelo Zephyr.'); return }
    setImporting(true)
    setMessage('')
    try {
      const payload = new FormData()
      zephyrFiles.forEach((file) => payload.append('files', file))
      payload.append('responsible_email', responsibleEmail)
      payload.append('reviewer_email', reviewerEmail)
      payload.append('supervisor_email', supervisorEmail)
      const response = await fetch('/api/scenarios/import-zephyr', { method: 'POST', credentials: 'include', body: payload })
      const result = await response.json().catch(() => ({})) as ZephyrImportResult
      if (!response.ok) {
        throw new Error(typeof result.detail === 'string' ? result.detail : 'Não foi possível importar o arquivo.')
      }
      setZephyrFiles([])
      await loadCases()
      await onScenariosChanged()
      setShowImportPanel(false)
      setMessage(`${result.imported_cases ?? 0} caso(s) importado(s) em ${result.scenarios?.length ?? 0} cenário(s).`)
    } catch (error) { setMessage(error instanceof Error ? error.message : 'Não foi possível importar o arquivo.') } finally { setImporting(false) }
  }
  const setField = (field: keyof TestCaseForm, value: string) => setForm((current) => ({ ...current, [field]: value }))
  const edit = (testCase: TestCaseData) => {
    const { id, code, zephyr_key: _zephyrKey, author_name: _authorName, scenario_name: _scenarioName, ...values } = testCase
    setEditingId(id)
    setForm({ ...values, scenario_id: values.scenario_id || '', case_number: code.match(/^TC-(\d+)$/)?.[1] || '' })
    setShowCaseEditor(true)
  }
  const reset = () => { setEditingId(null); setForm(blankTestCase(user.email)); setMessage('') }
  const openNewCase = () => {
    reset()
    setShowCaseEditor(true)
  }
  const toggleImportPanel = () => {
    if (showImportPanel) { setShowImportPanel(false); return }
    setShowImportPanel(true)
    window.requestAnimationFrame(() => importPanelRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
  }
  const closeCaseEditor = () => { reset(); setShowCaseEditor(false) }
  const save = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const wasEditing = Boolean(editingId)
    setSaving(true)
    setMessage('')
    try {
      const response = await fetch(editingId ? `/api/test-cases/${editingId}` : '/api/test-cases', {
        method: editingId ? 'PUT' : 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...form, case_number: form.case_number ? Number(form.case_number) : null, scenario_id: form.scenario_id || null }),
      })
      const payload = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(payload.detail || 'Não foi possível salvar.')
      closeCaseEditor()
      await loadCases()
      setMessage(wasEditing ? 'Caso de teste atualizado.' : 'Caso de teste criado.')
    } catch (error) { setMessage(error instanceof Error ? error.message : 'Não foi possível salvar.') } finally { setSaving(false) }
  }
  const remove = async (testCase: TestCaseData) => {
    const response = await fetch(`/api/test-cases/${testCase.id}`, { method: 'DELETE', credentials: 'include' })
    if (response.ok) { if (editingId === testCase.id) closeCaseEditor(); await loadCases(); setMessage('Caso de teste excluído.'); setCaseToDelete(null) }
    else { const payload = await response.json().catch(() => ({})); setMessage(payload.detail || 'Não foi possível excluir.') }
  }
  const visibleScenarios = selectedScenarioId ? scenarios.filter((scenario) => scenario.id === selectedScenarioId) : scenarios
  const visibleCases = selectedScenarioId ? cases.filter((testCase) => testCase.scenario_id === selectedScenarioId) : cases

  return <div className="app-shell"><Sidebar active="test-cases" user={user} onDashboard={onBack} onCases={() => undefined} onAudits={onOpenAudits} onNonconformities={onOpenNonconformities} onLogout={onLogout} onOrganizationChange={onOrganizationChange} /><main>
    <header className="topbar"><div><p className="eyebrow">CASOS E CENÁRIOS</p><h1>Cenários e casos de teste</h1><p className="subtitle">Crie casos gerais ou organize os casos importados em cenários do Zephyr.</p></div><div className="topbar-actions case-topbar-actions"><ScenarioFilter scenarios={scenarios} value={selectedScenarioId} onChange={onScenarioChange} /><button className="secondary-button" type="button" aria-expanded={showImportPanel} aria-controls="zephyr-import-panel" onClick={toggleImportPanel}>Importar do Zephyr <span aria-hidden="true">{showImportPanel ? '⌃' : '⌄'}</span></button><button className="primary-button" type="button" onClick={openNewCase}>＋ Criar caso</button></div></header>
    <section className="case-workspace list-only">
    {showCaseEditor && <div className="modal-backdrop" role="presentation"><form className="case-editor-modal case-form" onSubmit={save} role="dialog" aria-modal="true" aria-labelledby="case-editor-title">
      <div className="panel-header"><div><h2 id="case-editor-title">{editingId ? 'Editar caso de teste' : 'Novo caso de teste'}</h2><p>Campos em branco geram apenas uma sugestão; o revisor decide o resultado final.</p></div><button className="modal-close" type="button" aria-label="Fechar formulário" onClick={closeCaseEditor}>×</button></div>
      <div className="form-fields">
        <label>Cenário <span className="field-hint">Opcional. Sem cenário, o caso é geral.</span><SiteSelect value={form.scenario_id || ''} onChange={(value) => setField('scenario_id', value)} ariaLabel="Cenário do caso de teste" options={[{ value: '', label: 'Geral (sem cenário)', description: 'Este caso não será associado a um cenário.' }, ...scenarios.map((scenario) => ({ value: scenario.id, label: scenario.name, description: `${scenario.test_case_count} caso(s) no cenário` }))]} /></label>
        <label>Título *<input value={form.title} onChange={(event) => setField('title', event.target.value)} placeholder="Ex.: Login com credenciais válidas" minLength={3} required /></label>
        <label>Número do caso <span className="field-hint">Opcional. Deixe vazio para gerar automaticamente, como TC-01.</span><input type="number" min="1" max="9999" inputMode="numeric" value={form.case_number} onChange={(event) => setField('case_number', event.target.value)} placeholder="Automático" /></label>
        <label>Responsável pelo caso * <span className="field-hint">Receberá a NC automaticamente, se houver.</span><input type="email" value={form.responsible_email} onChange={(event) => setField('responsible_email', event.target.value)} placeholder="responsavel@exemplo.com" required /></label>
        {form.scenario_id ? <p className="workflow-summary"><strong>Papéis definidos pelo cenário</strong><span>Revisor: {scenarios.find((scenario) => scenario.id === form.scenario_id)?.reviewer_email || form.reviewer_email}</span><span>Supervisor: {scenarios.find((scenario) => scenario.id === form.scenario_id)?.supervisor_email || form.supervisor_email}</span></p> : <><label>Revisor * <span className="field-hint">Define o resultado final da auditoria e valida correções.</span><input type="email" value={form.reviewer_email} onChange={(event) => setField('reviewer_email', event.target.value)} placeholder="revisor@exemplo.com" required /></label><label>Supervisor * <span className="field-hint">Decide quando uma NC for contestada ou escalada.</span><input type="email" value={form.supervisor_email} onChange={(event) => setField('supervisor_email', event.target.value)} placeholder="supervisor@exemplo.com" required /></label></>}
        <label>Objetivo<textarea value={form.description} onChange={(event) => setField('description', event.target.value)} placeholder="O que este caso valida?" /></label>
        <label>Pré-condições<textarea value={form.preconditions} onChange={(event) => setField('preconditions', event.target.value)} placeholder="Ex.: Usuário já cadastrado" /></label>
        <label>Dado que <span className="field-hint">Descreva o contexto inicial do cenário, sem numeração.</span><textarea className="bdd-editor" value={form.steps} onChange={(event) => setField('steps', event.target.value)} placeholder="o usuário está na tela de login" /></label>
        <label>Quando <span className="field-hint">Descreva a ação ou os dados informados.</span><textarea value={form.test_data} onChange={(event) => setField('test_data', event.target.value)} placeholder="informa credenciais válidas e seleciona Entrar" /></label>
        <label>Então <span className="field-hint">Descreva o comportamento esperado.</span><textarea value={form.expected_result} onChange={(event) => setField('expected_result', event.target.value)} placeholder="o sistema libera o acesso à página inicial" /></label>
      </div>
      <div className="form-actions"><button className="text-button" type="button" onClick={closeCaseEditor}>{editingId ? 'Cancelar edição' : 'Cancelar criação'}</button><button className="primary-button" disabled={saving} type="submit">{saving ? 'Salvando…' : editingId ? 'Salvar alterações' : 'Criar caso'}</button></div>
    </form></div>}
    <section className="panel case-list"><div className="panel-header"><div><h2>Casos cadastrados</h2><p>{loading ? 'Carregando…' : `${visibleCases.length} caso(s) no filtro atual.`}</p></div></div>
      <div className="case-list-content">{!loading && visibleCases.length === 0 && <p className="empty-state">{selectedScenarioId ? 'Nenhum caso pertence ao cenário selecionado.' : 'Ainda não há casos de teste. Crie um caso geral ou importe um arquivo do Zephyr.'}</p>}{visibleCases.map((testCase) => <article className="case-summary" key={testCase.id}><div><span className="case-code">{testCase.code}</span><h3>{testCase.title}</h3>{testCase.zephyr_key && <p>Origem Zephyr: {testCase.zephyr_key}</p>}<p>Cenário: {testCase.scenario_name || 'Geral'}</p><p>Autor: {testCase.author_name}</p><p>Responsável: {testCase.responsible_email}</p><p>Revisor: {testCase.reviewer_email}</p><p>Supervisor: {testCase.supervisor_email || 'não definido'}</p></div><div className="case-summary-actions"><button className="case-action-button edit" type="button" onClick={() => edit(testCase)}><span aria-hidden="true">✎</span> Editar</button><button className="case-action-button delete" type="button" onClick={() => setCaseToDelete(testCase)}><span aria-hidden="true">×</span> Excluir</button></div></article>)}</div>
      <ApiState status={apiStatus} />
    </section></section>
    {showImportPanel && <form className="panel zephyr-import-panel" id="zephyr-import-panel" ref={importPanelRef} onSubmit={importZephyr}>
      <div className="panel-header"><div><p className="eyebrow">IMPORTAÇÃO DO ZEPHYR</p><h2>Importar casos e criar cenários</h2><p>Use o export original do Zephyr em Excel, XML ou CSV. Os folders agrupam os casos; revisor e supervisor são definidos para cada cenário criado.</p></div></div>
      <div className="form-fields compact-fields">
        <label>Arquivos do Zephyr *<span className="field-hint">Selecione um ou vários arquivos .xlsx, .xml ou .csv. Os folders de todos eles serão criados como cenários.</span><input type="file" multiple accept=".xlsx,.xml,.csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/xml,text/xml,text/csv" required onChange={(event) => setZephyrFiles(Array.from(event.target.files || []))} /></label>
        <label>Responsável pelos casos importados *<span className="field-hint">Este e-mail será aplicado a todos os casos, sem depender do campo Owner do Zephyr.</span><input type="email" value={responsibleEmail} onChange={(event) => setResponsibleEmail(event.target.value)} required /></label>
        <label>Revisor do cenário *<span className="field-hint">Decide o resultado final e valida as correções.</span><input type="email" value={reviewerEmail} onChange={(event) => setReviewerEmail(event.target.value)} required /></label>
        <label>Supervisor para escalonamento *<span className="field-hint">Dá a palavra final em contestações e atrasos.</span><input type="email" value={supervisorEmail} onChange={(event) => setSupervisorEmail(event.target.value)} placeholder="supervisor@exemplo.com" required /></label>
      </div>
      <div className="form-actions"><button className="text-button" type="button" onClick={() => setShowImportPanel(false)}>Cancelar importação</button><button className="primary-button" disabled={importing} type="submit">{importing ? 'Importando…' : 'Importar casos'}</button></div>
    </form>}
    <section className="panel scenario-list"><div className="panel-header"><div><h2>Cenários importados</h2><p>{loading ? 'Carregando…' : `${visibleScenarios.length} cenário(s) organizado(s) por folder.`}</p></div></div><div className="scenario-list-content">{!loading && visibleScenarios.length === 0 && <p className="empty-state">{selectedScenarioId ? 'Nenhum cenário corresponde ao filtro atual.' : 'Ainda não há cenários. Use “Importar do Zephyr” se quiser criar um a partir de um CSV.'}</p>}{visibleScenarios.map((scenario) => <article className="scenario-summary" key={scenario.id}><strong>{scenario.name}</strong><span>{scenario.test_case_count} caso(s) · {scenario.zephyr_folder}</span><small>Revisor: {scenario.reviewer_email}<br />Supervisor: {scenario.supervisor_email}</small></article>)}</div></section>
    <ConfirmationModal isOpen={Boolean(caseToDelete)} title="Excluir caso de teste?" description={caseToDelete ? `Você removerá ${caseToDelete.code} — ${caseToDelete.title}. Esta ação não pode ser desfeita.` : ''} confirmLabel="Excluir caso" tone="danger" onCancel={() => setCaseToDelete(null)} onConfirm={() => { if (caseToDelete) void remove(caseToDelete) }} />
    <Toast message={message} onDismiss={() => setMessage('')} />
  </main></div>
}

function AuditReviewModal({ audit, reviewItems, setReviewItems, busy, onClose, onFinalize }: {
  audit: AuditData
  reviewItems: Record<string, { result: 'CONFORMING' | 'NONCONFORMING' | 'NOT_APPLICABLE'; priority: 'LOW' | 'MEDIUM' | 'HIGH' }>
  setReviewItems: (items: Record<string, { result: 'CONFORMING' | 'NONCONFORMING' | 'NOT_APPLICABLE'; priority: 'LOW' | 'MEDIUM' | 'HIGH' }>) => void
  busy: boolean
  onClose: () => void
  onFinalize: () => void
}) {
  const canFinalize = audit.status === 'DRAFT' && audit.can_review
  const labelFor = (result: AuditItemData['result']) => result === 'CONFORMING' ? 'Conforme' : result === 'NOT_APPLICABLE' ? 'Não se aplica' : 'Não conforme'
  const toneFor = (result: AuditItemData['result']) => result === 'CONFORMING' ? 'success' : result === 'NOT_APPLICABLE' ? 'info' : 'danger'

  return <div className="modal-backdrop" role="presentation">
    <section className="audit-review-modal" role="dialog" aria-modal="true" aria-labelledby="audit-review-title">
      <div className="modal-heading"><div><p className="eyebrow">{canFinalize ? 'REVISÃO HUMANA' : 'RESULTADO DA AUDITORIA'}</p><h2 id="audit-review-title">{audit.test_case_code} · {audit.test_case_title}</h2><p>{canFinalize ? 'Confira a sugestão automática e defina o resultado final de cada campo.' : `Auditoria concluída por ${audit.auditor_name}.`}</p></div><button className="modal-close" type="button" aria-label="Fechar revisão" onClick={onClose}>×</button></div>
      <div className="audit-modal-list">{audit.items.map((item) => {
        const current = reviewItems[item.checklist_code]
        const result = canFinalize ? current?.result || 'CONFORMING' : item.final_result || item.result
        return <article className="audit-modal-item" key={item.checklist_code}><div><strong>{item.checklist_label}</strong><span>Sugestão: {labelFor(item.suggested_result)}</span><div className={`audit-field-value${item.field_value ? '' : ' is-empty'}`}><span>Conteúdo do caso de teste</span><p>{item.field_value || 'Campo não informado.'}</p></div>{item.note && <small>{item.note}</small>}</div>{canFinalize ? <div className="audit-modal-controls"><SiteSelect value={result || 'CONFORMING'} ariaLabel={`Resultado de ${item.checklist_label}`} options={[{ value: 'CONFORMING', label: 'Conforme', description: 'O campo atende ao que é esperado.' }, { value: 'NONCONFORMING', label: 'Não conforme', description: 'Gera uma não conformidade para correção.' }, { value: 'NOT_APPLICABLE', label: 'Não se aplica', description: 'O campo não é necessário neste caso.' }]} onChange={(value) => setReviewItems({ ...reviewItems, [item.checklist_code]: { result: value as 'CONFORMING' | 'NONCONFORMING' | 'NOT_APPLICABLE', priority: current?.priority || 'MEDIUM' } })} />{result === 'NONCONFORMING' && <SiteSelect value={current?.priority || 'MEDIUM'} ariaLabel={`Prioridade de ${item.checklist_label}`} options={[{ value: 'LOW', label: 'Prioridade baixa', description: 'Pode ser resolvida em até 10 dias úteis.' }, { value: 'MEDIUM', label: 'Prioridade média', description: 'Pode ser resolvida em até 5 dias úteis.' }, { value: 'HIGH', label: 'Prioridade alta', description: 'Pode ser resolvida em até 2 dias úteis.' }]} onChange={(value) => setReviewItems({ ...reviewItems, [item.checklist_code]: { result: 'NONCONFORMING', priority: value as 'LOW' | 'MEDIUM' | 'HIGH' } })} />}</div> : <span className={`status ${toneFor(result)}`}>{labelFor(result)}</span>}</article>
      })}</div>
      <div className="modal-actions"><button className="secondary-button" type="button" disabled={busy} onClick={onClose}>{canFinalize ? 'Cancelar' : 'Fechar'}</button>{canFinalize && <button className="primary-button" type="button" disabled={busy} onClick={onFinalize}>{busy ? 'Finalizando…' : 'Confirmar revisão e gerar NCs'}</button>}</div>
    </section>
  </div>
}

function AuditPage({ apiStatus, user, scenarios, selectedScenarioId, onScenarioChange, onBack, onOpenCases, onOpenNonconformities, onLogout, onOrganizationChange }: { apiStatus: ApiStatus; user: CurrentUser; scenarios: ScenarioData[]; selectedScenarioId: string; onScenarioChange: (value: string) => void; onBack: () => void; onOpenCases: () => void; onOpenNonconformities: () => void; onLogout: () => void; onOrganizationChange: (organizationId: string) => void }) {
  const [cases, setCases] = useState<TestCaseData[]>([])
  const [audits, setAudits] = useState<AuditData[]>([])
  const [selectedCaseId, setSelectedCaseId] = useState('')
  const [statusFilter, setStatusFilter] = useState<AuditStatusFilter>('ALL')
  const [loading, setLoading] = useState(true)
  const [runningId, setRunningId] = useState<string | null>(null)
  const [reviewAudit, setReviewAudit] = useState<AuditData | null>(null)
  const [reviewItems, setReviewItems] = useState<Record<string, { result: 'CONFORMING' | 'NONCONFORMING' | 'NOT_APPLICABLE'; priority: 'LOW' | 'MEDIUM' | 'HIGH' }>>({})
  const [message, setMessage] = useState('')

  const loadData = async () => {
    setLoading(true)
    try {
      const [casesResponse, auditsResponse] = await Promise.all([fetch('/api/test-cases', apiReadOptions), fetch('/api/audits', apiReadOptions)])
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
      setMessage('Sugestões automáticas criadas. O revisor deve confirmar cada item antes de gerar NCs.')
      await loadData()
    } catch (error) { setMessage(error instanceof Error ? error.message : 'Não foi possível executar a auditoria.') } finally { setRunningId(null) }
  }
  const openReview = (audit: AuditData) => {
    setReviewAudit(audit)
    setReviewItems(Object.fromEntries(audit.items.map((item) => [item.checklist_code, { result: item.suggested_result || item.result || 'CONFORMING', priority: 'MEDIUM' }])))
  }
  const finalizeReview = async () => {
    if (!reviewAudit) return
    setRunningId(reviewAudit.id)
    try {
      const items = reviewAudit.items.map((item) => ({ checklist_code: item.checklist_code, ...(reviewItems[item.checklist_code] || { result: 'CONFORMING', priority: 'MEDIUM' }) }))
      const response = await fetch(`/api/audits/${reviewAudit.id}/review`, { method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ items }) })
      const payload = await response.json().catch(() => ({})) as { detail?: string; nonconformity_count?: number }
      if (!response.ok) throw new Error(payload.detail || 'Não foi possível finalizar a revisão.')
      setReviewAudit(null)
      await loadData()
      setMessage(`Revisão finalizada. ${payload.nonconformity_count ?? 0} NC(s) confirmada(s).`)
    } catch (error) { setMessage(error instanceof Error ? error.message : 'Não foi possível finalizar a revisão.') } finally { setRunningId(null) }
  }

  const latestAuditByCase = new Map<string, AuditData>()
  for (const audit of audits) if (!latestAuditByCase.has(audit.test_case_id)) latestAuditByCase.set(audit.test_case_id, audit)
  const casesInScenario = selectedScenarioId ? cases.filter((testCase) => testCase.scenario_id === selectedScenarioId) : cases
  const visibleCases = casesInScenario.filter((testCase) => {
    if (selectedCaseId && testCase.id !== selectedCaseId) return false
    const audit = latestAuditByCase.get(testCase.id)
    const workflowReady = Boolean(testCase.reviewer_email && testCase.supervisor_email)
    if (statusFilter === 'MISSING_ROLES') return !workflowReady
    if (statusFilter === 'PENDING') return workflowReady && !audit
    if (statusFilter === 'WAITING_REVIEW') return audit?.status === 'DRAFT'
    if (statusFilter === 'COMPLETED') return audit?.status === 'COMPLETED'
    return true
  })

  return <div className="app-shell"><Sidebar active="audits" user={user} onDashboard={onBack} onCases={onOpenCases} onAudits={() => undefined} onNonconformities={onOpenNonconformities} onLogout={onLogout} onOrganizationChange={onOrganizationChange} /><main>
    <header className="topbar"><div><p className="eyebrow">AUDITORIA ASSISTIDA</p><h1>Auditorias de casos de teste</h1><p className="subtitle">Execute o caso, revise as sugestões e confirme o resultado final em uma única fila.</p></div><div className="topbar-actions audit-filter-actions"><ScenarioFilter scenarios={scenarios} value={selectedScenarioId} onChange={(value) => { setSelectedCaseId(''); onScenarioChange(value) }} /><label className="scenario-filter"><span>Filtrar caso</span><SiteSelect value={selectedCaseId} onChange={setSelectedCaseId} ariaLabel="Filtrar por caso de teste" options={[{ value: '', label: 'Todos os casos', description: 'Exibe todos os casos no cenário atual.' }, ...casesInScenario.map((testCase) => ({ value: testCase.id, label: `${testCase.code} · ${testCase.title}`, description: testCase.scenario_name || 'Caso geral' }))]} /></label><label className="scenario-filter"><span>Filtrar status</span><SiteSelect value={statusFilter} onChange={(value) => setStatusFilter(value as AuditStatusFilter)} ariaLabel="Filtrar por status da auditoria" options={[{ value: 'ALL', label: 'Todos os status', description: 'Exibe toda a fila.' }, { value: 'PENDING', label: 'Pendentes', description: 'Prontos para executar.' }, { value: 'WAITING_REVIEW', label: 'Aguardando revisão', description: 'Aguardam decisão do revisor.' }, { value: 'COMPLETED', label: 'Concluídas', description: 'Revisão finalizada.' }, { value: 'MISSING_ROLES', label: 'Configurar papéis', description: 'Faltam responsável, revisor ou supervisor.' }]} /></label></div></header>
    <section className="panel audit-table-panel"><div className="panel-header"><div><h2>Fila de auditorias</h2><p>Use a ação indicada em cada linha para avançar o caso para a próxima etapa.</p></div></div>
      <div className="table-wrap"><table className="audit-table"><thead><tr><th>Caso de teste</th><th>Cenário</th><th>Status</th><th>Resultado</th><th>Ação</th></tr></thead><tbody>
        {loading ? <tr><td colSpan={5}><p className="empty-state">Carregando casos e auditorias…</p></td></tr> : visibleCases.length === 0 ? <tr><td colSpan={5}><p className="empty-state">{selectedCaseId || statusFilter !== 'ALL' ? 'Nenhum caso corresponde aos filtros selecionados.' : selectedScenarioId ? 'Nenhum caso pertence ao cenário selecionado.' : 'Cadastre ou importe um caso de teste para iniciar.'}</p></td></tr> : visibleCases.map((testCase) => {
          const audit = latestAuditByCase.get(testCase.id)
          const workflowReady = Boolean(testCase.reviewer_email && testCase.supervisor_email)
          const waitingReview = audit?.status === 'DRAFT'
          const completed = audit?.status === 'COMPLETED'
          const statusLabel = !workflowReady ? 'Configurar papéis' : !audit ? 'Pendente' : waitingReview ? 'Aguardando revisão' : 'Concluída'
          const statusTone = !workflowReady ? 'danger' : !audit ? 'warning' : waitingReview ? 'info' : 'success'
          return <tr key={testCase.id}><td><span className="case-code">{testCase.code}</span><strong>{testCase.title}</strong></td><td>{testCase.scenario_name || 'Geral'}</td><td><span className={`status ${statusTone}`}>{statusLabel}</span></td><td>{completed ? <strong>{audit.adherence_percentage ?? 0}% · {audit.nonconformity_count} NC(s) gerada(s)</strong> : '—'}</td><td>{!workflowReady ? <button className="secondary-button table-action" type="button" onClick={onOpenCases}>Abrir caso e definir papéis</button> : !audit ? <button className="primary-button table-action" disabled={runningId === testCase.id} type="button" onClick={() => void runAudit(testCase)}>{runningId === testCase.id ? 'Executando…' : 'Executar auditoria'}</button> : waitingReview && audit.can_review ? <button className="primary-button table-action" type="button" onClick={() => openReview(audit)}>Revisar auditoria</button> : waitingReview ? <button className="secondary-button table-action" disabled type="button">Aguardando revisor</button> : <button className="secondary-button table-action" type="button" onClick={() => openReview(audit)}>Ver resultado</button>}</td></tr>
        })}
      </tbody></table></div><ApiState status={apiStatus} />
    </section>
    {reviewAudit && <AuditReviewModal audit={reviewAudit} reviewItems={reviewItems} setReviewItems={setReviewItems} busy={runningId === reviewAudit.id} onClose={() => setReviewAudit(null)} onFinalize={() => void finalizeReview()} />}
    <Toast message={message} onDismiss={() => setMessage('')} />
  </main></div>
}
function NonconformitiesPage({ apiStatus, user, scenarios, selectedScenarioId, onScenarioChange, onBack, onOpenCases, onOpenAudits, onLogout, onOrganizationChange }: { apiStatus: ApiStatus; user: CurrentUser; scenarios: ScenarioData[]; selectedScenarioId: string; onScenarioChange: (value: string) => void; onBack: () => void; onOpenCases: () => void; onOpenAudits: () => void; onLogout: () => void; onOrganizationChange: (organizationId: string) => void }) {
  const [nonconformities, setNonconformities] = useState<NonconformityData[]>([])
  const [lifecycleFilter, setLifecycleFilter] = useState<NonconformityFilter>('ALL')
  const [drafts, setDrafts] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState<string | null>(null)
  const [message, setMessage] = useState('')
  const [reviewTarget, setReviewTarget] = useState<{ nonconformity: NonconformityData; evidence: EvidenceData; approved: boolean } | null>(null)
  const [supervisorDrafts, setSupervisorDrafts] = useState<Record<string, string>>({})

  const loadNonconformities = async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/nonconformities', apiReadOptions)
      if (!response.ok) throw new Error()
      setNonconformities(await response.json() as NonconformityData[])
    } catch { setMessage('Não foi possível carregar as não conformidades.') } finally { setLoading(false) }
  }

  useEffect(() => { void loadNonconformities() }, [])
  const submitEvidence = async (nonconformity: NonconformityData, evidenceType: 'CORRECTION' | 'CONTESTATION') => {
    const description = (drafts[nonconformity.id] || '').trim()
    if (description.length < 3) { setMessage('Descreva a correção ou a contestação antes de enviar.'); return }
    setSending(nonconformity.id)
    try {
      const response = await fetch(`/api/nonconformities/${nonconformity.id}/evidences`, { method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ description, evidence_type: evidenceType }) })
      const payload = await response.json().catch(() => ({})) as { detail?: string }
      if (!response.ok) throw new Error(payload.detail || 'Não foi possível enviar a evidência.')
      setDrafts((current) => ({ ...current, [nonconformity.id]: '' }))
      setMessage(evidenceType === 'CORRECTION' ? 'Correção enviada para validação do auditor.' : 'Contestação enviada para análise do auditor.')
      await loadNonconformities()
    } catch (error) { setMessage(error instanceof Error ? error.message : 'Não foi possível enviar a evidência.') } finally { setSending(null) }
  }
  const reviewEvidence = async (nonconformity: NonconformityData, evidence: EvidenceData, approved: boolean) => {
    setSending(nonconformity.id)
    try {
      const response = await fetch(`/api/nonconformities/${nonconformity.id}/review`, { method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ evidence_id: evidence.id, approved }) })
      const payload = await response.json().catch(() => ({})) as { detail?: string }
      if (!response.ok) throw new Error(payload.detail || 'Não foi possível revisar a evidência.')
      setMessage(approved ? 'Evidência aprovada e NC resolvida.' : 'Evidência devolvida para correção.')
      await loadNonconformities()
    } catch (error) { setMessage(error instanceof Error ? error.message : 'Não foi possível revisar a evidência.') } finally { setSending(null) }
  }
  const retryNotification = async (nonconformity: NonconformityData) => {
    setSending(nonconformity.id)
    try {
      const response = await fetch(`/api/nonconformities/${nonconformity.id}/notify`, { method: 'POST', credentials: 'include' })
      const payload = await response.json().catch(() => ({})) as { email_sent?: boolean; detail?: string }
      if (!response.ok) throw new Error(payload.detail || 'Não foi possível reenviar o e-mail.')
      setMessage(payload.email_sent ? 'E-mail de lembrete enviado.' : 'A Resend recusou o e-mail. Confira a conta e o domínio configurados.')
    } catch (error) { setMessage(error instanceof Error ? error.message : 'Não foi possível reenviar o e-mail.') } finally { setSending(null) }
  }
  const decideAsSupervisor = async (nonconformity: NonconformityData, approved: boolean) => {
    const comment = (supervisorDrafts[nonconformity.id] || '').trim()
    if (comment.length < 3) { setMessage('Registre a justificativa da decisão final antes de continuar.'); return }
    setSending(nonconformity.id)
    try {
      const response = await fetch(`/api/nonconformities/${nonconformity.id}/supervisor-decision`, { method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ approved, comment }) })
      const payload = await response.json().catch(() => ({})) as { detail?: string }
      if (!response.ok) throw new Error(payload.detail || 'Não foi possível registrar a decisão final.')
      setSupervisorDrafts((all) => ({ ...all, [nonconformity.id]: '' }))
      setMessage(approved ? 'Decisão final registrada: NC resolvida.' : 'Decisão final registrada: NC devolvida para correção.')
      await loadNonconformities()
    } catch (error) { setMessage(error instanceof Error ? error.message : 'Não foi possível registrar a decisão final.') } finally { setSending(null) }
  }
  const formatDeadline = (date: string | null) => date ? new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(date)) : 'não definido'
  const statusLabel: Record<NonconformityData['status'], string> = { OPEN: 'Aberta', IN_CORRECTION: 'Em correção', WAITING_VALIDATION: 'Aguardando validação', CONTESTED: 'Contestada', ESCALATED: 'Escalada', RESOLVED: 'Resolvida' }
  const statusTone: Record<NonconformityData['status'], string> = { OPEN: 'danger', IN_CORRECTION: 'warning', WAITING_VALIDATION: 'info', CONTESTED: 'contested', ESCALATED: 'escalated', RESOLVED: 'success' }
  const lifecycleEventLabel: Record<string, string> = {
    GENERATED: 'Não conformidade gerada',
    CORRECTION_SUBMITTED: 'Correção enviada para validação',
    EVIDENCE_APPROVED: 'Correção aprovada',
    EVIDENCE_RETURNED: 'Correção devolvida',
    CONTESTATION_ESCALATED: 'Contestação enviada ao supervisor',
    ESCALATED: 'Decisão escalada ao supervisor',
    SUPERVISOR_DEADLINE_OVERDUE: 'Prazo de decisão do supervisor vencido',
    SUPERVISOR_DECISION: 'Decisão final do supervisor',
  }
  const lifecycleStatusLabel = (status: string | null) => status ? statusLabel[status as NonconformityData['status']] || 'Status não identificado' : null
  const severityLabel: Record<NonconformityData['severity'], string> = { LOW: 'Baixa', MEDIUM: 'Média', HIGH: 'Alta' }
  const severityTone: Record<NonconformityData['severity'], string> = { LOW: 'low', MEDIUM: 'medium', HIGH: 'high' }
  const slaLabel: Record<NonconformityData['severity'], string> = {
    HIGH: 'SLA: responsável 2 dias úteis · revisor 1 dia útil · supervisor 1 dia útil',
    MEDIUM: 'SLA: responsável 5 dias úteis · revisor 2 dias úteis · supervisor 2 dias úteis',
    LOW: 'SLA: responsável 10 dias úteis · revisor 3 dias úteis · supervisor 3 dias úteis',
  }
  const visibleNonconformities = nonconformities.filter((nonconformity) => {
    if (selectedScenarioId && nonconformity.scenario_id !== selectedScenarioId) return false
    return lifecycleFilter === 'ALL' || nonconformity.status === lifecycleFilter
  })
  const lifecycleCount = (status: NonconformityFilter) => nonconformities.filter((nonconformity) => (!selectedScenarioId || nonconformity.scenario_id === selectedScenarioId) && (status === 'ALL' || nonconformity.status === status)).length

  return <div className="app-shell"><Sidebar active="nonconformities" user={user} onDashboard={onBack} onCases={onOpenCases} onAudits={onOpenAudits} onNonconformities={() => undefined} onLogout={onLogout} onOrganizationChange={onOrganizationChange} /><main>
    <header className="topbar"><div><p className="eyebrow">CICLO DE VIDA E ESCALONAMENTO</p><h1>Não conformidades</h1><p className="subtitle">Acompanhe cada NC desde a geração, passando por correção ou contestação, até a decisão final.</p></div><div className="topbar-actions"><ScenarioFilter scenarios={scenarios} value={selectedScenarioId} onChange={onScenarioChange} /></div></header>
    <section className="nonconformity-list">
      <section className="lifecycle-filter-bar" aria-label="Filtros por etapa da não conformidade"><p>Filtrar por etapa</p><div className="lifecycle-filter-actions">{([{ value: 'ALL', label: 'Todas' }, { value: 'OPEN', label: 'Abertas' }, { value: 'IN_CORRECTION', label: 'Para correção' }, { value: 'WAITING_VALIDATION', label: 'Para revisão' }, { value: 'ESCALATED', label: 'Escaladas' }, { value: 'RESOLVED', label: 'Resolvidas' }] as { value: NonconformityFilter; label: string }[]).map((filter) => <button className={`lifecycle-filter-button ${lifecycleFilter === filter.value ? 'active' : ''}`} type="button" aria-pressed={lifecycleFilter === filter.value} key={filter.value} onClick={() => setLifecycleFilter(filter.value)}>{filter.label}<span>{lifecycleCount(filter.value)}</span></button>)}</div></section>
      {!loading && visibleNonconformities.length === 0 && <section className="panel empty-state-panel"><div><h2>{lifecycleFilter !== 'ALL' ? 'Nenhuma NC nesta etapa' : selectedScenarioId ? 'Nenhuma NC neste cenário' : 'Nenhuma não conformidade atribuída'}</h2><p className="empty-state">{lifecycleFilter !== 'ALL' ? 'Altere a etapa selecionada ou escolha “Todas” para consultar as demais NCs.' : selectedScenarioId ? 'Altere ou limpe o filtro para consultar os demais cenários.' : 'Quando uma auditoria confirmar um desvio, a não conformidade aparecerá aqui.'}</p></div><button className="secondary-button" type="button" onClick={lifecycleFilter !== 'ALL' ? () => setLifecycleFilter('ALL') : selectedScenarioId ? () => onScenarioChange('') : onOpenAudits}>{lifecycleFilter !== 'ALL' ? 'Ver todas as etapas' : selectedScenarioId ? 'Limpar filtro' : 'Abrir auditorias'}</button></section>}
      {visibleNonconformities.map((nonconformity) => <article className="panel nonconformity-card" key={nonconformity.id}>
        <div className="nc-header"><div><span className="case-code">{nonconformity.code} · {nonconformity.test_case_code}</span><h2>{nonconformity.test_case_title}</h2><p>{nonconformity.description}</p></div><div className="nc-badges"><span className={`priority ${severityTone[nonconformity.severity]}`}>Prioridade {severityLabel[nonconformity.severity]}</span><span className={`status ${statusTone[nonconformity.status]}`}>{statusLabel[nonconformity.status]}</span></div></div>
        <p className="nc-meta">Responsável: {nonconformity.assignee_email} · Supervisor: {nonconformity.supervisor_email || 'não definido'}</p>
        <p className="sla-description">{slaLabel[nonconformity.severity]} <span>(seg. a sex.; sem feriados no MVP)</span></p>
        {nonconformity.status === 'RESOLVED' ? <div className="lifecycle-complete" role="status"><span aria-hidden="true">✓</span><div><strong>Ciclo encerrado</strong><p>A correção foi aprovada e não há prazos ou escalonamentos ativos.</p></div></div> : <div className="deadline-grid"><span><strong>Correção/contestação</strong>{formatDeadline(nonconformity.resolution_due_at)}</span><span><strong>Aprovar ou reprovar</strong>{formatDeadline(nonconformity.review_due_at)}</span><span><strong>{nonconformity.escalated_at ? 'Escalonada em' : 'Escalonamento automático'}</strong>{nonconformity.escalated_at ? formatDeadline(nonconformity.escalated_at) : formatDeadline(nonconformity.escalation_due_at)}</span><span><strong>Decisão do supervisor</strong>{formatDeadline(nonconformity.supervisor_decision_due_at)}</span></div>}
        {nonconformity.status !== 'RESOLVED' && (nonconformity.can_submit_evidence || nonconformity.can_review || nonconformity.can_decide_final) && <button className="secondary-button secondary-compact" disabled={sending === nonconformity.id} type="button" onClick={() => void retryNotification(nonconformity)}><span aria-hidden="true">↗</span> {sending === nonconformity.id ? 'Enviando…' : 'Reenviar e-mail'}</button>}
        {nonconformity.can_submit_evidence && nonconformity.status !== 'RESOLVED' && <div className="evidence-form"><textarea value={drafts[nonconformity.id] || ''} onChange={(event) => setDrafts((current) => ({ ...current, [nonconformity.id]: event.target.value }))} placeholder="Descreva o que foi corrigido ou o motivo da contestação." /><div><button className="primary-button" disabled={sending === nonconformity.id} type="button" onClick={() => void submitEvidence(nonconformity, 'CORRECTION')}>Enviar correção</button><button className="secondary-button" disabled={sending === nonconformity.id} type="button" onClick={() => void submitEvidence(nonconformity, 'CONTESTATION')}>Contestar NC</button></div></div>}
        <div className="evidence-list">{nonconformity.evidences.map((evidence) => <article className="evidence-item" key={evidence.id}><div><strong>{evidence.evidence_type === 'CORRECTION' ? 'Correção' : 'Contestação'} por {evidence.submitted_by_name}</strong><p>{evidence.description}</p></div><span className={`status ${evidence.status === 'APPROVED' ? 'success' : evidence.status === 'REJECTED' ? 'danger' : 'warning'}`}>{evidence.status === 'SUBMITTED' ? 'Pendente' : evidence.status === 'APPROVED' ? 'Aprovada' : 'Devolvida'}</span>{nonconformity.can_review && evidence.status === 'SUBMITTED' && <div className="review-actions"><button className="review-button approve" disabled={sending === nonconformity.id} type="button" onClick={() => setReviewTarget({ nonconformity, evidence, approved: true })}><span aria-hidden="true">✓</span> Aprovar correção</button><button className="review-button return" disabled={sending === nonconformity.id} type="button" onClick={() => setReviewTarget({ nonconformity, evidence, approved: false })}><span aria-hidden="true">↩</span> Devolver para correção</button></div>}</article>)}</div>
        {nonconformity.can_decide_final && <section className="supervisor-decision"><h3>Decisão final do supervisor</h3><p>{nonconformity.history.some((event) => event.event_type === 'CONTESTATION_ESCALATED') ? 'A NC foi contestada e aguarda a sua palavra final.' : 'O prazo de uma etapa venceu e a decisão foi escalonada para você.'} Decida até {formatDeadline(nonconformity.supervisor_decision_due_at)}.</p><textarea value={supervisorDrafts[nonconformity.id] || ''} onChange={(event) => setSupervisorDrafts((all) => ({ ...all, [nonconformity.id]: event.target.value }))} placeholder="Justificativa da decisão final" /><div><button className="review-button approve" disabled={sending === nonconformity.id} type="button" onClick={() => void decideAsSupervisor(nonconformity, true)}>Encerrar NC</button><button className="review-button return" disabled={sending === nonconformity.id} type="button" onClick={() => void decideAsSupervisor(nonconformity, false)}>Devolver para correção</button></div></section>}
        <details className="lifecycle-history"><summary>Ver ciclo de vida completo ({nonconformity.history.length})</summary><ol>{nonconformity.history.map((event) => <li key={event.id}><strong>{lifecycleEventLabel[event.event_type] || 'Atualização registrada'}</strong><span>{event.message}</span>{event.new_status && <small>Estado: {lifecycleStatusLabel(event.previous_status) || 'Ainda não definido'} → {lifecycleStatusLabel(event.new_status)}</small>}<small>{event.actor_email || 'Sistema'} · {formatDeadline(event.created_at)}</small></li>)}</ol></details>
      </article>)}
      <ApiState status={apiStatus} />
    </section>
    <ConfirmationModal isOpen={Boolean(reviewTarget)} title={reviewTarget?.approved ? 'Aprovar correção?' : 'Devolver para correção?'} description={reviewTarget?.approved ? 'Ao aprovar, a não conformidade será marcada como resolvida.' : 'A evidência será devolvida ao responsável para que ele possa corrigir ou complementar a entrega.'} confirmLabel={reviewTarget?.approved ? 'Aprovar e resolver NC' : 'Devolver evidência'} tone={reviewTarget?.approved ? 'primary' : 'danger'} busy={sending === reviewTarget?.nonconformity.id} onCancel={() => setReviewTarget(null)} onConfirm={() => { if (reviewTarget) { void reviewEvidence(reviewTarget.nonconformity, reviewTarget.evidence, reviewTarget.approved).finally(() => setReviewTarget(null)) } }} />
    <Toast message={message} onDismiss={() => setMessage('')} />
  </main></div>
}

function Dashboard({ apiStatus, user, scenarios, selectedScenarioId, onScenarioChange, onLogout, onOpenCases, onOpenAudits, onOpenNonconformities, onOrganizationChange }: { apiStatus: ApiStatus; user: CurrentUser; scenarios: ScenarioData[]; selectedScenarioId: string; onScenarioChange: (value: string) => void; onLogout: () => void; onOpenCases: () => void; onOpenAudits: () => void; onOpenNonconformities: () => void; onOrganizationChange: (organizationId: string) => void }) {
  const [cases, setCases] = useState<TestCaseData[]>([])
  const [audits, setAudits] = useState<AuditData[]>([])
  const [nonconformities, setNonconformities] = useState<NonconformityData[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const loadDashboard = async () => {
      setLoading(true)
      try {
        const [casesResponse, auditsResponse, nonconformitiesResponse] = await Promise.all([
          fetch('/api/test-cases', apiReadOptions),
          fetch('/api/audits', apiReadOptions),
          fetch('/api/nonconformities', apiReadOptions),
        ])
        if (!casesResponse.ok || !auditsResponse.ok || !nonconformitiesResponse.ok) throw new Error()
        setCases(await casesResponse.json() as TestCaseData[])
        setAudits(await auditsResponse.json() as AuditData[])
        setNonconformities(await nonconformitiesResponse.json() as NonconformityData[])
      } finally { setLoading(false) }
    }
    void loadDashboard()
  }, [])

  const scopedCases = selectedScenarioId ? cases.filter((testCase) => testCase.scenario_id === selectedScenarioId) : cases
  const scopedAudits = selectedScenarioId ? audits.filter((audit) => audit.scenario_id === selectedScenarioId) : audits
  const scopedNonconformities = selectedScenarioId ? nonconformities.filter((nonconformity) => nonconformity.scenario_id === selectedScenarioId) : nonconformities
  const statusLabel: Record<NonconformityData['status'], string> = { OPEN: 'Aberta', IN_CORRECTION: 'Em correção', WAITING_VALIDATION: 'Aguardando validação', CONTESTED: 'Contestada', ESCALATED: 'Escalada', RESOLVED: 'Resolvida' }
  const statusTone: Record<NonconformityData['status'], string> = { OPEN: 'danger', IN_CORRECTION: 'warning', WAITING_VALIDATION: 'info', CONTESTED: 'contested', ESCALATED: 'escalated', RESOLVED: 'success' }
  const latestNonconformityByCase = new Map<string, NonconformityData>()
  scopedNonconformities.forEach((nonconformity) => {
    if (!latestNonconformityByCase.has(nonconformity.test_case_code)) latestNonconformityByCase.set(nonconformity.test_case_code, nonconformity)
  })
  const recentAudits = scopedAudits.slice(0, 3)
  const openNonconformities = scopedNonconformities.filter((nonconformity) => nonconformity.status !== 'RESOLVED')
  const averageAdherence = scopedAudits.length ? Math.round(scopedAudits.reduce((total, audit) => total + (audit.adherence_percentage ?? 0), 0) / scopedAudits.length) : null
  const averageOriginalAdherence = scopedAudits.length ? Math.round(scopedAudits.reduce((total, audit) => total + (audit.original_adherence_percentage ?? audit.adherence_percentage ?? 0), 0) / scopedAudits.length) : null
  const adherenceDelta = averageAdherence !== null && averageOriginalAdherence !== null ? averageAdherence - averageOriginalAdherence : null
  const auditedCaseIds = new Set(scopedAudits.map((audit) => audit.test_case_id))
  const casesWithoutAudit = scopedCases.filter((testCase) => !auditedCaseIds.has(testCase.id)).length
  const dueLabel = (deadline: string | null) => {
    if (!deadline) return 'Sem prazo ativo'
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    const due = new Date(deadline)
    due.setHours(0, 0, 0, 0)
    const days = Math.round((due.getTime() - today.getTime()) / 86_400_000)
    if (days < 0) return 'Atrasada'
    if (days === 0) return 'Hoje'
    if (days === 1) return 'Amanhã'
    return `Em ${days} dias`
  }
  const actions = [
    ...openNonconformities.map((nonconformity) => ({
      id: nonconformity.id,
      title: nonconformity.status === 'WAITING_VALIDATION' ? `${nonconformity.code} aguarda validação` : nonconformity.status === 'ESCALATED' ? `${nonconformity.code} aguarda decisão final` : `${nonconformity.code} ${statusLabel[nonconformity.status].toLowerCase()}`,
      description: `${nonconformity.test_case_code} · ${nonconformity.test_case_title}`,
      meta: dueLabel(nonconformity.status === 'WAITING_VALIDATION' ? nonconformity.review_due_at : nonconformity.status === 'ESCALATED' ? nonconformity.supervisor_decision_due_at : nonconformity.resolution_due_at),
      tone: nonconformity.status === 'WAITING_VALIDATION' ? 'violet' : 'red',
      target: 'nonconformities' as const,
    })),
    ...(casesWithoutAudit ? [{ id: 'cases-without-audit', title: 'Casos sem auditoria', description: 'Aguardam a primeira verificação.', meta: `${casesWithoutAudit} caso${casesWithoutAudit === 1 ? '' : 's'}`, tone: 'blue', target: 'audits' as const }] : []),
  ].slice(0, 3)

  return <div className="app-shell"><Sidebar active="dashboard" user={user} onDashboard={() => undefined} onCases={onOpenCases} onAudits={onOpenAudits} onNonconformities={onOpenNonconformities} onLogout={onLogout} onOrganizationChange={onOrganizationChange} /><main id="dashboard">
    <header className="topbar"><div><p className="eyebrow">PROJETO CHECKOUT</p><h1>Visão geral da qualidade</h1><p className="subtitle">Acompanhe auditorias, aderência e correções dos casos de teste.</p></div><div className="topbar-actions"><ScenarioFilter scenarios={scenarios} value={selectedScenarioId} onChange={onScenarioChange} /><button className="primary-button" type="button" onClick={onOpenAudits}>Abrir fila de auditorias <span aria-hidden="true">→</span></button></div></header>
    <section className="metrics" aria-label="Indicadores">
<article className="metric-card"><span className="metric-icon blue">≡</span><div><span>Casos de teste</span><strong>{loading ? '—' : scopedCases.length}</strong></div><small>{loading ? 'Carregando…' : scopedCases.length ? `${scopedCases.length} caso${scopedCases.length === 1 ? '' : 's'} cadastrado${scopedCases.length === 1 ? '' : 's'}` : 'Nenhum caso cadastrado'}</small></article>
<article className="metric-card"><span className="metric-icon violet">✓</span><div><span>Auditorias realizadas</span><strong>{loading ? '—' : scopedAudits.length}</strong></div><small>{loading ? 'Carregando…' : scopedAudits.length ? `${scopedAudits.length} registro${scopedAudits.length === 1 ? '' : 's'} concluído${scopedAudits.length === 1 ? '' : 's'}` : 'Nenhuma auditoria realizada'}</small></article>
      <article className="metric-card"><span className="metric-icon red">!</span><div><span>NCs abertas</span><strong>{loading ? '—' : openNonconformities.length}</strong></div><small>{loading ? 'Carregando…' : openNonconformities.length ? `${openNonconformities.length} requer${openNonconformities.length === 1 ? '' : 'em'} ação` : 'Nenhuma pendência aberta'}</small></article>
      <article className="metric-card"><span className="metric-icon green">↗</span><div><span>Aderência média atual</span><strong>{loading ? '—' : averageAdherence === null ? '—' : `${averageAdherence}%`}</strong></div><small className={adherenceDelta !== null && adherenceDelta > 0 ? 'positive' : ''}>{loading ? 'Carregando…' : averageAdherence === null ? 'Sem auditorias concluídas' : adherenceDelta === null || adherenceDelta === 0 ? 'Sem alteração desde antes da auditoria' : adherenceDelta > 0 ? `+${adherenceDelta} p.p. desde antes da auditoria` : `${adherenceDelta} p.p. desde antes da auditoria`}</small></article>
    </section>
    <section className="content-grid"><article className="panel cases-panel" id="test-cases"><div className="panel-header"><div><h2>Aderência dos últimos casos</h2><p>Comparação entre antes da auditoria e a aderência atual dos três casos mais recentes.</p></div><button className="text-button" type="button" onClick={onOpenAudits}>Ver fila →</button></div><div className="table-wrap"><table><thead><tr><th>Caso de teste</th><th>Auditor</th><th>Antes da auditoria</th><th>Aderência atual</th><th>Estado</th></tr></thead><tbody>{loading ? <tr><td colSpan={5}><p className="empty-state">Carregando auditorias…</p></td></tr> : recentAudits.length === 0 ? <tr><td colSpan={5}><p className="empty-state">Nenhuma auditoria realizada ainda.</p></td></tr> : recentAudits.map((audit) => { const nonconformity = latestNonconformityByCase.get(audit.test_case_code); const tone = nonconformity ? statusTone[nonconformity.status] : audit.nonconformity_count ? 'danger' : 'success'; const label = nonconformity ? statusLabel[nonconformity.status] : audit.nonconformity_count ? 'Não conforme' : 'Conforme'; const originalAdherence = audit.original_adherence_percentage ?? audit.adherence_percentage ?? 0; const currentAdherence = audit.adherence_percentage ?? 0; const delta = currentAdherence - originalAdherence; return <tr key={audit.id}><td><span className="case-code">{audit.test_case_code}</span><strong>{audit.test_case_title}</strong></td><td>{audit.auditor_name}</td><td><strong className="adherence-before">{originalAdherence}%</strong></td><td><div className="progress-row"><span className="progress-track"><span style={{ width: `${currentAdherence}%` }} /></span><strong>{currentAdherence}%</strong></div>{delta !== 0 && <small className={delta > 0 ? 'adherence-change positive' : 'adherence-change'}>{delta > 0 ? `+${delta}` : delta} p.p.</small>}</td><td><span className={`status ${tone}`}>{label}</span></td></tr> })}</tbody></table></div></article>
      <aside className="panel next-panel"><div className="panel-header"><div><h2>Próximas ações</h2><p>Itens que precisam de atenção.</p></div></div><ul className="action-list">{loading ? <li><div><strong>Carregando ações…</strong><span>Consultando os dados da equipe.</span></div></li> : actions.length === 0 ? <li><div><strong>Nenhuma ação pendente</strong><span>Não há NCs abertas ou casos aguardando auditoria.</span></div></li> : actions.map((action) => <li key={action.id}><span className={`action-dot ${action.tone}`} /><div><strong>{action.title}</strong><span>{action.description}</span></div><b>{action.meta}</b><button className="action-open-button" type="button" onClick={action.target === 'audits' ? onOpenAudits : onOpenNonconformities}>Abrir <span aria-hidden="true">→</span></button></li>)}</ul><ApiState status={apiStatus} /></aside>
    </section>
  </main></div>
}

function App() {
  const [apiStatus, setApiStatus] = useState<ApiStatus>('checking')
  const [user, setUser] = useState<CurrentUser | null>(null)
  const [scenarios, setScenarios] = useState<ScenarioData[]>([])
  const [selectedScenarioId, setSelectedScenarioId] = useState(() => window.sessionStorage.getItem('testcheck-scenario-filter') || '')
  const [loadingSession, setLoadingSession] = useState(true)
  const [view, setView] = useState<'dashboard' | 'test-cases' | 'audits' | 'nonconformities'>(() => {
    if (window.location.hash === '#test-cases') return 'test-cases'
    if (window.location.hash === '#audits') return 'audits'
    if (window.location.hash === '#nonconformities') return 'nonconformities'
    return 'dashboard'
  })
  useEffect(() => {
    const loadSession = async () => {
      try {
        const health = await fetch('/api/health', apiReadOptions)
        if (!health.ok) throw new Error('API indisponível')
        setApiStatus('online')
        const me = await fetch('/api/auth/me', apiReadOptions)
        if (me.ok) setUser(await me.json() as CurrentUser)
      } catch { setApiStatus('offline') } finally { setLoadingSession(false) }
    }
    void loadSession()
  }, [])
  const loadScenarios = async () => {
    try {
      const response = await fetch('/api/scenarios', apiReadOptions)
      if (!response.ok) throw new Error()
      const loadedScenarios = await response.json() as ScenarioData[]
      setScenarios(loadedScenarios)
      setSelectedScenarioId((current) => loadedScenarios.some((scenario) => scenario.id === current) ? current : '')
    } catch { setScenarios([]) }
  }
  useEffect(() => {
    if (user?.active_organization) void loadScenarios()
    else setScenarios([])
  }, [user])
  useEffect(() => { window.sessionStorage.setItem('testcheck-scenario-filter', selectedScenarioId) }, [selectedScenarioId])
  const logout = async () => { await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' }); setUser(null); setSelectedScenarioId(''); setView('dashboard') }
  const selectOrganization = async (organizationId: string) => {
    if (user?.active_organization?.id === organizationId) return
    const response = await fetch('/api/organizations/select', { method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ organization_id: organizationId }) })
    if (!response.ok) return
    setSelectedScenarioId('')
    setScenarios([])
    setUser(await response.json() as CurrentUser)
    setView('dashboard')
  }
  if (loadingSession) return <main className="loading-page">Carregando TestCheck…</main>
  if (!user) return <AuthScreen apiStatus={apiStatus} onAuthenticated={setUser} />
  if (!user.active_organization) return <OrganizationSetupScreen user={user} onReady={setUser} onLogout={logout} />
  if (view === 'test-cases') return <TestCasesPage key={user.active_organization.id} apiStatus={apiStatus} user={user} selectedScenarioId={selectedScenarioId} onScenarioChange={setSelectedScenarioId} onScenariosChanged={loadScenarios} onBack={() => setView('dashboard')} onOpenAudits={() => setView('audits')} onOpenNonconformities={() => setView('nonconformities')} onLogout={logout} onOrganizationChange={selectOrganization} />
  if (view === 'audits') return <AuditPage key={user.active_organization.id} apiStatus={apiStatus} user={user} scenarios={scenarios} selectedScenarioId={selectedScenarioId} onScenarioChange={setSelectedScenarioId} onBack={() => setView('dashboard')} onOpenCases={() => setView('test-cases')} onOpenNonconformities={() => setView('nonconformities')} onLogout={logout} onOrganizationChange={selectOrganization} />
  if (view === 'nonconformities') return <NonconformitiesPage key={user.active_organization.id} apiStatus={apiStatus} user={user} scenarios={scenarios} selectedScenarioId={selectedScenarioId} onScenarioChange={setSelectedScenarioId} onBack={() => setView('dashboard')} onOpenCases={() => setView('test-cases')} onOpenAudits={() => setView('audits')} onLogout={logout} onOrganizationChange={selectOrganization} />
  return <Dashboard key={user.active_organization.id} apiStatus={apiStatus} user={user} scenarios={scenarios} selectedScenarioId={selectedScenarioId} onScenarioChange={setSelectedScenarioId} onLogout={logout} onOpenCases={() => setView('test-cases')} onOpenAudits={() => setView('audits')} onOpenNonconformities={() => setView('nonconformities')} onOrganizationChange={selectOrganization} />
}

export default App
