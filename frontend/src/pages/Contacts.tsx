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
  const [showImport, setShowImport] = useState(false)

  function loadContacts() {
    const params: Record<string, unknown> = { limit: 200 }
    if (filterListId) params.list_id = filterListId
    if (filterTag.trim()) params.tags = filterTag.trim()
    setLoading(true)
    contactsApi.list(params)
      .then((r) => setContacts(r.data))
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

  function handleCreate() {
    setEditingContact(null)
    setShowForm(true)
  }

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
          <p className="contacts-subtitle">Base de contatos para campanhas e funis</p>
        </div>
        <div className="contacts-header-actions">
          <button type="button" className="contacts-btn secondary" onClick={() => setShowImport(true)}>
            Importar CSV
          </button>
          <button type="button" className="contacts-btn primary" onClick={handleCreate}>
            Novo contato
          </button>
        </div>
      </header>

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
          <p>Nenhum contato ainda.</p>
          <p>Adicione manualmente ou importe um CSV.</p>
          <button type="button" className="contacts-btn primary" onClick={handleCreate}>
            Novo contato
          </button>
        </div>
      ) : (
        <div className="contacts-table-wrap">
          <table className="contacts-table">
            <thead>
              <tr>
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

      {showForm && (
        <ContactForm
          contact={editingContact}
          lists={lists}
          tags={tags}
          onClose={() => { setShowForm(false); setEditingContact(null) }}
          onSuccess={handleFormSuccess}
        />
      )}

      {showImport && (
        <ImportCsvModal
          lists={lists}
          tags={tags}
          onClose={() => setShowImport(false)}
          onSuccess={() => { setShowImport(false); loadContacts(); loadListsAndTags() }}
        />
      )}
    </div>
  )
}

function ContactForm({
  contact,
  lists,
  tags,
  onClose,
  onSuccess,
}: {
  contact: Contact | null
  lists: ListItem[]
  tags: TagItem[]
  onClose: () => void
  onSuccess: () => void
}) {
  const [phone, setPhone] = useState(contact?.phone ?? '')
  const [name, setName] = useState(contact?.name ?? '')
  const [email, setEmail] = useState(contact?.email ?? '')
  const [optIn, setOptIn] = useState(contact?.opt_in ?? true)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const isEdit = !!contact

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    if (isEdit) {
      contactsApi.update(contact!.id, { name: name || undefined, email: email || undefined, opt_in: optIn })
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
          <div className="contacts-form-actions">
            <button type="button" onClick={onClose}>Cancelar</button>
            <button type="submit" disabled={loading}>{loading ? 'Salvando…' : 'Salvar'}</button>
          </div>
        </form>
      </div>
    </div>
  )
}

function ImportCsvModal({
  lists,
  tags,
  onClose,
  onSuccess,
}: {
  lists: ListItem[]
  tags: TagItem[]
  onClose: () => void
  onSuccess: () => void
}) {
  const [file, setFile] = useState<File | null>(null)
  const [listId, setListId] = useState<number | ''>('')
  const [tagNames, setTagNames] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<{ created: number; updated: number; errors: unknown[] } | null>(null)

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0]
    setFile(f || null)
    setResult(null)
  }

  function parseCsv(text: string): string[][] {
    const lines = text.split(/\r?\n/).filter((l) => l.trim())
    const rows: string[][] = []
    for (const line of lines) {
      const row: string[] = []
      let current = ''
      let inQuotes = false
      for (let i = 0; i < line.length; i++) {
        const c = line[i]
        if (c === '"') {
          inQuotes = !inQuotes
        } else if ((c === ',' || c === ';') && !inQuotes) {
          row.push(current.trim())
          current = ''
        } else {
          current += c
        }
      }
      row.push(current.trim())
      rows.push(row)
    }
    return rows
  }

  function handleImport() {
    if (!file) return
    setError('')
    setLoading(true)
    setResult(null)
    const reader = new FileReader()
    reader.onload = () => {
      const text = String(reader.result)
      const rows = parseCsv(text)
      if (rows.length < 2) {
        setError('CSV deve ter cabeçalho e ao menos uma linha.')
        setLoading(false)
        return
      }
      const header = rows[0].map((h) => h.toLowerCase().replace(/\s/g, '_'))
      const phoneIdx = header.findIndex((h) => /phone|telefone|celular|whatsapp/.test(h))
      if (phoneIdx < 0) {
        setError('Coluna de telefone não encontrada. Use "phone", "telefone" ou "celular" no cabeçalho.')
        setLoading(false)
        return
      }
      const nameIdx = header.findIndex((h) => /name|nome/.test(h))
      const emailIdx = header.findIndex((h) => /email|e-mail/.test(h))
      const contacts: Array<{ phone: string; name?: string; email?: string; tags?: string[]; list_id?: number; opt_in?: boolean }> = []
      for (let i = 1; i < rows.length; i++) {
        const row = rows[i]
        const phone = (row[phoneIdx] || '').replace(/\D/g, '')
        if (phone.length < 10) continue
        contacts.push({
          phone: phone,
          name: nameIdx >= 0 && row[nameIdx] ? row[nameIdx] : undefined,
          email: emailIdx >= 0 && row[emailIdx] ? row[emailIdx] : undefined,
          tags: tagNames ? tagNames.split(',').map((t) => t.trim()).filter(Boolean) : undefined,
          list_id: listId ? Number(listId) : undefined,
          opt_in: true,
        })
      }
      if (contacts.length === 0) {
        setError('Nenhum telefone válido encontrado.')
        setLoading(false)
        return
      }
      contactsApi.sync(contacts)
        .then((r) => {
          setResult(r.data)
          if (r.data.errors.length === 0) onSuccess()
        })
        .catch((err) => setError(getApiErrorMessage(err)))
        .finally(() => setLoading(false))
    }
    reader.readAsText(file, 'utf-8')
  }

  return (
    <div className="contacts-modal" role="dialog" aria-modal="true">
      <div className="contacts-modal-backdrop" onClick={onClose} />
      <div className="contacts-modal-content contacts-import-modal">
        <h2>Importar CSV</h2>
        <p className="contacts-import-hint">Cabeçalho deve ter coluna "phone", "telefone" ou "celular". Opcional: "nome", "email".</p>
        <label>
          Arquivo CSV
          <input type="file" accept=".csv,.txt" onChange={handleFileChange} />
        </label>
        <label>
          Adicionar à lista
          <select value={listId === '' ? '' : listId} onChange={(e) => setListId(e.target.value === '' ? '' : Number(e.target.value))}>
            <option value="">Nenhuma</option>
            {lists.map((l) => (
              <option key={l.id} value={l.id}>{l.name}</option>
            ))}
          </select>
        </label>
        <label>
          Tags (vírgula)
          <input type="text" value={tagNames} onChange={(e) => setTagNames(e.target.value)} placeholder="ex: importado, base-2025" />
        </label>
        {error && <div className="contacts-form-error">{error}</div>}
        {result && (
          <div className="contacts-import-result">
            <p>Criados: {result.created} · Atualizados: {result.updated}</p>
            {result.errors.length > 0 && <p>Erros: {result.errors.length}</p>}
          </div>
        )}
        <div className="contacts-form-actions">
          <button type="button" onClick={onClose}>Fechar</button>
          <button type="button" className="primary" onClick={handleImport} disabled={!file || loading}>
            {loading ? 'Importando…' : 'Importar'}
          </button>
        </div>
      </div>
    </div>
  )
}
