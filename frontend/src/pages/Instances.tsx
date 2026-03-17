import { useState, useEffect } from 'react'
import { instancesApi, type Instance } from '../services/api'
import './Instances.css'

const STATUS_CONNECTED = 'connected'

export default function Instances() {
  const [list, setList] = useState<Instance[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [connectResult, setConnectResult] = useState<{ id: number; pairing_code?: string; code?: string } | null>(null)

  useEffect(() => {
    let cancelled = false
    instancesApi.list()
      .then((r) => { if (!cancelled) setList(r.data) })
      .catch(() => { if (!cancelled) setError('Falha ao carregar instâncias.') })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [])

  function handleConnect(id: number) {
    setConnectResult(null)
    setError('')
    instancesApi.connect(id)
      .then((r) => setConnectResult({ id, ...r.data }))
      .catch((e) => setError(e.response?.data?.detail ?? 'Falha ao gerar QR/conexão.'))
  }

  function handleDisconnect(id: number) {
    setError('')
    instancesApi.disconnect(id)
      .then((updated) => setList((prev) => prev.map((i) => (i.id === id ? updated.data : i))))
      .catch((e) => setError(e.response?.data?.detail ?? 'Falha ao desconectar.'))
  }

  function handleRefresh(id: number) {
    setError('')
    instancesApi.refresh(id)
      .then((updated) => setList((prev) => prev.map((i) => (i.id === id ? updated.data : i))))
      .catch((e) => setError(e.response?.data?.detail ?? 'Falha ao atualizar status.'))
  }

  if (loading) return <div className="instances-loading">Carregando instâncias…</div>
  if (error && list.length === 0) return <div className="instances-error">{error}</div>

  return (
    <div className="instances-page">
      <header className="instances-header">
        <div>
          <h1>Instâncias WhatsApp</h1>
          <p className="instances-subtitle">Gerencie e configure suas instâncias</p>
        </div>
        <button type="button" className="instances-btn-primary" onClick={() => setShowForm(true)}>
          Nova instância
        </button>
      </header>

      {error && (
        <div className="instances-error-banner" role="alert">
          {error}
        </div>
      )}

      {connectResult && (
        <div className="instances-connect-box">
          <h3>Conectar ao WhatsApp</h3>
          {connectResult.pairing_code && (
            <p><strong>Pairing code:</strong> <code>{connectResult.pairing_code}</code></p>
          )}
          {connectResult.code && (
            <p className="instances-qr-hint">Use o código acima no WhatsApp ou escaneie o QR na Evolution API.</p>
          )}
          <button type="button" className="instances-btn-secondary" onClick={() => setConnectResult(null)}>Fechar</button>
        </div>
      )}

      {showForm && (
        <InstanceForm
          onClose={() => setShowForm(false)}
          onCreated={(inst) => { setList((prev) => [...prev, inst]); setShowForm(false) }}
        />
      )}

      {list.length === 0 ? (
        <div className="instances-empty">
          <p>Nenhuma instância ainda.</p>
          <p>Adicione uma instância conectada à sua Evolution API.</p>
          <button type="button" className="instances-btn-primary" onClick={() => setShowForm(true)}>
            Nova instância
          </button>
        </div>
      ) : (
        <div className="instances-grid">
          {list.map((inst) => (
            <article key={inst.id} className="instances-card">
              <div className="instances-card-head">
                <div>
                  <h2 className="instances-card-title">{inst.display_name || inst.name}</h2>
                  <p className="instances-card-subtitle">{inst.name}</p>
                </div>
                <span className={`instances-status ${inst.status === STATUS_CONNECTED ? 'instances-status--connected' : ''}`}>
                  <span className="instances-status-dot" aria-hidden />
                  {inst.status === STATUS_CONNECTED ? 'Conectado' : inst.status || '—'}
                </span>
              </div>
              <div className="instances-card-phone">
                <span className="instances-card-label">Telefone</span>
                <span className="instances-card-phone-value">
                  {inst.phone_number || '—'}
                </span>
              </div>
              <div className="instances-card-actions">
                <button
                  type="button"
                  className="instances-btn-refresh"
                  onClick={() => handleRefresh(inst.id)}
                  title="Atualizar status (consultar Evolution API)"
                  aria-label="Atualizar"
                >
                  ↻
                </button>
                {inst.status === STATUS_CONNECTED ? (
                  <button
                    type="button"
                    className="instances-btn-disconnect"
                    onClick={() => handleDisconnect(inst.id)}
                    title="Desconectar do WhatsApp"
                  >
                    Desconectar
                  </button>
                ) : (
                  <button
                    type="button"
                    className="instances-btn-qr"
                    onClick={() => handleConnect(inst.id)}
                    title="Conectar via QR Code"
                  >
                    QR Code
                  </button>
                )}
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  )
}

function InstanceForm({
  onClose,
  onCreated,
}: {
  onClose: () => void
  onCreated: (inst: Instance) => void
}) {
  const [name, setName] = useState('')
  const [apiUrl, setApiUrl] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const { data } = await instancesApi.create({
        name: name.trim(),
        api_url: apiUrl.trim(),
        api_key: apiKey.trim() || undefined,
        display_name: displayName.trim() || undefined,
      })
      onCreated(data)
    } catch (err: unknown) {
      const msg = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : 'Falha ao criar.'
      setError(Array.isArray(msg) ? msg.join(' ') : String(msg ?? 'Falha ao criar.'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="instances-modal" role="dialog" aria-modal="true">
      <div className="instances-modal-backdrop" onClick={onClose} />
      <div className="instances-modal-content">
        <h2>Nova instância</h2>
        <form onSubmit={handleSubmit}>
          {error && <div className="instances-form-error">{error}</div>}
          <label>
            Nome da instância (Evolution) *
            <input value={name} onChange={(e) => setName(e.target.value)} required placeholder="minha-instancia" />
          </label>
          <label>
            URL da Evolution API *
            <input value={apiUrl} onChange={(e) => setApiUrl(e.target.value)} required placeholder="https://sua-evolution.com" />
          </label>
          <label>
            API Key (opcional)
            <input type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)} placeholder="apikey" />
          </label>
          <label>
            Nome de exibição
            <input value={displayName} onChange={(e) => setDisplayName(e.target.value)} placeholder="Ex: MotoG - 01" />
          </label>
          <div className="instances-form-actions">
            <button type="button" onClick={onClose}>Cancelar</button>
            <button type="submit" disabled={loading}>{loading ? 'Criando…' : 'Criar'}</button>
          </div>
        </form>
      </div>
    </div>
  )
}
