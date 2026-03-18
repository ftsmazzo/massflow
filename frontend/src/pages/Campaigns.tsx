import { useState, useEffect } from 'react'
import { campaignsApi, listsApi, type CampaignItem, type ListItem } from '../services/api'
import { getApiErrorMessage } from '../services/api'
import './Campaigns.css'

const STATUS_LABEL: Record<string, string> = {
  draft: 'Rascunho',
  scheduled: 'Agendada',
  running: 'Em andamento',
  completed: 'Concluída',
  cancelled: 'Cancelada',
}

const TYPE_LABEL: Record<string, string> = {
  immediate: 'Disparo imediato',
  scheduled: 'Agendada',
}

export default function Campaigns() {
  const [campaigns, setCampaigns] = useState<CampaignItem[]>([])
  const [lists, setLists] = useState<ListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showForm, setShowForm] = useState(false)

  function load() {
    setLoading(true)
    campaignsApi.list()
      .then((r) => setCampaigns(r.data))
      .catch(() => setError('Falha ao carregar campanhas.'))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
    listsApi.list().then((r) => setLists(r.data)).catch(() => {})
  }, [])

  function handleDelete(c: CampaignItem) {
    if (c.status !== 'draft' && c.status !== 'cancelled') return
    if (!confirm(`Excluir a campanha "${c.name}"?`)) return
    campaignsApi.delete(c.id)
      .then(load)
      .catch((err) => setError(getApiErrorMessage(err)))
  }

  if (error && campaigns.length === 0) {
    return (
      <div className="campaigns-page">
        <div className="campaigns-error">{error}</div>
      </div>
    )
  }

  return (
    <div className="campaigns-page">
      <header className="campaigns-header">
        <div>
          <h1>Campanhas</h1>
          <p className="campaigns-subtitle">Crie e gerencie disparos em massa (lista, conteúdo, blindagem)</p>
        </div>
        <button type="button" className="campaigns-btn primary" onClick={() => setShowForm(true)}>
          Nova campanha
        </button>
      </header>

      {error && <div className="campaigns-error-banner">{error}</div>}

      {loading ? (
        <p className="campaigns-loading">Carregando…</p>
      ) : campaigns.length === 0 ? (
        <div className="campaigns-empty">
          <p>Nenhuma campanha ainda.</p>
          <p>Crie uma lista em Listas, depois defina nome, público e conteúdo aqui.</p>
          <button type="button" className="campaigns-btn primary" onClick={() => setShowForm(true)}>
            Nova campanha
          </button>
        </div>
      ) : (
        <div className="campaigns-grid">
          {campaigns.map((c) => (
            <article key={c.id} className="campaigns-card">
              <div className="campaigns-card-main">
                <h2 className="campaigns-card-name">{c.name}</h2>
                <p className="campaigns-card-meta">
                  <span className={`campaigns-status campaigns-status--${c.status}`}>
                    {STATUS_LABEL[c.status] ?? c.status}
                  </span>
                  {' · '}
                  {TYPE_LABEL[c.type] ?? c.type}
                </p>
                <p className="campaigns-card-list">
                  Lista ID: {c.list_id}
                  {lists.find((l) => l.id === c.list_id) && ` (${lists.find((l) => l.id === c.list_id)!.name})`}
                </p>
              </div>
              <div className="campaigns-card-actions">
                {(c.status === 'draft' || c.status === 'cancelled') && (
                  <button
                    type="button"
                    className="campaigns-btn-link danger"
                    onClick={() => handleDelete(c)}
                  >
                    Excluir
                  </button>
                )}
              </div>
            </article>
          ))}
        </div>
      )}

      {showForm && (
        <CampaignForm
          lists={lists}
          onClose={() => setShowForm(false)}
          onSuccess={() => { setShowForm(false); load() }}
        />
      )}
    </div>
  )
}

function CampaignForm({
  lists,
  onClose,
  onSuccess,
}: {
  lists: ListItem[]
  onClose: () => void
  onSuccess: () => void
}) {
  const [name, setName] = useState('')
  const [listId, setListId] = useState<number | ''>('')
  const [type, setType] = useState<'immediate' | 'scheduled'>('immediate')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!listId) {
      setError('Selecione uma lista.')
      return
    }
    setError('')
    setLoading(true)
    campaignsApi.create({
      name: name.trim(),
      type,
      list_id: Number(listId),
      content: { type: 'text', text: '' },
    })
      .then(onSuccess)
      .catch((err) => setError(getApiErrorMessage(err)))
      .finally(() => setLoading(false))
  }

  return (
    <div className="campaigns-modal" role="dialog" aria-modal="true">
      <div className="campaigns-modal-backdrop" onClick={onClose} />
      <div className="campaigns-modal-content">
        <h2>Nova campanha</h2>
        <p className="campaigns-form-hint">Conteúdo e agendamento podem ser editados depois no rascunho.</p>
        <form onSubmit={handleSubmit}>
          {error && <div className="campaigns-form-error">{error}</div>}
          <label>
            Nome da campanha *
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              placeholder="Ex: Black Friday 2025"
            />
          </label>
          <label>
            Lista (público-alvo) *
            <select
              value={listId === '' ? '' : listId}
              onChange={(e) => setListId(e.target.value === '' ? '' : Number(e.target.value))}
              required
            >
              <option value="">Selecione uma lista</option>
              {lists.map((l) => (
                <option key={l.id} value={l.id}>{l.name} ({l.contact_count} contatos)</option>
              ))}
            </select>
          </label>
          <label>
            Tipo
            <select value={type} onChange={(e) => setType(e.target.value as 'immediate' | 'scheduled')}>
              <option value="immediate">Disparo imediato</option>
              <option value="scheduled">Agendada</option>
            </select>
          </label>
          <div className="campaigns-form-actions">
            <button type="button" onClick={onClose}>Cancelar</button>
            <button type="submit" disabled={loading}>{loading ? 'Criando…' : 'Criar rascunho'}</button>
          </div>
        </form>
      </div>
    </div>
  )
}
