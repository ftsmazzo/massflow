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
        <Link to="/app/shielding" className="dashboard-card">
          <h2>Blindagem</h2>
          <p>Configurações globais para evitar bloqueios</p>
        </Link>
        <div className="dashboard-card disabled">
          <h2>Campanhas</h2>
          <p>Em breve</p>
        </div>
        <div className="dashboard-card disabled">
          <h2>Contatos</h2>
          <p>Em breve</p>
        </div>
      </div>
    </div>
  )
}
