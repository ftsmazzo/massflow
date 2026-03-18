import { useState } from 'react'
import { contactsApi, type ListItem } from '../services/api'
import { getApiErrorMessage } from '../services/api'
import '../pages/Contacts.css'

export default function ImportCsvModal({
  lists,
  defaultListId,
  onClose,
  onSuccess,
}: {
  lists: ListItem[]
  defaultListId?: number
  onClose: () => void
  onSuccess: () => void
}) {
  const [file, setFile] = useState<File | null>(null)
  const [listId, setListId] = useState<number | ''>(defaultListId ?? '')
  const [tagNames, setTagNames] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<{ created: number; updated: number; errors: unknown[] } | null>(null)

  const listFixed = defaultListId != null
  const effectiveListId = listFixed ? defaultListId : listId
  const listRequired = listFixed || lists.length > 0

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
    if (listRequired && !effectiveListId) {
      setError('Selecione uma lista para importar os contatos (público da campanha).')
      return
    }
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
          list_id: effectiveListId ? Number(effectiveListId) : undefined,
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
        <p className="contacts-import-hint">
          Contatos entram para uma lista (público da campanha). Cabeçalho do CSV: &quot;phone&quot;, &quot;telefone&quot; ou &quot;celular&quot;; opcional: &quot;nome&quot;, &quot;email&quot;.
        </p>
        {!listFixed && lists.length === 0 ? (
          <>
            <div className="contacts-form-error">Crie uma lista em Listas antes de importar contatos.</div>
            <div className="contacts-form-actions">
              <button type="button" onClick={onClose}>Fechar</button>
            </div>
          </>
        ) : (
          <>
            {!listFixed && (
              <label>
                Lista (obrigatório)
                <select value={listId === '' ? '' : listId} onChange={(e) => setListId(e.target.value === '' ? '' : Number(e.target.value))} required>
                  <option value="">Selecione uma lista</option>
                  {lists.map((l) => (
                    <option key={l.id} value={l.id}>{l.name}</option>
                  ))}
                </select>
              </label>
            )}
            <label>
              Arquivo CSV
              <input type="file" accept=".csv,.txt" onChange={handleFileChange} />
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
          </>
        )}
      </div>
    </div>
  )
}
