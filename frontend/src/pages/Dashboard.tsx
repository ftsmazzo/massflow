import { useAuth } from '../contexts/AuthContext'
import { Link } from 'react-router-dom'
import './Dashboard.css'

export default function Dashboard() {
  const { user, tenant } = useAuth()

  return (
    <div className="dashboard">
      <h1>Olá, {user?.name || user?.email}</h1>
      <p className="dashboard-tenant">{tenant?.name} · Plano {tenant?.plan_type}</p>
      <div className="dashboard-cards">
        <Link to="/app/instances" className="dashboard-card">
          <h2>Instâncias</h2>
          <p>Conecte suas instâncias Evolution API (WhatsApp)</p>
        </Link>
        <Link to="/app/contacts" className="dashboard-card">
          <h2>Contatos</h2>
          <p>Base de contatos, listas e tags</p>
        </Link>
        <Link to="/app/lists" className="dashboard-card">
          <h2>Listas</h2>
          <p>Agrupe contatos para campanhas</p>
        </Link>
        <Link to="/app/tags" className="dashboard-card">
          <h2>Tags</h2>
          <p>Funis e segmentação</p>
        </Link>
        <Link to="/app/shielding" className="dashboard-card">
          <h2>Blindagem</h2>
          <p>Configurações globais para evitar bloqueios</p>
        </Link>
        <Link to="/app/campaigns" className="dashboard-card">
          <h2>Campanhas</h2>
          <p>Crie e gerencie disparos em massa</p>
        </Link>
      </div>
    </div>
  )
}
