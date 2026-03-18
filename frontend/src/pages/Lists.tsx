import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { listsApi, contactsApi, tagsApi, type ListItem, type Contact, type TagItem } from '../services/api'
import { getApiErrorMessage } from '../services/api'
import ImportCsvModal from '../components/ImportCsvModal'
import './Lists.css'

export default function Lists() {
  const [lists, setLists] = useState<ListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [editingList, setEditingList] = useState<ListItem | null>(null)

  function load() {
    setLoading(true)
    listsApi.list()
      .then((r) => setLists(r.data))
      .catch(() => setError('Falha ao carregar listas.'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  function handleCreate() {
    setEditingList(null)
    setShowForm(true)
  }

  function handleEdit(list: ListItem) {
    setEditingList(list)
    setShowForm(true)
  }

  function handleFormSuccess() {
    setShowForm(false)
    setEditingList(null)
    load()
  }

  function handleDelete(list: ListItem) {
    if (!confirm(`Remover a lista "${list.name}"? Os contatos não serão apagados.`)) return
    listsApi.delete(list.id)
      .then(load)
      .catch((err) => setError(getApiErrorMessage(err)))
  }

  if (error && lists.length === 0) {
    return (
      <div className="lists-page">
        <div className="lists-error">{error}</div>
      </div>
    )
  }

  return (
    <div className="lists-page">
      <header className="lists-header">
        <div>
          <h1>Listas</h1>
          <p className="lists-subtitle">Agrupe contatos para campanhas</p>
        </div>
        <button type="button" className="lists-btn primary" onClick={handleCreate}>
          Nova lista
        </button>
      </header>

      {error && <div className="lists-error-banner">{error}</div>}

      {loading ? (
        <p className="lists-loading">Carregando…</p>
      ) : lists.length === 0 ? (
        <div className="lists-empty">
          <p>Nenhuma lista ainda.</p>
          <button type="button" className="lists-btn primary" onClick={handleCreate}>
            Nova lista
          </button>
        </div>
      ) : (
        <div className="lists-grid">
          {lists.map((list) => (
            <article key={list.id} className="lists-card">
              <div className="lists-card-main">
                <h2 className="lists-card-name">{list.name}</h2>
                <p className="lists-card-count">{list.contact_count} contato(s)</p>
              </div>
              <div className="lists-card-actions">
                <button type="button" className="lists-btn-link" onClick={() => handleEdit(list)}>
                  Editar
                </button>
                <Link to={`/app/lists/${list.id}`} className="lists-btn-link">Ver contatos</Link>
                <button type="button" className="lists-btn-link danger" onClick={() => handleDelete(list)}>
                  Excluir
                </button>
              </div>
            </article>
          ))}
        </div>
      )}

      {showForm && (
        <ListForm
          list={editingList}
          onClose={() => { setShowForm(false); setEditingList(null) }}
          onSuccess={handleFormSuccess}
        />
      )}
    </div>
  )
}

function ListDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [list, setList] = useState<ListItem | null>(null)
  const [contacts, setContacts] = useState<Contact[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showAdd, setShowAdd] = useState(false)
  const [showImport, setShowImport] = useState(false)
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())

  const listId = id ? parseInt(id, 10) : 0

  useEffect(() => {
    if (!listId) return
    listsApi.get(listId)
      .then((r) => setList(r.data))
      .catch(() => setError('Lista não encontrada.'))
    listsApi.getContacts(listId)
      .then((r) => setContacts(r.data))
      .catch(() => setError('Falha ao carregar contatos.'))
      .finally(() => setLoading(false))
  }, [listId])

  function handleAddSuccess() {
    setShowAdd(false)
    listsApi.get(listId).then((r) => setList(r.data))
    listsApi.getContacts(listId).then((r) => setContacts(r.data))
  }

  function handleImportSuccess() {
    setShowImport(false)
    listsApi.get(listId).then((r) => setList(r.data))
    listsApi.getContacts(listId).then((r) => setContacts(r.data))
  }

  function toggleSelect(id: number) {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  function handleRemoveSelected() {
    if (selectedIds.size === 0) return
    if (!confirm(`Remover ${selectedIds.size} contato(s) da lista?`)) return
    listsApi.removeContacts(listId, Array.from(selectedIds))
      .then(() => {
        setSelectedIds(new Set())
        listsApi.get(listId).then((r) => setList(r.data))
        listsApi.getContacts(listId).then((r) => setContacts(r.data))
      })
      .catch((err) => setError(getApiErrorMessage(err)))
  }

  if (!listId || (!loading && !list)) {
    return (
      <div className="lists-page">
        <p className="lists-error">Lista não encontrada.</p>
        <button type="button" onClick={() => navigate('/app/lists')}>Voltar</button>
      </div>
    )
  }

  return (
    <div className="lists-page lists-detail">
      <header className="lists-header">
        <div>
          <button type="button" className="lists-back" onClick={() => navigate('/app/lists')}>← Voltar</button>
          <h1>{list?.name ?? '…'}</h1>
          <p className="lists-subtitle">{list?.contact_count ?? 0} contato(s)</p>
        </div>
        <div className="lists-header-actions">
          {selectedIds.size > 0 && (
            <button type="button" className="lists-btn danger" onClick={handleRemoveSelected}>
              Remover {selectedIds.size} da lista
            </button>
          )}
          <button type="button" className="lists-btn secondary" onClick={() => setShowImport(true)}>
            Importar CSV
          </button>
          <button type="button" className="lists-btn primary" onClick={() => setShowAdd(true)}>
            Adicionar contatos
          </button>
        </div>
      </header>

      {error && <div className="lists-error-banner">{error}</div>}

      {loading ? (
        <p className="lists-loading">Carregando…</p>
      ) : contacts.length === 0 ? (
        <div className="lists-empty">
          <p>Nenhum contato nesta lista.</p>
          <p>Importe um CSV ou adicione contatos já existentes no sistema.</p>
          <div className="lists-empty-actions">
            <button type="button" className="lists-btn secondary" onClick={() => setShowImport(true)}>
              Importar CSV
            </button>
            <button type="button" className="lists-btn primary" onClick={() => setShowAdd(true)}>
              Adicionar contatos
            </button>
          </div>
        </div>
      ) : (
        <div className="lists-table-wrap">
          <table className="lists-table">
            <thead>
              <tr>
                <th><input type="checkbox" onChange={(e) => setSelectedIds(e.target.checked ? new Set(contacts.map((c) => c.id)) : new Set())} checked={selectedIds.size === contacts.length && contacts.length > 0} /></th>
                <th>Telefone</th>
                <th>Nome</th>
                <th>Email</th>
                <th>Tags</th>
              </tr>
            </thead>
            <tbody>
              {contacts.map((c) => (
                <tr key={c.id}>
                  <td><input type="checkbox" checked={selectedIds.has(c.id)} onChange={() => toggleSelect(c.id)} /></td>
                  <td>{c.phone}</td>
                  <td>{c.name || '—'}</td>
                  <td>{c.email || '—'}</td>
                  <td>{c.tags.length ? c.tags.join(', ') : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showAdd && (
        <AddContactsModal
          listId={listId}
          currentIds={new Set(contacts.map((c) => c.id))}
          onClose={() => setShowAdd(false)}
          onSuccess={handleAddSuccess}
        />
      )}
      {showImport && list && (
        <ImportCsvModal
          lists={[list]}
          defaultListId={listId}
          onClose={() => setShowImport(false)}
          onSuccess={handleImportSuccess}
        />
      )}
    </div>
  )
}

function ListForm({
  list,
  onClose,
  onSuccess,
}: {
  list: ListItem | null
  onClose: () => void
  onSuccess: () => void
}) {
  const [name, setName] = useState(list?.name ?? '')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    if (list) {
      listsApi.update(list.id, { name: name.trim() })
        .then(onSuccess)
        .catch((err) => setError(getApiErrorMessage(err)))
        .finally(() => setLoading(false))
    } else {
      listsApi.create({ name: name.trim() })
        .then(onSuccess)
        .catch((err) => setError(getApiErrorMessage(err)))
        .finally(() => setLoading(false))
    }
  }

  return (
    <div className="lists-modal" role="dialog" aria-modal="true">
      <div className="lists-modal-backdrop" onClick={onClose} />
      <div className="lists-modal-content">
        <h2>{list ? 'Editar lista' : 'Nova lista'}</h2>
        <form onSubmit={handleSubmit}>
          {error && <div className="lists-form-error">{error}</div>}
          <label>
            Nome da lista
            <input value={name} onChange={(e) => setName(e.target.value)} required placeholder="Ex: Base Black Friday" />
          </label>
          <div className="lists-form-actions">
            <button type="button" onClick={onClose}>Cancelar</button>
            <button type="submit" disabled={loading}>{loading ? 'Salvando…' : 'Salvar'}</button>
          </div>
        </form>
      </div>
    </div>
  )
}

function AddContactsModal({
  listId,
  currentIds,
  onClose,
  onSuccess,
}: {
  listId: number
  currentIds: Set<number>
  onClose: () => void
  onSuccess: () => void
}) {
  const [contacts, setContacts] = useState<Contact[]>([])
  const [tags, setTags] = useState<TagItem[]>([])
  const [filterTag, setFilterTag] = useState('')
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    tagsApi.list().then((r) => setTags(r.data)).catch(() => {})
  }, [])

  useEffect(() => {
    setLoading(true)
    const params: { limit: number; tags?: string } = { limit: 500 }
    if (filterTag.trim()) params.tags = filterTag.trim()
    contactsApi.list(params)
      .then((r) => setContacts(r.data.filter((c) => !currentIds.has(c.id))))
      .catch(() => setError('Falha ao carregar contatos.'))
      .finally(() => setLoading(false))
  }, [listId, filterTag])

  function toggle(id: number) {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  function handleAdd() {
    if (selectedIds.size === 0) return
    setSaving(true)
    listsApi.addContacts(listId, Array.from(selectedIds))
      .then(onSuccess)
      .catch((err) => setError(getApiErrorMessage(err)))
      .finally(() => setSaving(false))
  }

  return (
    <div className="lists-modal" role="dialog" aria-modal="true">
      <div className="lists-modal-backdrop" onClick={onClose} />
      <div className="lists-modal-content lists-modal-wide">
        <h2>Adicionar contatos à lista</h2>
        <div className="lists-add-filters">
          <label>
            Filtrar por tag
            <select
              value={filterTag}
              onChange={(e) => setFilterTag(e.target.value)}
              aria-label="Filtrar contatos por tag"
            >
              <option value="">Todas</option>
              {tags.map((t) => (
                <option key={t.id} value={t.name}>{t.name}</option>
              ))}
            </select>
          </label>
          {filterTag && (
            <span className="lists-add-filter-hint">
              {contacts.length} contato(s) com a tag &quot;{filterTag}&quot;
            </span>
          )}
        </div>
        {error && <div className="lists-form-error">{error}</div>}
        {loading ? (
          <p>Carregando…</p>
        ) : contacts.length === 0 ? (
          <p>
            {filterTag
              ? `Nenhum contato com a tag "${filterTag}" (ou todos já estão nesta lista).`
              : 'Nenhum contato disponível (todos já estão nesta lista).'}
          </p>
        ) : (
          <>
            <div className="lists-add-list">
              {contacts.slice(0, 100).map((c) => (
                <label key={c.id} className="lists-add-row">
                  <input type="checkbox" checked={selectedIds.has(c.id)} onChange={() => toggle(c.id)} />
                  <span>{c.phone}</span>
                  <span>{c.name || '—'}</span>
                  {c.tags.length > 0 && (
                    <span className="lists-add-row-tags">{c.tags.join(', ')}</span>
                  )}
                </label>
              ))}
            </div>
            {contacts.length > 100 && (
              <p className="lists-add-hint">
                Exibindo os 100 primeiros de {contacts.length} contatos{filterTag ? ` com a tag "${filterTag}"` : ''}. Adicione em lotes.
              </p>
            )}
          </>
        )}
        <div className="lists-form-actions">
          <button type="button" onClick={onClose}>Fechar</button>
          <button type="button" className="primary" onClick={handleAdd} disabled={selectedIds.size === 0 || saving}>
            {saving ? 'Adicionando…' : `Adicionar ${selectedIds.size}`}
          </button>
        </div>
      </div>
    </div>
  )
}

export { ListDetail }
