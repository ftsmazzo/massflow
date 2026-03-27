import { useState, useEffect, useRef } from 'react'
import {
  campaignsApi,
  listsApi,
  instancesApi,
  qualificationApi,
  type CampaignItem,
  type ListItem,
  type Instance,
  type CampaignInboundReplyItem,
  type CampaignReport,
  type QualificationConfig,
  type QualificationSessionListItem,
} from '../services/api'
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

const DELETABLE_STATUSES = new Set(['draft', 'cancelled', 'completed', 'scheduled'])
const FIXED_WEBHOOK_URL = 'https://fabricaia-n8n.90qhxz.easypanel.host/webhook/controle-disparo'

function canDeleteCampaign(c: CampaignItem) {
  return DELETABLE_STATUSES.has(c.status)
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
  const [pollingId, setPollingId] = useState<number | null>(null)
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [bulkDeleting, setBulkDeleting] = useState(false)
  const [inboundReplies, setInboundReplies] = useState<CampaignInboundReplyItem[]>([])
  const [repliesLoading, setRepliesLoading] = useState(false)
  const [showReplies, setShowReplies] = useState(false)
  const [reportCampaign, setReportCampaign] = useState<CampaignItem | null>(null)
  const [qualificationCampaign, setQualificationCampaign] = useState<CampaignItem | null>(null)

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

  useEffect(() => {
    if (pollingId == null) return
    const timer = setInterval(() => {
      campaignsApi.list()
        .then((r) => {
          const campaign = r.data.find((c) => c.id === pollingId)
          if (campaign && campaign.status !== 'running') {
            setCampaigns(r.data)
            setPollingId(null)
          }
        })
        .catch(() => setPollingId(null))
    }, 4000)
    return () => clearInterval(timer)
  }, [pollingId])

  function loadInboundReplies() {
    setRepliesLoading(true)
    campaignsApi
      .inboundReplies(40)
      .then((r) => setInboundReplies(r.data))
      .catch(() => setInboundReplies([]))
      .finally(() => setRepliesLoading(false))
  }

  function toggleSelect(id: number) {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  function selectAllDeletable() {
    const ids = campaigns.filter(canDeleteCampaign).map((c) => c.id)
    setSelectedIds(new Set(ids))
  }

  function clearSelection() {
    setSelectedIds(new Set())
  }

  function handleBulkDelete() {
    const ids = [...selectedIds]
    if (ids.length === 0) return
    if (!confirm(`Excluir ${ids.length} campanha(s)? Esta ação não pode ser desfeita.`)) return
    setBulkDeleting(true)
    setError('')
    campaignsApi
      .bulkDelete(ids)
      .then((res) => {
        if (res.data.errors.length > 0) {
          setError(
            `Excluídas: ${res.data.deleted}. Algumas falharam (status em andamento ou não encontrada).`
          )
        }
        clearSelection()
        load()
      })
      .catch((err) => setError(getApiErrorMessage(err)))
      .finally(() => setBulkDeleting(false))
  }

  function handleDelete(c: CampaignItem) {
    if (!canDeleteCampaign(c)) return
    if (!confirm(`Excluir a campanha "${c.name}"?`)) return
    campaignsApi
      .delete(c.id)
      .then(() => {
        setSelectedIds((prev) => {
          const next = new Set(prev)
          next.delete(c.id)
          return next
        })
        load()
      })
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
        setPollingId(c.id)
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
          <p className="campaigns-subtitle">
            Crie e gerencie disparos em massa (lista, conteúdo, blindagem). Respostas do WhatsApp e n8n: configure em{' '}
            <strong>Instâncias</strong> com o botão que aplica o webhook na Evolution (todas as linhas de uma vez).
          </p>
        </div>
        <button type="button" className="campaigns-btn primary" onClick={() => setShowForm(true)}>
          Nova campanha
        </button>
      </header>

      {error && <div className="campaigns-error-banner">{error}</div>}

      <section className="campaigns-replies-section">
        <button
          type="button"
          className="campaigns-btn campaigns-btn-ghost"
          onClick={() => {
            setShowReplies((v) => {
              if (!v) loadInboundReplies()
              return !v
            })
          }}
        >
          {showReplies ? 'Ocultar' : 'Ver'} respostas recebidas (salvas no MassFlow)
        </button>
        {showReplies && (
          <div className="campaigns-replies-panel">
            <div className="campaigns-replies-toolbar">
              <button
                type="button"
                className="campaigns-btn"
                disabled={repliesLoading}
                onClick={() => loadInboundReplies()}
              >
                {repliesLoading ? 'Atualizando…' : 'Atualizar lista'}
              </button>
              <p className="campaigns-form-hint">
                Toda resposta de lead atribuída a uma campanha fica aqui, com ou sem webhook n8n. “Enc. n8n” indica se o
                envio externo foi feito.
              </p>
            </div>
            {inboundReplies.length === 0 && !repliesLoading ? (
              <p className="campaigns-form-hint">Nenhuma resposta registrada ainda.</p>
            ) : (
              <div className="campaigns-replies-table-wrap">
                <table className="campaigns-replies-table">
                  <thead>
                    <tr>
                      <th>Quando</th>
                      <th>Campanha</th>
                      <th>Instância</th>
                      <th>Lead</th>
                      <th>Mensagem</th>
                      <th>Enc. n8n</th>
                    </tr>
                  </thead>
                  <tbody>
                    {inboundReplies.map((row) => (
                      <tr key={row.id}>
                        <td>{row.created_at ? new Date(row.created_at).toLocaleString() : '—'}</td>
                        <td>{row.campaign_name ?? `#${row.campaign_id}`}</td>
                        <td>{row.evolution_instance_label ?? (row.evolution_instance_id != null ? `#${row.evolution_instance_id}` : '—')}</td>
                        <td>
                          {(row.lead_name || '—') + (row.lead_phone ? ` · ${row.lead_phone}` : '')}
                        </td>
                        <td className="campaigns-replies-msg">{row.message_text}</td>
                        <td>
                          {row.forwarded_to_webhook ? 'Sim' : 'Não'}
                          {row.webhook_skip_reason && (
                            <span className="campaigns-replies-skip" title={row.webhook_skip_reason}>
                              ({row.webhook_skip_reason})
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </section>

      {campaigns.length > 0 && (
        <div className="campaigns-bulk-toolbar">
          <label className="campaigns-bulk-select-all">
            <input
              type="checkbox"
              checked={
                campaigns.filter(canDeleteCampaign).length > 0 &&
                campaigns.filter(canDeleteCampaign).every((c) => selectedIds.has(c.id))
              }
              onChange={(e) => (e.target.checked ? selectAllDeletable() : clearSelection())}
            />
            Selecionar todas (excluíveis)
          </label>
          {selectedIds.size > 0 && (
            <button
              type="button"
              className="campaigns-btn danger"
              disabled={bulkDeleting}
              onClick={handleBulkDelete}
            >
              {bulkDeleting ? 'Excluindo…' : `Excluir selecionadas (${selectedIds.size})`}
            </button>
          )}
        </div>
      )}

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
              {canDeleteCampaign(c) && (
                <label className="campaigns-card-select">
                  <input
                    type="checkbox"
                    checked={selectedIds.has(c.id)}
                    onChange={() => toggleSelect(c.id)}
                  />
                </label>
              )}
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
                <button
                  type="button"
                  className="campaigns-btn-link"
                  onClick={() => setReportCampaign(c)}
                >
                  Relatório
                </button>
                <button
                  type="button"
                  className="campaigns-btn-link"
                  onClick={() => setQualificationCampaign(c)}
                >
                  Qualificação
                </button>
                {canDeleteCampaign(c) && (
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
      {reportCampaign && (
        <CampaignReportModal
          campaign={reportCampaign}
          onClose={() => setReportCampaign(null)}
        />
      )}
      {qualificationCampaign && (
        <CampaignQualificationModal
          campaign={qualificationCampaign}
          onClose={() => setQualificationCampaign(null)}
        />
      )}
    </div>
  )
}

function CampaignReportModal({
  campaign,
  onClose,
}: {
  campaign: CampaignItem
  onClose: () => void
}) {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [report, setReport] = useState<CampaignReport | null>(null)
  const [tagName, setTagName] = useState('bloqueio')
  const [tagging, setTagging] = useState(false)
  const [tagResult, setTagResult] = useState('')

  useEffect(() => {
    setLoading(true)
    setError('')
    campaignsApi.report(campaign.id)
      .then((r) => setReport(r.data))
      .catch((err) => setError(getApiErrorMessage(err)))
      .finally(() => setLoading(false))
  }, [campaign.id])

  function handleTagFailedContacts() {
    const t = tagName.trim()
    if (!t) {
      setError('Informe o nome da tag para bloqueio.')
      return
    }
    setTagging(true)
    setTagResult('')
    setError('')
    campaignsApi.tagFailedContacts(campaign.id, t)
      .then((r) => {
        setTagResult(
          `Tag "${r.data.tag_name}" aplicada. Com falha: ${r.data.failed_contacts_found}. Novos marcados: ${r.data.tagged_contacts}.`
        )
      })
      .catch((err) => setError(getApiErrorMessage(err)))
      .finally(() => setTagging(false))
  }

  return (
    <div className="campaigns-modal" role="dialog" aria-modal="true">
      <div className="campaigns-modal-backdrop" onClick={onClose} />
      <div className="campaigns-modal-content campaigns-edit-modal">
        <h2>Relatório da campanha</h2>
        <p className="campaigns-form-hint">
          {campaign.name} · {STATUS_LABEL[campaign.status] ?? campaign.status}
        </p>
        {loading && <p className="campaigns-loading">Carregando relatório…</p>}
        {error && <div className="campaigns-form-error">{error}</div>}
        {report && (
          <>
            <div className="campaigns-report-grid">
              <div><strong>Tentativas:</strong> {report.summary.total_attempts}</div>
              <div><strong>Enviadas:</strong> {report.summary.total_sent}</div>
              <div><strong>Falhas:</strong> {report.summary.total_failed}</div>
              <div><strong>Sem WhatsApp:</strong> {report.summary.failed_without_whatsapp}</div>
              <div><strong>Respostas:</strong> {report.summary.total_replies}</div>
              <div><strong>Positivas:</strong> {report.summary.positive_replies}</div>
            </div>

            <fieldset className="campaigns-fieldset">
              <legend>Ação rápida de bloqueio</legend>
              <label>
                Tag para contatos com falha
                <input value={tagName} onChange={(e) => setTagName(e.target.value)} placeholder="bloqueio" />
              </label>
              <div className="campaigns-form-actions">
                <button type="button" onClick={handleTagFailedContacts} disabled={tagging}>
                  {tagging ? 'Aplicando…' : 'Aplicar tag nos contatos com falha'}
                </button>
              </div>
              {tagResult && <p className="campaigns-form-hint">{tagResult}</p>}
            </fieldset>

            <fieldset className="campaigns-fieldset">
              <legend>Números com erro no disparo</legend>
              {report.messages.filter((m) => m.status === 'failed').length === 0 ? (
                <p className="campaigns-form-hint">Nenhuma falha registrada.</p>
              ) : (
                <div className="campaigns-replies-table-wrap">
                  <table className="campaigns-replies-table">
                    <thead>
                      <tr>
                        <th>Lead</th>
                        <th>Telefone</th>
                        <th>Instância</th>
                        <th>Erro</th>
                      </tr>
                    </thead>
                    <tbody>
                      {report.messages.filter((m) => m.status === 'failed').map((m) => (
                        <tr key={m.id}>
                          <td>{m.lead_name || `#${m.lead_id}`}</td>
                          <td>{m.lead_phone || '—'}</td>
                          <td>{m.evolution_instance_label || (m.evolution_instance_id ?? '—')}</td>
                          <td>{m.error_message || 'Falha sem detalhe'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </fieldset>

            <fieldset className="campaigns-fieldset">
              <legend>Respostas desta campanha</legend>
              {report.replies.length === 0 ? (
                <p className="campaigns-form-hint">Nenhuma resposta recebida.</p>
              ) : (
                <div className="campaigns-replies-table-wrap">
                  <table className="campaigns-replies-table">
                    <thead>
                      <tr>
                        <th>Quando</th>
                        <th>Lead</th>
                        <th>Mensagem</th>
                        <th>Positiva</th>
                        <th>Enc. n8n</th>
                      </tr>
                    </thead>
                    <tbody>
                      {report.replies.map((r) => (
                        <tr key={r.id}>
                          <td>{r.created_at ? new Date(r.created_at).toLocaleString() : '—'}</td>
                          <td>{(r.lead_name || '—') + (r.lead_phone ? ` · ${r.lead_phone}` : '')}</td>
                          <td className="campaigns-replies-msg">{r.message_text}</td>
                          <td>{r.is_positive ? `Sim (${r.matched_keywords.join(', ')})` : 'Não'}</td>
                          <td>{r.forwarded_to_webhook ? 'Sim' : 'Não'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </fieldset>
          </>
        )}
        <div className="campaigns-form-actions">
          <button type="button" onClick={onClose}>Fechar</button>
        </div>
      </div>
    </div>
  )
}

function CampaignQualificationModal({
  campaign,
  onClose,
}: {
  campaign: CampaignItem
  onClose: () => void
}) {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [cfg, setCfg] = useState<QualificationConfig | null>(null)
  const [questionsText, setQuestionsText] = useState('')
  const [scoringText, setScoringText] = useState('')
  const [classifyText, setClassifyText] = useState('')
  const [sessions, setSessions] = useState<QualificationSessionListItem[]>([])

  function loadAll() {
    setLoading(true)
    Promise.all([
      qualificationApi.getConfig(campaign.id),
      qualificationApi.listSessions(campaign.id, 200),
    ])
      .then(([cfgRes, sesRes]) => {
        setCfg(cfgRes.data)
        setQuestionsText(JSON.stringify(cfgRes.data.questions_json ?? [], null, 2))
        setScoringText(JSON.stringify(cfgRes.data.scoring_rules_json ?? {}, null, 2))
        setClassifyText(JSON.stringify(cfgRes.data.classification_rules_json ?? {}, null, 2))
        setSessions(sesRes.data.sessions ?? [])
      })
      .catch((err) => setError(getApiErrorMessage(err)))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    loadAll()
  }, [campaign.id])

  function saveConfig() {
    if (!cfg) return
    setSaving(true)
    setError('')
    try {
      const questions = JSON.parse(questionsText)
      const scoring = JSON.parse(scoringText)
      const classify = JSON.parse(classifyText)
      qualificationApi.saveConfig(campaign.id, {
        enabled: cfg.enabled,
        notify_lawyer: cfg.notify_lawyer,
        final_webhook_url: cfg.final_webhook_url,
        version: cfg.version,
        questions_json: questions,
        scoring_rules_json: scoring,
        classification_rules_json: classify,
      })
        .then((r) => {
          setCfg(r.data)
          setQuestionsText(JSON.stringify(r.data.questions_json ?? [], null, 2))
          setScoringText(JSON.stringify(r.data.scoring_rules_json ?? {}, null, 2))
          setClassifyText(JSON.stringify(r.data.classification_rules_json ?? {}, null, 2))
        })
        .catch((err) => setError(getApiErrorMessage(err)))
        .finally(() => setSaving(false))
    } catch {
      setSaving(false)
      setError('JSON inválido em perguntas/regras.')
    }
  }

  return (
    <div className="campaigns-modal" role="dialog" aria-modal="true">
      <div className="campaigns-modal-backdrop" onClick={onClose} />
      <div className="campaigns-modal-content campaigns-edit-modal">
        <h2>Qualificação da campanha</h2>
        <p className="campaigns-form-hint">{campaign.name}</p>
        {loading && <p className="campaigns-loading">Carregando…</p>}
        {error && <div className="campaigns-form-error">{error}</div>}
        {cfg && (
          <>
            <label className="campaigns-check">
              <input
                type="checkbox"
                checked={cfg.enabled}
                onChange={(e) => setCfg({ ...cfg, enabled: e.target.checked })}
              />
              Habilitar qualificação A-E
            </label>
            <label className="campaigns-check">
              <input
                type="checkbox"
                checked={cfg.notify_lawyer}
                onChange={(e) => setCfg({ ...cfg, notify_lawyer: e.target.checked })}
              />
              Notificar advogado ao concluir
            </label>
            <label>
              Webhook final da qualificação (opcional)
              <input
                value={cfg.final_webhook_url ?? ''}
                onChange={(e) => setCfg({ ...cfg, final_webhook_url: e.target.value || null })}
                placeholder="https://.../webhook/final-qualificacao"
              />
            </label>
            <label>
              Perguntas (JSON)
              <textarea rows={6} value={questionsText} onChange={(e) => setQuestionsText(e.target.value)} />
            </label>
            <label>
              Regras de pontuação (JSON)
              <textarea rows={6} value={scoringText} onChange={(e) => setScoringText(e.target.value)} />
            </label>
            <label>
              Regras de classificação (JSON)
              <textarea rows={4} value={classifyText} onChange={(e) => setClassifyText(e.target.value)} />
            </label>
            <div className="campaigns-form-actions">
              <button type="button" onClick={saveConfig} disabled={saving}>
                {saving ? 'Salvando…' : 'Salvar qualificação'}
              </button>
              <button type="button" onClick={loadAll}>Atualizar sessões</button>
            </div>
            <fieldset className="campaigns-fieldset">
              <legend>Sessões de qualificação (lead x campanha)</legend>
              {sessions.length === 0 ? (
                <p className="campaigns-form-hint">Sem sessões ainda.</p>
              ) : (
                <div className="campaigns-replies-table-wrap">
                  <table className="campaigns-replies-table">
                    <thead>
                      <tr>
                        <th>Lead</th>
                        <th>Telefone</th>
                        <th>Status</th>
                        <th>Score</th>
                        <th>Classificação</th>
                        <th>Respostas</th>
                      </tr>
                    </thead>
                    <tbody>
                      {sessions.map((s) => (
                        <tr key={s.session_id}>
                          <td>{s.lead_name || `#${s.lead_id ?? s.session_id}`}</td>
                          <td>{s.lead_phone}</td>
                          <td>{s.status}</td>
                          <td>{s.score_total}</td>
                          <td>{s.classification || '—'}</td>
                          <td>{s.answers_count}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </fieldset>
          </>
        )}
        <div className="campaigns-form-actions">
          <button type="button" onClick={onClose}>Fechar</button>
        </div>
      </div>
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
  const [responseKeywords, setResponseKeywords] = useState('')
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
    const content: Record<string, unknown> = { type: 'text', text: '' }
    content.campaign_webhook_url = FIXED_WEBHOOK_URL
    const kw = responseKeywords
      .split(',')
      .map((k) => k.trim())
      .filter(Boolean)
    if (kw.length > 0) content.response_keywords = kw
    campaignsApi.create({
      name: name.trim(),
      type,
      list_id: Number(listId),
      content,
    })
      .then(onSuccess)
      .catch((err) => setError(getApiErrorMessage(err)))
      .finally(() => setLoading(false))
  }

  return (
    <div className="campaigns-modal" role="dialog" aria-modal="true">
      <div className="campaigns-modal-backdrop" onClick={onClose} />
      <div className="campaigns-modal-content campaigns-modal-wide">
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
          <p className="campaigns-form-hint">
            Webhook n8n fixo desta operação: <code>{FIXED_WEBHOOK_URL}</code>
          </p>
          <label>
            Palavras-chave (opcional — obrigatórias no texto para disparar o n8n; vão também em matched_keywords)
            <input
              value={responseKeywords}
              onChange={(e) => setResponseKeywords(e.target.value)}
              placeholder="quero, sim, interesse"
            />
          </label>
          <p className="campaigns-form-hint">
            As respostas do lead ficam salvas no MassFlow mesmo sem webhook. O texto completo é definido ao editar o rascunho.
          </p>
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
  const [contentMediaPath, setContentMediaPath] = useState((content.media_path as string) || '')
  const [contentMediaMimetype, setContentMediaMimetype] = useState((content.media_mimetype as string) || '')
  const [contentMediaFilename, setContentMediaFilename] = useState((content.media_filename as string) || '')
  const [contentCaption, setContentCaption] = useState((content.caption as string) || '')
  const [responseKeywords, setResponseKeywords] = useState(
    Array.isArray(content.response_keywords)
      ? (content.response_keywords as string[]).join(', ')
      : String((content.response_keywords as string) || '')
  )
  const [useGlobalShielding, setUseGlobalShielding] = useState(campaign.use_global_shielding)
  const [instanceIds, setInstanceIds] = useState<number[]>(campaign.instance_ids || [])
  const [loading, setLoading] = useState(false)
  const [uploadingMedia, setUploadingMedia] = useState(false)
  const [error, setError] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)

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

  function doSave(mediaPath: string, mediaMimetype: string, mediaFilename: string) {
    const contentPayload: Record<string, unknown> = {
      type: contentType,
      text: contentType === 'text' ? contentText : (contentCaption || contentText || ''),
      ...(contentType !== 'text' && { caption: contentCaption || '' }),
    }
    if (contentType !== 'text' && mediaPath) {
      contentPayload.media_path = mediaPath
      contentPayload.media_mimetype = mediaMimetype
      contentPayload.media_filename = mediaFilename
    }
    contentPayload.campaign_webhook_url = FIXED_WEBHOOK_URL
    const kw = responseKeywords
      .split(',')
      .map((k) => k.trim())
      .filter(Boolean)
    contentPayload.response_keywords = kw
    const payload: Record<string, unknown> = {
      name: name.trim(),
      type,
      list_id: listId,
      content: contentPayload,
      use_global_shielding: useGlobalShielding,
    }
    if (scheduledAt) payload.scheduled_at = scheduledAt
    else payload.scheduled_at = null
    if (instanceIds.length > 0) payload.instance_ids = instanceIds
    else payload.instance_ids = null
    return campaignsApi.update(campaign.id, payload as Partial<CampaignItem>)
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!listId) {
      setError('Selecione uma lista.')
      return
    }
    setError('')
    setLoading(true)

    const fileFromInput = fileInputRef.current?.files?.[0]
    const hasMediaInState = contentType !== 'text' && contentMediaPath

    if (contentType !== 'text' && !hasMediaInState && fileFromInput) {
      campaignsApi.uploadMedia(campaign.id, fileFromInput)
        .then((res) => doSave(res.data.media_path, res.data.media_mimetype, res.data.media_filename))
        .then(onSuccess)
        .catch((err) => setError(getApiErrorMessage(err)))
        .finally(() => setLoading(false))
      return
    }

    if (contentType !== 'text' && !hasMediaInState && !fileFromInput) {
      setError('Anexe um arquivo de mídia (imagem, vídeo, áudio ou documento) antes de salvar.')
      setLoading(false)
      return
    }

    doSave(contentMediaPath, contentMediaMimetype, contentMediaFilename)
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
                  Anexar arquivo (imagem, vídeo, áudio ou documento) — o arquivo é enviado e anexado ao disparo, não link
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*,video/*,audio/*,.pdf,.doc,.docx"
                    onChange={(e) => {
                      const file = e.target.files?.[0]
                      if (!file) return
                      setError('')
                      setUploadingMedia(true)
                      campaignsApi.uploadMedia(campaign.id, file)
                        .then((res) => {
                          setContentMediaPath(res.data.media_path)
                          setContentMediaMimetype(res.data.media_mimetype)
                          setContentMediaFilename(res.data.media_filename)
                          e.target.value = '' // limpa input só após sucesso para permitir trocar arquivo
                        })
                        .catch((err) => setError(getApiErrorMessage(err)))
                        .finally(() => setUploadingMedia(false))
                    }}
                  />
                  {contentMediaFilename && (
                    <p className="campaigns-form-attached" role="status">
                      ✓ Arquivo anexado: <strong>{contentMediaFilename}</strong> — salve a campanha e depois dispare.
                    </p>
                  )}
                  {uploadingMedia && <p className="campaigns-form-hint">Enviando arquivo…</p>}
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
            <p className="campaigns-form-hint">
              Webhook n8n fixo desta operação: <code>{FIXED_WEBHOOK_URL}</code>
            </p>
            <label>
              Palavras-chave (opcional — se preenchidas, o n8n só é chamado se alguma aparecer na resposta)
              <input
                value={responseKeywords}
                onChange={(e) => setResponseKeywords(e.target.value)}
                placeholder="quero, interesse, sim"
              />
            </label>
            <p className="campaigns-form-hint">
              O disparo <strong>não</strong> chama o n8n. Em <strong>Instâncias</strong>, use “Aplicar webhook na Evolution” (todas as linhas).
              Toda resposta fica no MassFlow; com URL aqui, encaminha ao n8n se as palavras-chave baterem (se houver).
            </p>
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
