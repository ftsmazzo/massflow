import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import './Layout.css'

export default function Layout() {
  const { user, tenant, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="app-layout">
      <header className="app-header">
        <div className="app-header-inner">
          <NavLink to="/app" className="app-logo">MassFlow</NavLink>
          <nav className="app-nav">
            <NavLink to="/app" end>Início</NavLink>
            <NavLink to="/app/contacts">Contatos</NavLink>
            <NavLink to="/app/lists">Listas</NavLink>
            <NavLink to="/app/tags">Tags</NavLink>
            <NavLink to="/app/instances">Instâncias</NavLink>
            <NavLink to="/app/shielding">Blindagem</NavLink>
          </nav>
          <div className="app-user">
            <span className="app-tenant">{tenant?.name ?? '—'}</span>
            <span className="app-email">{user?.email ?? ''}</span>
            <button type="button" onClick={handleLogout} className="app-logout">
              Sair
            </button>
          </div>
        </div>
      </header>
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  )
}
