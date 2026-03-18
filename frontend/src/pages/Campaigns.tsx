import { useState, useEffect } from 'react'
import { campaignsApi, listsApi, instancesApi, type CampaignItem, type ListItem, type Instance } from '../services/api'
import { getApiErrorMessage } from '../services/api'
import './Campaigns.css'

const CONTENT_TYPE_OPTIONS = [
  { value: 'text', label: 'Só texto' },
  { value: 'image', label: 'Imagem + legenda' },
  { value: 'video', label: 'Vídeo + legenda' },
  { value: 'audio', label: 'Áudio + texto' },
  { value: 'document', label: 'Documento + legenda' },
] as const

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
  const [editingCampaign, setEditingCampaign] = useState<CampaignItem | null>(null)
  const [instances, setInstances] = useState<Instance[]>([])
  const [startingId, setStartingId] = useState<number | null>(null)

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
    instancesApi.list().then((r) => setInstances(r.data)).catch(() => {})
  }, [])

  function handleDelete(c: CampaignItem) {
    if (c.status !== 'draft' && c.status !== 'cancelled') return
    if (!confirm(`Excluir a campanha "${c.name}"?`)) return
    campaignsApi.delete(c.id)
      .then(load)
      .catch((err) => setError(getApiErrorMessage(err)))
  }

  function handleStart(c: CampaignItem) {
    if (c.status !== 'draft') return
    setStartingId(c.id)
    setError('')
    campaignsApi.start(c.id)
      .then(() => {
        setStartingId(null)
        load()
      })
      .catch((err) => {
        setStartingId(null)
        setError(getApiErrorMessage(err))
      })
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
                {c.status === 'draft' && (
                  <>
                    <button
                      type="button"
                      className="campaigns-btn primary"
                      disabled={startingId === c.id}
                      onClick={() => handleStart(c)}
                    >
                      {startingId === c.id ? 'Disparando…' : 'Disparar agora'}
                    </button>
                    <button
                      type="button"
                      className="campaigns-btn-link"
                      onClick={() => setEditingCampaign(c)}
                    >
                      Editar
                    </button>
                  </>
                )}
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

      {showForm && !editingCampaign && (
        <CampaignForm
          lists={lists}
          onClose={() => setShowForm(false)}
          onSuccess={() => { setShowForm(false); load() }}
        />
      )}
      {editingCampaign && (
        <CampaignEditForm
          campaign={editingCampaign}
          lists={lists}
          instances={instances}
          onClose={() => setEditingCampaign(null)}
          onSuccess={() => { setEditingCampaign(null); load() }}
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

function CampaignEditForm({
  campaign,
  lists,
  instances,
  onClose,
  onSuccess,
}: {
  campaign: CampaignItem
  lists: ListItem[]
  instances: Instance[]
  onClose: () => void
  onSuccess: () => void
}) {
  const content = (campaign.content && typeof campaign.content === 'object') ? campaign.content as Record<string, unknown> : {}
  const [name, setName] = useState(campaign.name)
  const [listId, setListId] = useState(campaign.list_id)
  const [type, setType] = useState(campaign.type)
  const [scheduledAt, setScheduledAt] = useState(
    campaign.scheduled_at ? campaign.scheduled_at.slice(0, 16) : ''
  )
  const [contentType, setContentType] = useState((content.type as string) || 'text')
  const [contentText, setContentText] = useState((content.text as string) || '')
  const [contentMediaUrl, setContentMediaUrl] = useState((content.media_url as string) || '')
  const [contentCaption, setContentCaption] = useState((content.caption as string) || '')
  const [useGlobalShielding, setUseGlobalShielding] = useState(campaign.use_global_shielding)
  const [instanceIds, setInstanceIds] = useState<number[]>(campaign.instance_ids || [])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  function toggleInstance(id: number) {
    setInstanceIds((prev) => {
      const allIds = instances.map((i) => i.id)
      if (prev.length === 0) {
        return allIds.filter((x) => x !== id)
      }
      const next = prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
      return next.length === allIds.length ? [] : next
    })
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!listId) {
      setError('Selecione uma lista.')
      return
    }
    setError('')
    setLoading(true)
    const contentPayload: Record<string, string | undefined> = {
      type: contentType,
      text: contentType === 'text' ? contentText : contentCaption || contentText,
    }
    if (contentType !== 'text') {
      if (contentMediaUrl) contentPayload.media_url = contentMediaUrl
      if (contentCaption) contentPayload.caption = contentCaption
    }
    const payload = {
      name: name.trim(),
      type,
      list_id: listId,
      scheduled_at: scheduledAt || null,
      content: contentPayload,
      use_global_shielding: useGlobalShielding,
      instance_ids: instanceIds.length > 0 ? instanceIds : null,
    }
    campaignsApi.update(campaign.id, payload)
      .then(onSuccess)
      .catch((err) => setError(getApiErrorMessage(err)))
      .finally(() => setLoading(false))
  }

  return (
    <div className="campaigns-modal" role="dialog" aria-modal="true">
      <div className="campaigns-modal-backdrop" onClick={onClose} />
      <div className="campaigns-modal-content campaigns-edit-modal">
        <h2>Editar campanha</h2>
        <p className="campaigns-form-hint">Use {'{nome}'} no texto para personalizar. Spintax: {'{Olá|Oi}'} escolhe uma opção.</p>
        <form onSubmit={handleSubmit}>
          {error && <div className="campaigns-form-error">{error}</div>}
          <label>
            Nome *
            <input value={name} onChange={(e) => setName(e.target.value)} required />
          </label>
          <label>
            Lista (público-alvo) *
            <select
              value={listId}
              onChange={(e) => setListId(Number(e.target.value))}
              required
            >
              {!lists.find((l) => l.id === listId) && (
                <option value={listId}>Lista #{listId}</option>
              )}
              {lists.map((l) => (
                <option key={l.id} value={l.id}>{l.name} ({l.contact_count} contatos)</option>
              ))}
            </select>
          </label>
          <label>
            Tipo
            <select value={type} onChange={(e) => setType(e.target.value)}>
              <option value="immediate">Disparo imediato</option>
              <option value="scheduled">Agendada</option>
            </select>
          </label>
          {type === 'scheduled' && (
            <label>
              Data/hora do disparo
              <input
                type="datetime-local"
                value={scheduledAt}
                onChange={(e) => setScheduledAt(e.target.value)}
              />
            </label>
          )}
          <fieldset className="campaigns-fieldset">
            <legend>Conteúdo</legend>
            <label>
              Tipo de mídia
              <select value={contentType} onChange={(e) => setContentType(e.target.value)}>
                {CONTENT_TYPE_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </label>
            {contentType === 'text' && (
              <label>
                Texto da mensagem *
                <textarea
                  value={contentText}
                  onChange={(e) => setContentText(e.target.value)}
                  rows={4}
                  placeholder="Ex: Olá, {nome}! Tudo bem?"
                />
              </label>
            )}
            {contentType !== 'text' && (
              <>
                <label>
                  URL da mídia (imagem, vídeo, áudio ou documento)
                  <input
                    type="url"
                    value={contentMediaUrl}
                    onChange={(e) => setContentMediaUrl(e.target.value)}
                    placeholder="https://..."
                  />
                </label>
                <label>
                  {contentType === 'image' || contentType === 'video' || contentType === 'document' ? 'Legenda' : 'Texto (antes/depois do áudio)'}
                  <textarea
                    value={contentCaption}
                    onChange={(e) => setContentCaption(e.target.value)}
                    rows={3}
                    placeholder="Use {nome} para personalizar"
                  />
                </label>
              </>
            )}
          </fieldset>
          <label className="campaigns-check">
            <input
              type="checkbox"
              checked={useGlobalShielding}
              onChange={(e) => setUseGlobalShielding(e.target.checked)}
            />
            Usar configuração global de blindagem
          </label>
          {instances.length > 0 && (
            <fieldset className="campaigns-fieldset">
              <legend>Instâncias (vazio = todas)</legend>
              <div className="campaigns-instance-list">
                {instances.map((inst) => (
                  <label key={inst.id} className="campaigns-instance-row">
                    <input
                      type="checkbox"
                      checked={instanceIds.length === 0 || instanceIds.includes(inst.id)}
                      onChange={() => toggleInstance(inst.id)}
                    />
                    <span>{inst.display_name || inst.name}</span>
                    {inst.status && <span className="campaigns-instance-status">{inst.status}</span>}
                  </label>
                ))}
              </div>
              <p className="campaigns-form-hint">Todas selecionadas = usa todas as instâncias.</p>
            </fieldset>
          )}
          <div className="campaigns-form-actions">
            <button type="button" onClick={onClose}>Cancelar</button>
            <button type="submit" disabled={loading}>{loading ? 'Salvando…' : 'Salvar'}</button>
          </div>
        </form>
      </div>
    </div>
  )
}
