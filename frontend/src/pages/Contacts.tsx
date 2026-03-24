import { useState, useEffect } from 'react'
import { contactsApi, listsApi, tagsApi, type Contact, type ListItem, type TagItem } from '../services/api'
import { getApiErrorMessage } from '../services/api'
import './Contacts.css'

export default function Contacts() {
  const [contacts, setContacts] = useState<Contact[]>([])
  const [lists, setLists] = useState<ListItem[]>([])
  const [tags, setTags] = useState<TagItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [filterListId, setFilterListId] = useState<number | ''>('')
  const [filterTag, setFilterTag] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [editingContact, setEditingContact] = useState<Contact | null>(null)
  const [selectedIds, setSelectedIds] = useState<number[]>([])
  const [bulkDeleting, setBulkDeleting] = useState(false)

  function loadContacts() {
    const params: Record<string, unknown> = { limit: 200 }
    if (filterListId) params.list_id = filterListId
    if (filterTag.trim()) params.tags = filterTag.trim()
    setLoading(true)
    contactsApi.list(params)
      .then((r) => {
        setContacts(r.data)
        const valid = new Set(r.data.map((c) => c.id))
        setSelectedIds((prev) => prev.filter((id) => valid.has(id)))
      })
      .catch(() => setError('Falha ao carregar contatos.'))
      .finally(() => setLoading(false))
  }

  function loadListsAndTags() {
    listsApi.list().then((r) => setLists(r.data)).catch(() => {})
    tagsApi.list().then((r) => setTags(r.data)).catch(() => {})
  }

  useEffect(() => {
    loadContacts()
  }, [filterListId, filterTag])

  useEffect(() => {
    loadListsAndTags()
  }, [])

  function handleEdit(c: Contact) {
    setEditingContact(c)
    setShowForm(true)
  }

  function handleFormSuccess() {
    setShowForm(false)
    setEditingContact(null)
    loadContacts()
    loadListsAndTags()
  }

  function handleDelete(id: number) {
    if (!confirm('Remover este contato?')) return
    contactsApi.delete(id)
      .then(() => loadContacts())
      .catch((err) => setError(getApiErrorMessage(err)))
  }

  function toggleSelect(id: number, checked: boolean) {
    setSelectedIds((prev) => {
      if (checked) return prev.includes(id) ? prev : [...prev, id]
      return prev.filter((x) => x !== id)
    })
  }

  function toggleSelectAll(checked: boolean) {
    if (!checked) {
      setSelectedIds([])
      return
    }
    setSelectedIds(contacts.map((c) => c.id))
  }

  function handleBulkDelete() {
    if (selectedIds.length === 0) return
    if (!confirm(`Remover ${selectedIds.length} contato(s) selecionado(s)?`)) return
    setBulkDeleting(true)
    contactsApi.bulkDelete(selectedIds)
      .then((res) => {
        const fail = res.data.errors.length
        setSelectedIds([])
        loadContacts()
        if (fail > 0) setError(`Removidos: ${res.data.deleted}. Falhas: ${fail}.`)
      })
      .catch((err) => setError(getApiErrorMessage(err)))
      .finally(() => setBulkDeleting(false))
  }

  if (error && contacts.length === 0) {
    return (
      <div className="contacts-page">
        <div className="contacts-error">{error}</div>
      </div>
    )
  }

  return (
    <div className="contacts-page">
      <header className="contacts-header">
        <div>
          <h1>Contatos</h1>
          <p className="contacts-subtitle">Visualize, filtre e gerencie contatos. Inclusão de contatos em Listas (Importar CSV ou adicionar à lista).</p>
        </div>
      </header>

      <div className="contacts-volume">
        <span className="contacts-volume-total">Exibindo {contacts.length} contato(s)</span>
        {(filterListId || filterTag) && (
          <span className="contacts-volume-filter">com os filtros aplicados</span>
        )}
      </div>

      <div className="contacts-bulk-bar">
        <span>{selectedIds.length} selecionado(s)</span>
        <button
          type="button"
          className="contacts-btn secondary"
          disabled={selectedIds.length === 0 || bulkDeleting}
          onClick={handleBulkDelete}
        >
          {bulkDeleting ? 'Removendo…' : 'Excluir selecionados'}
        </button>
      </div>

      {error && <div className="contacts-error-banner">{error}</div>}

      <div className="contacts-filters">
        <label>
          Lista
          <select
            value={filterListId === '' ? '' : filterListId}
            onChange={(e) => setFilterListId(e.target.value === '' ? '' : Number(e.target.value))}
          >
            <option value="">Todas</option>
            {lists.map((l) => (
              <option key={l.id} value={l.id}>{l.name} ({l.contact_count})</option>
            ))}
          </select>
        </label>
        <label>
          Tag
          <select value={filterTag} onChange={(e) => setFilterTag(e.target.value)}>
            <option value="">Nenhuma</option>
            {tags.map((t) => (
              <option key={t.id} value={t.name}>{t.name}</option>
            ))}
          </select>
        </label>
      </div>

      {loading ? (
        <p className="contacts-loading">Carregando…</p>
      ) : contacts.length === 0 ? (
        <div className="contacts-empty">
          <p>Nenhum contato com os filtros atuais.</p>
          <p>Use <strong>Listas</strong> para importar CSV ou adicionar contatos a uma lista.</p>
        </div>
      ) : (
        <div className="contacts-table-wrap">
          <table className="contacts-table">
            <thead>
              <tr>
                <th>
                  <input
                    type="checkbox"
                    checked={contacts.length > 0 && selectedIds.length === contacts.length}
                    onChange={(e) => toggleSelectAll(e.target.checked)}
                    aria-label="Selecionar todos"
                  />
                </th>
                <th>Telefone</th>
                <th>Nome</th>
                <th>Email</th>
                <th>Tags</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {contacts.map((c) => (
                <tr key={c.id}>
                  <td>
                    <input
                      type="checkbox"
                      checked={selectedIds.includes(c.id)}
                      onChange={(e) => toggleSelect(c.id, e.target.checked)}
                      aria-label={`Selecionar contato ${c.phone}`}
                    />
                  </td>
                  <td className="contacts-cell-phone">{c.phone}</td>
                  <td>{c.name || '—'}</td>
                  <td>{c.email || '—'}</td>
                  <td>
                    <span className="contacts-tags">
                      {c.tags.length ? c.tags.map((t) => <span key={t} className="contacts-tag">{t}</span>) : '—'}
                    </span>
                  </td>
                  <td><span className={`contacts-status contacts-status--${c.status || 'ativo'}`}>{c.status || 'ativo'}</span></td>
                  <td className="contacts-actions">
                    <button type="button" className="contacts-btn-icon" onClick={() => handleEdit(c)} title="Editar">✎</button>
                    <button type="button" className="contacts-btn-icon danger" onClick={() => handleDelete(c.id)} title="Remover">×</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showForm && editingContact != null && (
        <ContactForm
          contact={editingContact}
          allTags={tags}
          onClose={() => { setShowForm(false); setEditingContact(null) }}
          onSuccess={handleFormSuccess}
        />
      )}
    </div>
  )
}

function ContactForm({
  contact,
  allTags,
  onClose,
  onSuccess,
}: {
  contact: Contact | null
  allTags: TagItem[]
  onClose: () => void
  onSuccess: () => void
}) {
  const [phone, setPhone] = useState(contact?.phone ?? '')
  const [name, setName] = useState(contact?.name ?? '')
  const [email, setEmail] = useState(contact?.email ?? '')
  const [optIn, setOptIn] = useState(contact?.opt_in ?? true)
  const [selectedTagIds, setSelectedTagIds] = useState<number[]>(() => {
    if (!contact) return []
    const byName = new Map(allTags.map((t) => [t.name, t.id]))
    return contact.tags.map((n) => byName.get(n)).filter((v): v is number => typeof v === 'number')
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const isEdit = !!contact

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    if (isEdit) {
      contactsApi.update(contact!.id, {
        name: name || undefined,
        email: email || undefined,
        opt_in: optIn,
        tag_ids: selectedTagIds,
      })
        .then(onSuccess)
        .catch((err) => setError(getApiErrorMessage(err)))
        .finally(() => setLoading(false))
    } else {
      contactsApi.create({ phone: phone.trim(), name: name.trim() || undefined, email: email.trim() || undefined, opt_in: optIn })
        .then(onSuccess)
        .catch((err) => setError(getApiErrorMessage(err)))
        .finally(() => setLoading(false))
    }
  }

  return (
    <div className="contacts-modal" role="dialog" aria-modal="true">
      <div className="contacts-modal-backdrop" onClick={onClose} />
      <div className="contacts-modal-content">
        <h2>{isEdit ? 'Editar contato' : 'Novo contato'}</h2>
        <form onSubmit={handleSubmit}>
          {error && <div className="contacts-form-error">{error}</div>}
          {!isEdit && (
            <label>
              Telefone *
              <input value={phone} onChange={(e) => setPhone(e.target.value)} required placeholder="5511999999999" />
            </label>
          )}
          {isEdit && <p className="contacts-form-phone">Telefone: {contact?.phone}</p>}
          <label>
            Nome
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Nome" />
          </label>
          <label>
            Email
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="email@exemplo.com" />
          </label>
          <label className="contacts-check">
            <input type="checkbox" checked={optIn} onChange={(e) => setOptIn(e.target.checked)} />
            Opt-in (pode receber mensagens)
          </label>
          <fieldset className="contacts-tags-fieldset">
            <legend>Tags</legend>
            {allTags.length === 0 ? (
              <p className="contacts-tags-empty">Nenhuma tag cadastrada.</p>
            ) : (
              <div className="contacts-tags-selector">
                {allTags.map((t) => (
                  <label key={t.id} className="contacts-check">
                    <input
                      type="checkbox"
                      checked={selectedTagIds.includes(t.id)}
                      onChange={(e) =>
                        setSelectedTagIds((prev) =>
                          e.target.checked
                            ? (prev.includes(t.id) ? prev : [...prev, t.id])
                            : prev.filter((id) => id !== t.id)
                        )
                      }
                    />
                    {t.name}
                  </label>
                ))}
              </div>
            )}
          </fieldset>
          <div className="contacts-form-actions">
            <button type="button" onClick={onClose}>Cancelar</button>
            <button type="submit" disabled={loading}>{loading ? 'Salvando…' : 'Salvar'}</button>
          </div>
        </form>
      </div>
    </div>
  )
}

