import { useState, useEffect } from 'react'
import { shieldingApi, type ShieldingConfig } from '../services/api'
import { getApiErrorMessage } from '../services/api'
import './Shielding.css'

const emptyConfig: ShieldingConfig = {
  delays: { min_sec: 20, max_sec: 45 },
  batches: { size_min: 15, size_max: 30, pause_between_min_sec: 600, pause_between_max_sec: 900 },
  long_pause: { after_messages: 50, duration_min_sec: 900, duration_max_sec: 1800 },
  limits: { max_per_hour: 30, max_per_day: 200, new_account_max_per_day: 50, new_account_days: 7 },
  warmup: { enabled: true, days: 7, max_per_day: 20 },
  rotation: { enabled: true, switch_after_messages: 100 },
  risk: { pause_on_403: true, pause_on_429: true, max_consecutive_errors: 3, pause_duration_sec: 3600 },
  content: {
    max_repetition_alert_pct: 70,
    require_personalization: true,
    opt_out_keywords: ['sair', 'descadastrar', 'stop', 'parar', 'remover', 'cancelar'],
  },
  schedule: { start_hour: 9, end_hour: 18, timezone: 'America/Sao_Paulo' },
}

export default function Shielding() {
  const [config, setConfig] = useState<ShieldingConfig>(emptyConfig)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    shieldingApi
      .get()
      .then((r) => setConfig(r.data))
      .catch(() => setError('Falha ao carregar configurações.'))
      .finally(() => setLoading(false))
  }, [])

  function update<K extends keyof ShieldingConfig>(key: K, value: ShieldingConfig[K]) {
    setConfig((c) => ({ ...c, [key]: value }))
    setSaved(false)
  }

  function updateNested<K extends keyof ShieldingConfig>(
    key: K,
    nestedKey: keyof ShieldingConfig[K],
    value: number | boolean | string[]
  ) {
    setConfig((c) => ({
      ...c,
      [key]: { ...(c[key] as object), [nestedKey]: value },
    }))
    setSaved(false)
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setSaving(true)
    shieldingApi
      .put(config)
      .then((r) => {
        setConfig(r.data)
        setSaved(true)
      })
      .catch((err) => setError(getApiErrorMessage(err, 'Falha ao salvar.')))
      .finally(() => setSaving(false))
  }

  if (loading) return <div className="shielding-loading">Carregando configurações de blindagem…</div>

  return (
    <div className="shielding-page">
      <header className="shielding-header">
        <div>
          <h1>Blindagem</h1>
          <p className="shielding-subtitle">
            Configurações globais para evitar e mitigar bloqueios. Delays aleatórios, lotes, limites, aquecimento e detecção de risco.
          </p>
        </div>
      </header>

      {error && (
        <div className="shielding-error" role="alert">
          {error}
        </div>
      )}
      {saved && (
        <div className="shielding-saved" role="status">
          Configurações salvas.
        </div>
      )}

      <form onSubmit={handleSubmit} className="shielding-form">
        {/* Delays */}
        <section className="shielding-section">
          <h2>Intervalo entre mensagens</h2>
          <p className="shielding-hint">Nunca use intervalo fixo. Sempre aleatório entre min e max (segundos).</p>
          <div className="shielding-row">
            <label>
              Mín (seg)
              <input
                type="number"
                min={5}
                max={300}
                value={config.delays.min_sec}
                onChange={(e) => updateNested('delays', 'min_sec', parseInt(e.target.value, 10) || 5)}
              />
            </label>
            <label>
              Máx (seg)
              <input
                type="number"
                min={5}
                max={300}
                value={config.delays.max_sec}
                onChange={(e) => updateNested('delays', 'max_sec', parseInt(e.target.value, 10) || 5)}
              />
            </label>
          </div>
        </section>

        {/* Batches */}
        <section className="shielding-section">
          <h2>Lotes e pausa entre lotes</h2>
          <p className="shielding-hint">Envio em lotes com pausa entre eles (ex.: 15–30 msg, depois 10–15 min de pausa).</p>
          <div className="shielding-row">
            <label>
              Lote mín (msg)
              <input
                type="number"
                min={5}
                max={100}
                value={config.batches.size_min}
                onChange={(e) => updateNested('batches', 'size_min', parseInt(e.target.value, 10) || 5)}
              />
            </label>
            <label>
              Lote máx (msg)
              <input
                type="number"
                min={5}
                max={100}
                value={config.batches.size_max}
                onChange={(e) => updateNested('batches', 'size_max', parseInt(e.target.value, 10) || 5)}
              />
            </label>
            <label>
              Pausa entre lotes mín (seg)
              <input
                type="number"
                min={60}
                max={3600}
                value={config.batches.pause_between_min_sec}
                onChange={(e) => updateNested('batches', 'pause_between_min_sec', parseInt(e.target.value, 10) || 60)}
              />
            </label>
            <label>
              Pausa entre lotes máx (seg)
              <input
                type="number"
                min={60}
                max={3600}
                value={config.batches.pause_between_max_sec}
                onChange={(e) => updateNested('batches', 'pause_between_max_sec', parseInt(e.target.value, 10) || 60)}
              />
            </label>
          </div>
        </section>

        {/* Long pause */}
        <section className="shielding-section">
          <h2>Pausa longa</h2>
          <p className="shielding-hint">Após X mensagens, pausa longa (ex.: 50 msg → 15–30 min) para simular comportamento humano.</p>
          <div className="shielding-row">
            <label>
              Após (msg)
              <input
                type="number"
                min={20}
                max={200}
                value={config.long_pause.after_messages}
                onChange={(e) => updateNested('long_pause', 'after_messages', parseInt(e.target.value, 10) || 20)}
              />
            </label>
            <label>
              Duração mín (seg)
              <input
                type="number"
                min={300}
                max={7200}
                value={config.long_pause.duration_min_sec}
                onChange={(e) => updateNested('long_pause', 'duration_min_sec', parseInt(e.target.value, 10) || 300)}
              />
            </label>
            <label>
              Duração máx (seg)
              <input
                type="number"
                min={300}
                max={7200}
                value={config.long_pause.duration_max_sec}
                onChange={(e) => updateNested('long_pause', 'duration_max_sec', parseInt(e.target.value, 10) || 300)}
              />
            </label>
          </div>
        </section>

        {/* Limits */}
        <section className="shielding-section">
          <h2>Limites por instância</h2>
          <p className="shielding-hint">Máx mensagens/hora e/dia por instância. Contas novas têm teto menor.</p>
          <div className="shielding-row">
            <label>
              Máx/hora
              <input
                type="number"
                min={5}
                max={100}
                value={config.limits.max_per_hour}
                onChange={(e) => updateNested('limits', 'max_per_hour', parseInt(e.target.value, 10) || 5)}
              />
            </label>
            <label>
              Máx/dia
              <input
                type="number"
                min={20}
                max={500}
                value={config.limits.max_per_day}
                onChange={(e) => updateNested('limits', 'max_per_day', parseInt(e.target.value, 10) || 20)}
              />
            </label>
            <label>
              Conta nova: máx/dia
              <input
                type="number"
                min={10}
                max={200}
                value={config.limits.new_account_max_per_day}
                onChange={(e) => updateNested('limits', 'new_account_max_per_day', parseInt(e.target.value, 10) || 10)}
              />
            </label>
            <label>
              Dias “conta nova”
              <input
                type="number"
                min={1}
                max={30}
                value={config.limits.new_account_days}
                onChange={(e) => updateNested('limits', 'new_account_days', parseInt(e.target.value, 10) || 1)}
              />
            </label>
          </div>
        </section>

        {/* Warmup */}
        <section className="shielding-section">
          <h2>Aquecimento (warm-up)</h2>
          <p className="shielding-hint">Instâncias novas: envio leve por N dias antes de liberar volume.</p>
          <div className="shielding-row">
            <label className="shielding-check">
              <input
                type="checkbox"
                checked={config.warmup.enabled}
                onChange={(e) => updateNested('warmup', 'enabled', e.target.checked)}
              />
              Ativar aquecimento
            </label>
            <label>
              Dias
              <input
                type="number"
                min={1}
                max={30}
                value={config.warmup.days}
                onChange={(e) => updateNested('warmup', 'days', parseInt(e.target.value, 10) || 1)}
              />
            </label>
            <label>
              Máx/dia no aquecimento
              <input
                type="number"
                min={5}
                max={50}
                value={config.warmup.max_per_day}
                onChange={(e) => updateNested('warmup', 'max_per_day', parseInt(e.target.value, 10) || 5)}
              />
            </label>
          </div>
        </section>

        {/* Rotation */}
        <section className="shielding-section">
          <h2>Rotação de instâncias</h2>
          <p className="shielding-hint">Trocar de instância a cada N mensagens para distribuir carga.</p>
          <div className="shielding-row">
            <label className="shielding-check">
              <input
                type="checkbox"
                checked={config.rotation.enabled}
                onChange={(e) => updateNested('rotation', 'enabled', e.target.checked)}
              />
              Ativar rotação
            </label>
            <label>
              Trocar a cada (msg)
              <input
                type="number"
                min={20}
                max={500}
                value={config.rotation.switch_after_messages}
                onChange={(e) => updateNested('rotation', 'switch_after_messages', parseInt(e.target.value, 10) || 20)}
              />
            </label>
          </div>
        </section>

        {/* Risk */}
        <section className="shielding-section">
          <h2>Detecção de risco</h2>
          <p className="shielding-hint">Pausar instância em 403/429 ou após N erros consecutivos.</p>
          <div className="shielding-row">
            <label className="shielding-check">
              <input
                type="checkbox"
                checked={config.risk.pause_on_403}
                onChange={(e) => updateNested('risk', 'pause_on_403', e.target.checked)}
              />
              Pausar em 403
            </label>
            <label className="shielding-check">
              <input
                type="checkbox"
                checked={config.risk.pause_on_429}
                onChange={(e) => updateNested('risk', 'pause_on_429', e.target.checked)}
              />
              Pausar em 429
            </label>
            <label>
              Erros consecutivos para pausar
              <input
                type="number"
                min={1}
                max={10}
                value={config.risk.max_consecutive_errors}
                onChange={(e) => updateNested('risk', 'max_consecutive_errors', parseInt(e.target.value, 10) || 1)}
              />
            </label>
            <label>
              Tempo de pausa (seg)
              <input
                type="number"
                min={300}
                max={86400}
                value={config.risk.pause_duration_sec}
                onChange={(e) => updateNested('risk', 'pause_duration_sec', parseInt(e.target.value, 10) || 300)}
              />
            </label>
          </div>
        </section>

        {/* Content */}
        <section className="shielding-section">
          <h2>Conteúdo e opt-out</h2>
          <p className="shielding-hint">Alerta de repetição e palavras que indicam pedido de descadastro.</p>
          <div className="shielding-row">
            <label>
              Alerta repetição (&gt; %)
              <input
                type="number"
                min={50}
                max={100}
                value={config.content.max_repetition_alert_pct}
                onChange={(e) => updateNested('content', 'max_repetition_alert_pct', parseInt(e.target.value, 10) || 50)}
              />
            </label>
            <label className="shielding-check">
              <input
                type="checkbox"
                checked={config.content.require_personalization}
                onChange={(e) => updateNested('content', 'require_personalization', e.target.checked)}
              />
              Recomendar variáveis (ex.: {'{nome}'})
            </label>
          </div>
          <label className="shielding-full">
            Palavras de opt-out (uma por linha)
            <textarea
              rows={2}
              value={config.content.opt_out_keywords.join('\n')}
              onChange={(e) =>
                updateNested(
                  'content',
                  'opt_out_keywords',
                  e.target.value
                    .split('\n')
                    .map((s) => s.trim().toLowerCase())
                    .filter(Boolean)
                )
              }
              placeholder="sair, descadastrar, stop..."
            />
          </label>
        </section>

        {/* Schedule */}
        <section className="shielding-section">
          <h2>Horário permitido</h2>
          <p className="shielding-hint">Só enviar entre início e fim (0–23).</p>
          <div className="shielding-row">
            <label>
              Início (h)
              <input
                type="number"
                min={0}
                max={23}
                value={config.schedule.start_hour}
                onChange={(e) => updateNested('schedule', 'start_hour', parseInt(e.target.value, 10) || 0)}
              />
            </label>
            <label>
              Fim (h)
              <input
                type="number"
                min={0}
                max={23}
                value={config.schedule.end_hour}
                onChange={(e) => updateNested('schedule', 'end_hour', parseInt(e.target.value, 10) || 0)}
              />
            </label>
            <label className="shielding-full">
              Timezone
              <input
                type="text"
                value={config.schedule.timezone}
                onChange={(e) => updateNested('schedule', 'timezone', e.target.value.trim() || 'America/Sao_Paulo')}
                placeholder="America/Sao_Paulo"
              />
            </label>
          </div>
        </section>

        <div className="shielding-actions">
          <button type="submit" className="shielding-btn-save" disabled={saving}>
            {saving ? 'Salvando…' : 'Salvar configurações'}
          </button>
        </div>
      </form>
    </div>
  )
}
