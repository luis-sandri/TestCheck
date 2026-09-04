import { useEffect, useState } from 'react'
import './App.css'

type ApiStatus = 'checking' | 'online' | 'offline'

const testCases = [
  {
    code: 'TC-014',
    title: 'Login com senha incorreta',
    author: 'André Murilo',
    adherence: 67,
    status: 'Não conforme',
    tone: 'danger',
  },
  {
    code: 'TC-013',
    title: 'Recuperação de acesso',
    author: 'Marcelo Bellon',
    adherence: 100,
    status: 'Conforme',
    tone: 'success',
  },
  {
    code: 'TC-012',
    title: 'Cadastro com e-mail existente',
    author: 'Matheus Pamplona',
    adherence: 83,
    status: 'Em correção',
    tone: 'warning',
  },
]

function App() {
  const [apiStatus, setApiStatus] = useState<ApiStatus>('checking')
  const [notice, setNotice] = useState('')

  useEffect(() => {
    fetch('/api/health')
      .then((response) => {
        if (!response.ok) throw new Error('API indisponível')
        setApiStatus('online')
      })
      .catch(() => setApiStatus('offline'))
  }, [])

  const startAudit = () => {
    setNotice('A criação da auditoria será implementada na próxima tarefa.')
    window.setTimeout(() => setNotice(''), 3600)
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">✓</span>
          <div>
            <strong>TestCheck</strong>
            <span>Qualidade de Software</span>
          </div>
        </div>

        <nav aria-label="Navegação principal">
          <a className="nav-item active" href="#dashboard">
            <span aria-hidden="true">◫</span> Visão geral
          </a>
          <a className="nav-item" href="#test-cases">
            <span aria-hidden="true">≡</span> Casos de teste
          </a>
          <a className="nav-item" href="#audits">
            <span aria-hidden="true">✓</span> Auditorias
          </a>
          <a className="nav-item" href="#nonconformities">
            <span aria-hidden="true">!</span> Não conformidades
          </a>
        </nav>

        <div className="sidebar-footer">
          <div className="avatar">LG</div>
          <div>
            <strong>Luís Gustavo</strong>
            <span>Vistoriador</span>
          </div>
        </div>
      </aside>

      <main id="dashboard">
        <header className="topbar">
          <div>
            <p className="eyebrow">PROJETO CHECKOUT</p>
            <h1>Visão geral da qualidade</h1>
            <p className="subtitle">
              Acompanhe auditorias, aderência e correções dos casos de teste.
            </p>
          </div>
          <button className="primary-button" type="button" onClick={startAudit}>
            <span aria-hidden="true">＋</span> Nova auditoria
          </button>
        </header>

        <section className="metrics" aria-label="Indicadores">
          <article className="metric-card">
            <span className="metric-icon blue">≡</span>
            <div><strong>12</strong><span>Casos de teste</span></div>
            <small>3 adicionados nesta semana</small>
          </article>
          <article className="metric-card">
            <span className="metric-icon violet">✓</span>
            <div><strong>4</strong><span>Auditorias pendentes</span></div>
            <small>2 com prazo próximo</small>
          </article>
          <article className="metric-card">
            <span className="metric-icon red">!</span>
            <div><strong>3</strong><span>NCs abertas</span></div>
            <small>1 aguardando validação</small>
          </article>
          <article className="metric-card">
            <span className="metric-icon green">↗</span>
            <div><strong>86%</strong><span>Aderência média</span></div>
            <small className="positive">+8% desde a última rodada</small>
          </article>
        </section>

        <section className="content-grid">
          <article className="panel cases-panel" id="test-cases">
            <div className="panel-header">
              <div>
                <h2>Casos auditados recentemente</h2>
                <p>Últimos artefatos avaliados pela equipe.</p>
              </div>
              <button className="text-button" type="button">Ver todos →</button>
            </div>

            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Caso de teste</th>
                    <th>Responsável</th>
                    <th>Aderência</th>
                    <th>Estado</th>
                  </tr>
                </thead>
                <tbody>
                  {testCases.map((testCase) => (
                    <tr key={testCase.code}>
                      <td>
                        <span className="case-code">{testCase.code}</span>
                        <strong>{testCase.title}</strong>
                      </td>
                      <td>{testCase.author}</td>
                      <td>
                        <div className="progress-row">
                          <span className="progress-track">
                            <span style={{ width: `${testCase.adherence}%` }} />
                          </span>
                          <strong>{testCase.adherence}%</strong>
                        </div>
                      </td>
                      <td><span className={`status ${testCase.tone}`}>{testCase.status}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </article>

          <aside className="panel next-panel">
            <div className="panel-header">
              <div>
                <h2>Próximas ações</h2>
                <p>Itens que precisam de atenção.</p>
              </div>
            </div>
            <ul className="action-list">
              <li>
                <span className="action-dot red" />
                <div><strong>NC-002 vence amanhã</strong><span>Dados de teste não informados</span></div>
                <b>1d</b>
              </li>
              <li>
                <span className="action-dot violet" />
                <div><strong>Correção para validar</strong><span>TC-012 · Cadastro duplicado</span></div>
                <b>Hoje</b>
              </li>
              <li>
                <span className="action-dot blue" />
                <div><strong>4 casos sem auditoria</strong><span>Projeto Portal Acadêmico</span></div>
                <b>4</b>
              </li>
            </ul>
            <div className={`api-state ${apiStatus}`}>
              <span />
              {apiStatus === 'checking' && 'Verificando conexão com a API…'}
              {apiStatus === 'online' && 'API conectada e operacional'}
              {apiStatus === 'offline' && 'Interface pronta; inicie a API local'}
            </div>
          </aside>
        </section>

        {notice && <div className="toast" role="status">{notice}</div>}
      </main>
    </div>
  )
}

export default App

