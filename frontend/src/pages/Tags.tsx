import { useState, useEffect } from 'react'
import { tagsApi, contactsApi, listsApi, type TagItem, type Contact, type ListItem } from '../services/api'
import { getApiErrorMessage } from '../services/api'
import './Tags.css'

export default function Tags() {
  const [tags, setTags] = useState<TagItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [showApply, setShowApply] = useState<TagItem | null>(null)
  const [showBulk, setShowBulk] = useState(false)

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
        <div className="tags-header-actions">
          <button type="button" className="tags-btn secondary" onClick={() => setShowBulk(true)}>
            Operação em massa
          </button>
          <button type="button" className="tags-btn primary" onClick={handleCreate}>
            Nova tag
          </button>
        </div>
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

      {showBulk && (
        <BulkTagModal
          tags={tags}
          onClose={() => setShowBulk(false)}
          onSuccess={load}
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
  const [lists, setLists] = useState<ListItem[]>([])
  const [listId, setListId] = useState<number | ''>('')
  const [tagsFilter, setTagsFilter] = useState('')
  const [contacts, setContacts] = useState<Contact[]>([])
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    listsApi
      .list()
      .then((r) => setLists(r.data))
      .catch(() => {})
  }, [])

  useEffect(() => {
    setLoading(true)
    setError('')
    contactsApi
      .list({
        limit: 500,
        ...(listId !== '' ? { list_id: listId } : {}),
        ...(tagsFilter.trim() ? { tags: tagsFilter.trim() } : {}),
      })
      .then((r) => setContacts(r.data))
      .catch(() => setError('Falha ao carregar contatos.'))
      .finally(() => setLoading(false))
  }, [listId, tagsFilter])

  function toggle(id: number) {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  function selectAllVisible() {
    setSelectedIds(new Set(contacts.map((c) => c.id)))
  }

  function clearSelection() {
    setSelectedIds(new Set())
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
      <div className="tags-modal-content tags-modal-xwide">
        <h2>Aplicar tag &quot;{tag.name}&quot;</h2>
        <p className="tags-hint">
          Filtre por lista e/ou tags (nomes separados por vírgula). A API considera contatos que tenham{' '}
          <strong>qualquer uma</strong> das tags indicadas.
        </p>
        <div className="tags-filters-row">
          <label className="tags-filter-field">
            Lista
            <select
              value={listId === '' ? '' : String(listId)}
              onChange={(e) => setListId(e.target.value === '' ? '' : Number(e.target.value))}
            >
              <option value="">Todas</option>
              {lists.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.name} ({l.contact_count})
                </option>
              ))}
            </select>
          </label>
          <label className="tags-filter-field grow">
            Filtrar por tags (nomes)
            <input
              value={tagsFilter}
              onChange={(e) => setTagsFilter(e.target.value)}
              placeholder="ex: super endividamento, disparo 1"
            />
          </label>
        </div>
        <div className="tags-bulk-toolbar">
          <button type="button" className="tags-btn-link" onClick={selectAllVisible} disabled={loading || contacts.length === 0}>
            Selecionar todos (até {contacts.length})
          </button>
          <button type="button" className="tags-btn-link" onClick={clearSelection} disabled={selectedIds.size === 0}>
            Limpar seleção
          </button>
        </div>
        {error && <div className="tags-form-error">{error}</div>}
        {loading ? (
          <p>Carregando contatos…</p>
        ) : (
          <div className="tags-apply-list">
            {contacts.map((c) => (
              <label key={c.id} className="tags-apply-row">
                <input type="checkbox" checked={selectedIds.has(c.id)} onChange={() => toggle(c.id)} />
                <span>{c.phone}</span>
                <span>{c.name || '—'}</span>
                <span className="tags-apply-tags" title={(c.tags || []).join(', ')}>
                  {(c.tags || []).slice(0, 3).join(', ')}
                  {(c.tags || []).length > 3 ? '…' : ''}
                </span>
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

function tagToggle(set: Set<number>, id: number, on: boolean) {
  const next = new Set(set)
  if (on) next.add(id)
  else next.delete(id)
  return next
}

function BulkTagModal({
  tags,
  onClose,
  onSuccess,
}: {
  tags: TagItem[]
  onClose: () => void
  onSuccess: () => void
}) {
  const [lists, setLists] = useState<ListItem[]>([])
  const [listId, setListId] = useState<number | ''>('')
  const [idsText, setIdsText] = useState('')
  const [requireAll, setRequireAll] = useState<Set<number>>(new Set())
  const [withoutAny, setWithoutAny] = useState<Set<number>>(new Set())
  const [addIds, setAddIds] = useState<Set<number>>(new Set())
  const [removeIds, setRemoveIds] = useState<Set<number>>(new Set())
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<string | null>(null)

  useEffect(() => {
    listsApi
      .list()
      .then((r) => setLists(r.data))
      .catch(() => {})
  }, [])

  function parseContactIds(): number[] | null {
    const raw = idsText
      .split(/[\s,;]+/)
      .map((s) => s.trim())
      .filter(Boolean)
    const ids = raw.map((s) => Number(s)).filter((n) => Number.isInteger(n) && n > 0)
    return ids.length ? ids : null
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setResult(null)
    const contact_ids = parseContactIds()
    if (listId === '' && !contact_ids) {
      setError('Escolha uma lista ou informe ao menos um ID de contato.')
      return
    }
    if (addIds.size === 0 && removeIds.size === 0) {
      setError('Marque ao menos uma tag para adicionar ou para remover.')
      return
    }
    setSaving(true)
    tagsApi
      .bulkUpdate({
        ...(listId !== '' ? { list_id: listId } : {}),
        ...(contact_ids ? { contact_ids } : {}),
        require_all_tag_ids: Array.from(requireAll),
        without_any_tag_ids: Array.from(withoutAny),
        add_tag_ids: Array.from(addIds),
        remove_tag_ids: Array.from(removeIds),
      })
      .then((r) => {
        const c = r.data.capped ? ' Limite de 5000 contatos; refine os filtros se precisar de todos.' : ''
        setResult(
          `Concluído: ${r.data.matched_leads} contato(s) no escopo; +${r.data.tags_added_links} vínculos adicionados, −${r.data.tags_removed_links} removidos.${c}`
        )
        onSuccess()
      })
      .catch((err) => setError(getApiErrorMessage(err)))
      .finally(() => setSaving(false))
  }

  return (
    <div className="tags-modal" role="dialog" aria-modal="true">
      <div className="tags-modal-backdrop" onClick={onClose} />
      <div className="tags-modal-content tags-modal-xwide">
        <h2>Operação em massa</h2>
        <p className="tags-hint">
          Defina o escopo (lista e/ou IDs), refine com &quot;deve ter todas&quot; e &quot;não pode ter nenhuma&quot;, depois
          adicione ou remova tags. Ex.: lista base + deve ter &quot;super endividamento&quot; + sem &quot;disparo 2&quot; +
          adicionar &quot;disparo 3&quot;.
        </p>
        <form onSubmit={handleSubmit}>
          {error && <div className="tags-form-error">{error}</div>}
          {result && <div className="tags-form-success">{result}</div>}
          <div className="tags-bulk-section">
            <h3>Escopo</h3>
            <label className="tags-filter-field">
              Lista (opcional)
              <select
                value={listId === '' ? '' : String(listId)}
                onChange={(e) => setListId(e.target.value === '' ? '' : Number(e.target.value))}
              >
                <option value="">— Nenhuma (só IDs abaixo) —</option>
                {lists.map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.name} ({l.contact_count})
                  </option>
                ))}
              </select>
            </label>
            <label className="tags-filter-field">
              IDs de contatos (opcional, um por linha ou separados por vírgula)
              <textarea
                value={idsText}
                onChange={(e) => setIdsText(e.target.value)}
                rows={3}
                placeholder="Ex: 149&#10;150"
              />
            </label>
          </div>
          <div className="tags-bulk-section">
            <h3>Filtros por tags</h3>
            <p className="tags-hint small">Marque &quot;deve ter todas&quot; para exigir todas as tags marcadas. &quot;Não pode ter nenhuma&quot; exclui quem tiver qualquer uma das marcadas.</p>
            <div className="tags-bulk-two-cols">
              <div>
                <strong>Deve ter todas</strong>
                <ul className="tags-bulk-check-list">
                  {tags.map((t) => (
                    <li key={`req-${t.id}`}>
                      <label>
                        <input
                          type="checkbox"
                          checked={requireAll.has(t.id)}
                          onChange={(e) => setRequireAll(tagToggle(requireAll, t.id, e.target.checked))}
                        />
                        {t.name}
                      </label>
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <strong>Não pode ter nenhuma destas</strong>
                <ul className="tags-bulk-check-list">
                  {tags.map((t) => (
                    <li key={`wo-${t.id}`}>
                      <label>
                        <input
                          type="checkbox"
                          checked={withoutAny.has(t.id)}
                          onChange={(e) => setWithoutAny(tagToggle(withoutAny, t.id, e.target.checked))}
                        />
                        {t.name}
                      </label>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
          <div className="tags-bulk-section">
            <h3>Ações</h3>
            <div className="tags-bulk-two-cols">
              <div>
                <strong>Adicionar tags</strong>
                <ul className="tags-bulk-check-list">
                  {tags.map((t) => (
                    <li key={`add-${t.id}`}>
                      <label>
                        <input
                          type="checkbox"
                          checked={addIds.has(t.id)}
                          onChange={(e) => setAddIds(tagToggle(addIds, t.id, e.target.checked))}
                        />
                        {t.name}
                      </label>
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <strong>Remover tags</strong>
                <ul className="tags-bulk-check-list">
                  {tags.map((t) => (
                    <li key={`rm-${t.id}`}>
                      <label>
                        <input
                          type="checkbox"
                          checked={removeIds.has(t.id)}
                          onChange={(e) => setRemoveIds(tagToggle(removeIds, t.id, e.target.checked))}
                        />
                        {t.name}
                      </label>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
          <div className="tags-form-actions">
            <button type="button" onClick={onClose}>Fechar</button>
            <button type="submit" className="primary" disabled={saving}>
              {saving ? 'Aplicando…' : 'Executar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
