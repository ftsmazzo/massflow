import { BrowserRouter, Routes, Route, Navigate, Link } from 'react-router-dom'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import ProtectedRoute from './components/ProtectedRoute'
import Layout from './components/Layout'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import Instances from './pages/Instances'
import './App.css'

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route
            path="/app"
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Dashboard />} />
            <Route path="instances" element={<Instances />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}

function Home() {
  const { token, loading } = useAuth()

  if (loading) {
    return (
      <div className="page">
        <p>Carregando…</p>
      </div>
    )
  }

  if (token) {
    return <Navigate to="/app" replace />
  }

  return (
    <div className="page home-page">
      <h1>MassFlow</h1>
      <p>Sistema de disparos em massa via Evolution API</p>
      <p><small>Captação de leads e campanhas · Multi-tenant</small></p>
      <div className="home-actions">
        <Link to="/login" className="home-btn primary">Entrar</Link>
        <Link to="/register" className="home-btn">Cadastrar</Link>
      </div>
    </div>
  )
}

export default App
