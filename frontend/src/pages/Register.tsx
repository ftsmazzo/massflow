import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { getApiErrorMessage, apiBaseURL } from '../services/api'
import './Auth.css'

export default function Register() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [tenantName, setTenantName] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { register } = useAuth()
  const navigate = useNavigate()

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await register({ email, password, name: name || undefined, tenant_name: tenantName })
      navigate('/app', { replace: true })
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, 'Falha ao cadastrar.'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h1>MassFlow</h1>
        <p className="auth-subtitle">Criar conta</p>
        <form onSubmit={handleSubmit} className="auth-form">
          {!apiBaseURL && import.meta.env.PROD && (
            <div className="auth-error">
              URL da API não configurada. No Easypanel, no serviço do frontend, defina <strong>Build Arg</strong> <code>VITE_API_URL</code> = URL do backend (ex: https://...-backend....easypanel.host) e refaça o build.
            </div>
          )}
          {error && <div className="auth-error">{error}</div>}
          <label>
            Nome da organização *
            <input
              type="text"
              value={tenantName}
              onChange={(e) => setTenantName(e.target.value)}
              required
              placeholder="Minha Empresa"
            />
          </label>
          <label>
            Seu nome
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="João Silva"
            />
          </label>
          <label>
            E-mail *
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
            />
          </label>
          <label>
            Senha *
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="new-password"
            />
          </label>
          <button type="submit" disabled={loading}>
            {loading ? 'Cadastrando…' : 'Cadastrar'}
          </button>
        </form>
        <p className="auth-footer">
          Já tem conta? <Link to="/login">Entrar</Link>
        </p>
      </div>
    </div>
  )
}
