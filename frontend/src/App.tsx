import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import './App.css'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<div className="page">Login (em breve)</div>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

function Home() {
  return (
    <div className="page">
      <h1>MassFlow</h1>
      <p>Sistema de disparos em massa via Evolution API</p>
      <p><small>Versão 0.1.0 - Estrutura base</small></p>
    </div>
  )
}

export default App
