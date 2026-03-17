import { useState, useEffect } from 'react'
import { tagsApi, contactsApi, type TagItem, type Contact } from '../services/api'
import { getApiErrorMessage } from '../services/api'
import './Tags.css'

export default function Tags() {
  const [tags, setTags] = useState<TagItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [showApply, setShowApply] = useState<TagItem | null>(null)

  function load() {
    setLoading(true)
    tagsApi.list()
      .then((r) => setTags(r.data))
      .catch(() => setError('Falha ao carregar tags.'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  function handleCreate() {
    setShowForm(true)
  }

  function handleFormSuccess() {
    setShowForm(false)
    load()
  }

  function handleDelete(tag: TagItem) {
    if (!confirm(`Excluir a tag "${tag.name}"?`)) return
    tagsApi.delete(tag.id)
      .then(load)
      .catch((err) => setError(getApiErrorMessage(err)))
  }

  return (
    <div className="tags-page">
      <header className="tags-header">
        <div>
          <h1>Tags</h1>
          <p className="tags-subtitle">Para funis e segmentação em campanhas</p>
        </div>
        <button type="button" className="tags-btn primary" onClick={handleCreate}>
          Nova tag
        </button>
      </header>

      {error && <div className="tags-error">{error}</div>}

      {loading ? (
        <p className="tags-loading">Carregando…</p>
      ) : tags.length === 0 ? (
        <div className="tags-empty">
          <p>Nenhuma tag ainda.</p>
          <button type="button" className="tags-btn primary" onClick={handleCreate}>
            Nova tag
          </button>
        </div>
      ) : (
        <ul className="tags-list">
          {tags.map((tag) => (
            <li key={tag.id} className="tags-item">
              <span className="tags-item-name">{tag.name}</span>
              <div className="tags-item-actions">
                <button type="button" className="tags-btn-link" onClick={() => setShowApply(tag)}>
                  Aplicar a contatos
                </button>
                <button type="button" className="tags-btn-link danger" onClick={() => handleDelete(tag)}>
                  Excluir
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

      {showForm && (
        <TagForm
          onClose={() => setShowForm(false)}
          onSuccess={handleFormSuccess}
        />
      )}

      {showApply && (
        <ApplyTagModal
          tag={showApply}
          onClose={() => setShowApply(null)}
          onSuccess={() => { setShowApply(null); load() }}
        />
      )}
    </div>
  )
}

function TagForm({
  onClose,
  onSuccess,
}: {
  onClose: () => void
  onSuccess: () => void
}) {
  const [name, setName] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    tagsApi.create({ name: name.trim() })
      .then(onSuccess)
      .catch((err) => setError(getApiErrorMessage(err)))
      .finally(() => setLoading(false))
  }

  return (
    <div className="tags-modal" role="dialog" aria-modal="true">
      <div className="tags-modal-backdrop" onClick={onClose} />
      <div className="tags-modal-content">
        <h2>Nova tag</h2>
        <form onSubmit={handleSubmit}>
          {error && <div className="tags-form-error">{error}</div>}
          <label>
            Nome da tag
            <input value={name} onChange={(e) => setName(e.target.value)} required placeholder="ex: quente, interessado" />
          </label>
          <div className="tags-form-actions">
            <button type="button" onClick={onClose}>Cancelar</button>
            <button type="submit" disabled={loading}>{loading ? 'Criando…' : 'Criar'}</button>
          </div>
        </form>
      </div>
    </div>
  )
}

function ApplyTagModal({
  tag,
  onClose,
  onSuccess,
}: {
  tag: TagItem
  onClose: () => void
  onSuccess: () => void
}) {
  const [contacts, setContacts] = useState<Contact[]>([])
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    contactsApi.list({ limit: 500 })
      .then((r) => setContacts(r.data))
      .catch(() => setError('Falha ao carregar contatos.'))
      .finally(() => setLoading(false))
  }, [])

  function toggle(id: number) {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  function handleApply() {
    if (selectedIds.size === 0) return
    setSaving(true)
    tagsApi.apply(tag.id, Array.from(selectedIds))
      .then(onSuccess)
      .catch((err) => setError(getApiErrorMessage(err)))
      .finally(() => setSaving(false))
  }

  return (
    <div className="tags-modal" role="dialog" aria-modal="true">
      <div className="tags-modal-backdrop" onClick={onClose} />
      <div className="tags-modal-content tags-modal-wide">
        <h2>Aplicar tag &quot;{tag.name}&quot;</h2>
        {error && <div className="tags-form-error">{error}</div>}
        {loading ? (
          <p>Carregando contatos…</p>
        ) : (
          <div className="tags-apply-list">
            {contacts.slice(0, 150).map((c) => (
              <label key={c.id} className="tags-apply-row">
                <input type="checkbox" checked={selectedIds.has(c.id)} onChange={() => toggle(c.id)} />
                <span>{c.phone}</span>
                <span>{c.name || '—'}</span>
              </label>
            ))}
          </div>
        )}
        <div className="tags-form-actions">
          <button type="button" onClick={onClose}>Fechar</button>
          <button type="button" className="primary" onClick={handleApply} disabled={selectedIds.size === 0 || saving}>
            {saving ? 'Aplicando…' : `Aplicar a ${selectedIds.size} contato(s)`}
          </button>
        </div>
      </div>
    </div>
  )
}
