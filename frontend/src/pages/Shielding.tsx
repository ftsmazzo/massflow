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
  risk: {
    pause_on_403: true,
    pause_on_429: true,
    check_whatsapp_before_send: false,
    max_consecutive_errors: 3,
    pause_duration_sec: 3600,
  },
  content: {
    max_repetition_alert_pct: 70,
    require_personalization: true,
    opt_out_keywords: ['sair', 'descadastrar', 'stop', 'parar', 'remover', 'cancelar'],
  },
  schedule: { start_hour: 9, end_hour: 18, timezone: 'America/Sao_Paulo' },
}

const PRESETS: { id: string; label: string; desc: string; config: ShieldingConfig }[] = [
  {
    id: 'conservador',
    label: 'Conservador',
    desc: 'Máxima proteção, menor volume',
    config: {
      ...emptyConfig,
      delays: { min_sec: 30, max_sec: 60 },
      batches: { size_min: 10, size_max: 20, pause_between_min_sec: 900, pause_between_max_sec: 1200 },
      long_pause: { after_messages: 30, duration_min_sec: 1200, duration_max_sec: 2400 },
      limits: { max_per_hour: 15, max_per_day: 80, new_account_max_per_day: 25, new_account_days: 14 },
      warmup: { enabled: true, days: 14, max_per_day: 15 },
      rotation: { enabled: true, switch_after_messages: 50 },
    },
  },
  {
    id: 'moderado',
    label: 'Moderado',
    desc: 'Recomendado para a maioria',
    config: {
      ...emptyConfig,
      delays: { min_sec: 20, max_sec: 45 },
      batches: { size_min: 15, size_max: 30, pause_between_min_sec: 600, pause_between_max_sec: 900 },
      long_pause: { after_messages: 50, duration_min_sec: 900, duration_max_sec: 1800 },
      limits: { max_per_hour: 30, max_per_day: 200, new_account_max_per_day: 50, new_account_days: 7 },
      warmup: { enabled: true, days: 7, max_per_day: 20 },
      rotation: { enabled: true, switch_after_messages: 100 },
    },
  },
  {
    id: 'agressivo',
    label: 'Agressivo',
    desc: 'Maior volume, mais risco',
    config: {
      ...emptyConfig,
      delays: { min_sec: 10, max_sec: 25 },
      batches: { size_min: 25, size_max: 50, pause_between_min_sec: 300, pause_between_max_sec: 600 },
      long_pause: { after_messages: 80, duration_min_sec: 600, duration_max_sec: 1200 },
      limits: { max_per_hour: 50, max_per_day: 400, new_account_max_per_day: 100, new_account_days: 3 },
      warmup: { enabled: true, days: 3, max_per_day: 40 },
      rotation: { enabled: true, switch_after_messages: 150 },
    },
  },
]

function Slider({
  label,
  value,
  min,
  max,
  step = 1,
  unit = '',
  onChange,
}: {
  label: string
  value: number
  min: number
  max: number
  step?: number
  unit?: string
  onChange: (v: number) => void
}) {
  return (
    <div className="shielding-slider-wrap">
      <div className="shielding-slider-label">
        <span>{label}</span>
        <span className="shielding-slider-value">{value}{unit}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="shielding-slider"
      />
    </div>
  )
}

function Toggle({
  label,
  checked,
  onChange,
}: {
  label: string
  checked: boolean
  onChange: (v: boolean) => void
}) {
  return (
    <label className="shielding-toggle">
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      <span className="shielding-toggle-slider" />
      <span className="shielding-toggle-text">{label}</span>
    </label>
  )
}

export default function Shielding() {
  const [config, setConfig] = useState<ShieldingConfig>(emptyConfig)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)
  const [advancedOpen, setAdvancedOpen] = useState(false)

  useEffect(() => {
    shieldingApi
      .get()
      .then((r) => setConfig(r.data))
      .catch(() => setError('Falha ao carregar configurações.'))
      .finally(() => setLoading(false))
  }, [])

  function applyPreset(presetConfig: ShieldingConfig) {
    setConfig(presetConfig)
    setSaved(false)
  }

  function updateNested<K extends keyof ShieldingConfig>(
    key: K,
    nestedKey: keyof ShieldingConfig[K],
    value: number | boolean | string | string[]
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

  const limitProfile = config.limits.max_per_day <= 100 ? 'low' : config.limits.max_per_day <= 250 ? 'mid' : 'high'
  function setLimitProfile(profile: 'low' | 'mid' | 'high') {
    const sets = { low: { max_per_day: 80, max_per_hour: 15 }, mid: { max_per_day: 200, max_per_hour: 30 }, high: { max_per_day: 400, max_per_hour: 50 } }
    const s = sets[profile]
    setConfig((c) => ({
      ...c,
      limits: { ...c.limits, max_per_day: s.max_per_day, max_per_hour: s.max_per_hour },
    }))
    setSaved(false)
  }

  const scheduleProfile = config.schedule.start_hour === 9 && config.schedule.end_hour === 18 ? 'comercial' : config.schedule.start_hour === 0 && config.schedule.end_hour === 23 ? '24h' : 'estendido'
  function setScheduleProfile(profile: 'comercial' | 'estendido' | '24h') {
    const sets = { comercial: [9, 18], estendido: [8, 20], '24h': [0, 23] }
    const [start, end] = sets[profile]
    setConfig((c) => ({
      ...c,
      schedule: { ...c.schedule, start_hour: start, end_hour: end },
    }))
    setSaved(false)
  }

  if (loading) return <div className="shielding-loading">Carregando configurações…</div>

  return (
    <div className="shielding-page">
      <header className="shielding-header">
        <h1>Blindagem</h1>
        <p className="shielding-subtitle">
          Reduza bloqueios com envio inteligente. Escolha um perfil ou ajuste abaixo.
        </p>
      </header>

      {error && <div className="shielding-error" role="alert">{error}</div>}
      {saved && <div className="shielding-saved" role="status">Configurações salvas.</div>}

      <form onSubmit={handleSubmit} className="shielding-form">
        {/* Presets */}
        <section className="shielding-section shielding-presets">
          <h2 className="shielding-section-title">Perfil de envio</h2>
          <p className="shielding-hint">Um clique aplica todas as regras recomendadas para esse perfil.</p>
          <div className="shielding-preset-grid">
            {PRESETS.map((p) => (
              <button
                key={p.id}
                type="button"
                className="shielding-preset-card"
                onClick={() => applyPreset(p.config)}
              >
                <span className="shielding-preset-label">{p.label}</span>
                <span className="shielding-preset-desc">{p.desc}</span>
              </button>
            ))}
          </div>
        </section>

        {/* Limites + Horário em linha */}
        <section className="shielding-section">
          <h2 className="shielding-section-title">Limite e horário</h2>
          <div className="shielding-block">
            <span className="shielding-block-label">Limite diário por instância</span>
            <div className="shielding-pills">
              {(['low', 'mid', 'high'] as const).map((id) => (
                <button
                  key={id}
                  type="button"
                  className={`shielding-pill ${limitProfile === id ? 'active' : ''}`}
                  onClick={() => setLimitProfile(id)}
                >
                  {id === 'low' && 'Baixo (até 80/dia)'}
                  {id === 'mid' && 'Médio (até 200/dia)'}
                  {id === 'high' && 'Alto (até 400/dia)'}
                </button>
              ))}
            </div>
          </div>
          <div className="shielding-block">
            <span className="shielding-block-label">Horário de envio</span>
            <div className="shielding-pills">
              {(['comercial', 'estendido', '24h'] as const).map((id) => (
                <button
                  key={id}
                  type="button"
                  className={`shielding-pill ${scheduleProfile === id ? 'active' : ''}`}
                  onClick={() => setScheduleProfile(id)}
                >
                  {id === 'comercial' && 'Comercial (9h–18h)'}
                  {id === 'estendido' && 'Estendido (8h–20h)'}
                  {id === '24h' && '24 horas'}
                </button>
              ))}
            </div>
          </div>
        </section>

        {/* Toggles */}
        <section className="shielding-section">
          <h2 className="shielding-section-title">Proteções ativas</h2>
          <div className="shielding-toggles">
            <Toggle
              label="Aquecimento de contas novas (envio leve nos primeiros dias)"
              checked={config.warmup.enabled}
              onChange={(v) => updateNested('warmup', 'enabled', v)}
            />
            <Toggle
              label="Rotação entre instâncias (distribui o envio)"
              checked={config.rotation.enabled}
              onChange={(v) => updateNested('rotation', 'enabled', v)}
            />
            <Toggle
              label="Pausar em erros 403/429 (protege a instância)"
              checked={config.risk.pause_on_403 && config.risk.pause_on_429}
              onChange={(v) => {
                updateNested('risk', 'pause_on_403', v)
                updateNested('risk', 'pause_on_429', v)
              }}
            />
            <Toggle
              label="Validar número com WhatsApp antes do envio (reduz falhas em números inválidos)"
              checked={config.risk.check_whatsapp_before_send}
              onChange={(v) => updateNested('risk', 'check_whatsapp_before_send', v)}
            />
            <Toggle
              label="Recomendar personalização (ex.: uso de variáveis)"
              checked={config.content.require_personalization}
              onChange={(v) => updateNested('content', 'require_personalization', v)}
            />
          </div>
        </section>

        {/* Avançado */}
        <section className="shielding-section shielding-advanced">
          <button
            type="button"
            className="shielding-advanced-toggle"
            onClick={() => setAdvancedOpen((o) => !o)}
            aria-expanded={advancedOpen}
          >
            {advancedOpen ? 'Ocultar opções avançadas' : 'Mostrar opções avançadas'}
          </button>
          {advancedOpen && (
            <div className="shielding-advanced-content">
              <h3>Intervalo entre mensagens (seg)</h3>
              <div className="shielding-sliders">
                <Slider
                  label="Mínimo"
                  min={5}
                  max={120}
                  value={config.delays.min_sec}
                  onChange={(v) => updateNested('delays', 'min_sec', v)}
                  unit="s"
                />
                <Slider
                  label="Máximo"
                  min={10}
                  max={180}
                  value={config.delays.max_sec}
                  onChange={(v) => updateNested('delays', 'max_sec', v)}
                  unit="s"
                />
              </div>

              <h3>Tamanho do lote e pausa</h3>
              <div className="shielding-sliders">
                <Slider
                  label="Mensagens por lote"
                  min={5}
                  max={80}
                  value={config.batches.size_max}
                  onChange={(v) => {
                    setConfig((c) => ({
                      ...c,
                      batches: {
                        ...c.batches,
                        size_max: v,
                        size_min: Math.min(c.batches.size_min, v),
                      },
                    }))
                    setSaved(false)
                  }}
                />
                <Slider
                  label="Pausa entre lotes (min)"
                  min={2}
                  max={45}
                  value={Math.round(config.batches.pause_between_min_sec / 60)}
                  onChange={(v) => {
                    const sec = v * 60
                    updateNested('batches', 'pause_between_min_sec', sec)
                    updateNested('batches', 'pause_between_max_sec', Math.min(3600, sec + 300))
                  }}
                  unit=" min"
                />
              </div>

              <h3>Pausa longa (após quantas mensagens)</h3>
              <Slider
                label="A cada"
                min={20}
                max={150}
                value={config.long_pause.after_messages}
                onChange={(v) => updateNested('long_pause', 'after_messages', v)}
                unit=" msg"
              />

              <h3>Risco: pausar após erros</h3>
              <div className="shielding-sliders">
                <Slider
                  label="Erros consecutivos"
                  min={1}
                  max={10}
                  value={config.risk.max_consecutive_errors}
                  onChange={(v) => updateNested('risk', 'max_consecutive_errors', v)}
                />
                <Slider
                  label="Tempo de pausa (min)"
                  min={5}
                  max={120}
                  value={Math.round(config.risk.pause_duration_sec / 60)}
                  onChange={(v) => updateNested('risk', 'pause_duration_sec', v * 60)}
                  unit=" min"
                />
              </div>

              <h3>Conta nova</h3>
              <div className="shielding-sliders">
                <Slider
                  label="Máx/dia (conta nova)"
                  min={10}
                  max={150}
                  value={config.limits.new_account_max_per_day}
                  onChange={(v) => updateNested('limits', 'new_account_max_per_day', v)}
                />
                <Slider
                  label="Dias considerados “conta nova”"
                  min={1}
                  max={30}
                  value={config.limits.new_account_days}
                  onChange={(v) => updateNested('limits', 'new_account_days', v)}
                />
              </div>

              <h3>Aquecimento</h3>
              <div className="shielding-sliders">
                <Slider
                  label="Dias de aquecimento"
                  min={1}
                  max={21}
                  value={config.warmup.days}
                  onChange={(v) => updateNested('warmup', 'days', v)}
                />
                <Slider
                  label="Máx/dia no aquecimento"
                  min={5}
                  max={50}
                  value={config.warmup.max_per_day}
                  onChange={(v) => updateNested('warmup', 'max_per_day', v)}
                />
              </div>

              <h3>Rotação</h3>
              <Slider
                label="Trocar instância a cada"
                min={30}
                max={300}
                value={config.rotation.switch_after_messages}
                onChange={(v) => updateNested('rotation', 'switch_after_messages', v)}
                unit=" msg"
              />

              <h3>Conteúdo</h3>
              <Slider
                label="Alerta se repetição &gt; (%)"
                min={50}
                max={95}
                value={config.content.max_repetition_alert_pct}
                onChange={(v) => updateNested('content', 'max_repetition_alert_pct', v)}
                unit="%"
              />
              <label className="shielding-textarea-label">
                Palavras de opt-out (uma por linha)
                <textarea
                  rows={2}
                  value={config.content.opt_out_keywords.join('\n')}
                  onChange={(e) =>
                    updateNested(
                      'content',
                      'opt_out_keywords',
                      e.target.value.split('\n').map((s) => s.trim().toLowerCase()).filter(Boolean)
                    )
                  }
                  placeholder="sair, descadastrar, stop..."
                />
              </label>

              <h3>Fuso horário</h3>
              <input
                type="text"
                className="shielding-timezone"
                value={config.schedule.timezone}
                onChange={(e) => updateNested('schedule', 'timezone', e.target.value.trim() || 'America/Sao_Paulo')}
                placeholder="America/Sao_Paulo"
              />
            </div>
          )}
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
