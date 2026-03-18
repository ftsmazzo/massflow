/**
 * Cliente HTTP para a MassFlow API.
 * Em dev: proxy /api -> localhost:8000. Em produção: mesma origem ou VITE_API_URL.
 */
import axios, { type AxiosError } from 'axios'

/** Extrai mensagem de erro da resposta da API (FastAPI: detail string ou array de validação). */
export function getApiErrorMessage(err: unknown, fallback = 'Ocorreu um erro.'): string {
  if (!err || typeof err !== 'object' || !('response' in err)) {
    const ax = err as AxiosError
    const url = ax.config?.baseURL ? `${ax.config.baseURL}${ax.config?.url ?? ''}` : ''
    const hint = url
      ? `Chamada: ${url}. Pode ser CORS (backend deve permitir a origem do front em CORS_ORIGINS ou CORS_ORIGIN_REGEX), rede ou URL incorreta.`
      : 'URL da API vazia. Defina VITE_API_URL no build do frontend.'
    return `Não foi possível conectar ao servidor. ${hint}`
  }
  const response = (err as AxiosError<{ detail?: string | Array<{ msg?: string; loc?: unknown }> }>).response
  const detail = response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const messages = detail.map((d) => (typeof d === 'object' && d && 'msg' in d ? d.msg : String(d)))
    return messages.filter(Boolean).join(' ') || fallback
  }
  if (response?.status) {
    const url = (err as AxiosError).config?.url
    const base = (err as AxiosError).config?.baseURL
    const full = base ? (base + url) : url
    return full
      ? `Erro ${response.status}. URL: ${full} — ${fallback}`
      : `Erro ${response.status}. ${fallback}`
  }
  return fallback
}

const baseURL = (import.meta.env.VITE_API_URL ?? '').replace(/\/+$/, '')

/** URL base da API (vazia = requisições vão para o mesmo domínio do front; defina VITE_API_URL no build). */
export const apiBaseURL = baseURL

export const api = axios.create({
  baseURL,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('massflow_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('massflow_token')
      localStorage.removeItem('massflow_user')
      window.dispatchEvent(new Event('storage'))
    }
    return Promise.reject(err)
  }
)

// --- Auth
export type Token = { access_token: string; token_type: string }
export type User = { id: number; email: string; name: string | null; tenant_id: number; is_admin: boolean; is_active: boolean }
export type Tenant = { id: number; name: string; slug: string; plan_type: number; credits_balance: number; active: boolean }

/** Body em form-urlencoded para não disparar preflight CORS (evita 405 em proxy). */
function authForm(data: Record<string, string | undefined>): URLSearchParams {
  const p = new URLSearchParams()
  for (const [k, v] of Object.entries(data)) if (v != null && v !== '') p.set(k, v)
  return p
}

export const authApi = {
  login: (email: string, password: string) =>
    api.post<Token>('/api/auth/login', authForm({ email, password }), {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    }),
  register: (data: { email: string; password: string; name?: string; tenant_name: string }) =>
    api.post<Token>('/api/auth/register', authForm({
      email: data.email,
      password: data.password,
      tenant_name: data.tenant_name,
      name: data.name,
    }), {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    }),
  me: () => api.get<User>('/api/auth/me'),
  tenant: () => api.get<Tenant>('/api/tenants/me'),
}

// --- Instances
export type Instance = {
  id: number
  tenant_id: number
  name: string
  api_url: string
  display_name: string | null
  owner: string
  status: string
  phone_number: string | null
  limits: Record<string, unknown>
  created_at: string
}

export const instancesApi = {
  list: (owner?: 'tenant' | 'platform') =>
    api.get<Instance[]>('/api/instances', owner ? { params: { owner } } : undefined),
  get: (id: number) => api.get<Instance>(`/api/instances/${id}`),
  create: (data: { name: string; api_url: string; api_key?: string; display_name?: string }) =>
    api.post<Instance>('/api/instances', data),
  connect: (id: number) =>
    api.post<{ pairing_code?: string; code?: string; count?: number }>(`/api/instances/${id}/connect`),
  disconnect: (id: number) => api.post<Instance>(`/api/instances/${id}/disconnect`),
  refresh: (id: number) => api.post<Instance>(`/api/instances/${id}/refresh`),
  status: (id: number) => api.get<{ instance: string; connection_state: unknown }>(`/api/instances/${id}/status`),
}

// --- Shielding (Blindagem global)
export type ShieldingConfig = {
  delays: { min_sec: number; max_sec: number }
  batches: { size_min: number; size_max: number; pause_between_min_sec: number; pause_between_max_sec: number }
  long_pause: { after_messages: number; duration_min_sec: number; duration_max_sec: number }
  limits: { max_per_hour: number; max_per_day: number; new_account_max_per_day: number; new_account_days: number }
  warmup: { enabled: boolean; days: number; max_per_day: number }
  rotation: { enabled: boolean; switch_after_messages: number }
  risk: { pause_on_403: boolean; pause_on_429: boolean; max_consecutive_errors: number; pause_duration_sec: number }
  content: { max_repetition_alert_pct: number; require_personalization: boolean; opt_out_keywords: string[] }
  schedule: { start_hour: number; end_hour: number; timezone: string }
}

export const shieldingApi = {
  get: () => api.get<ShieldingConfig>('/api/settings/shielding'),
  put: (data: ShieldingConfig) => api.put<ShieldingConfig>('/api/settings/shielding', data),
}

// --- Contacts
export type Contact = {
  id: number
  tenant_id: number
  phone: string
  name: string | null
  email: string | null
  custom_fields: Record<string, unknown>
  opt_in: boolean
  status: string
  tags: string[]
  list_ids: number[]
  created_at: string | null
  updated_at: string | null
  last_sent_at: string | null
  last_response_at: string | null
}

export const contactsApi = {
  list: (params?: { list_id?: number; tags?: string; updated_since?: string; status?: string; opt_in?: boolean; limit?: number; offset?: number }) =>
    api.get<Contact[]>('/api/contacts', { params }),
  get: (id: number) => api.get<Contact>(`/api/contacts/${id}`),
  create: (data: { phone: string; name?: string; email?: string; custom_fields?: Record<string, unknown>; opt_in?: boolean }) =>
    api.post<Contact>('/api/contacts', data),
  update: (id: number, data: { name?: string; email?: string; custom_fields?: Record<string, unknown>; opt_in?: boolean; status?: string }) =>
    api.patch<Contact>(`/api/contacts/${id}`, data),
  delete: (id: number) => api.delete(`/api/contacts/${id}`),
  sync: (contacts: Array<{ phone: string; name?: string; email?: string; tags?: string[]; list_id?: number; custom_fields?: Record<string, unknown>; opt_in?: boolean }>) =>
    api.post<{ created: number; updated: number; errors: Array<Record<string, unknown>> }>('/api/contacts/sync', { contacts }),
}

// --- Lists
export type ListItem = {
  id: number
  tenant_id: number
  name: string
  created_at: string | null
  updated_at: string | null
  contact_count: number
}

export const listsApi = {
  list: () => api.get<ListItem[]>('/api/lists'),
  get: (id: number) => api.get<ListItem>(`/api/lists/${id}`),
  getContacts: (id: number) => api.get<Contact[]>(`/api/lists/${id}/contacts`),
  create: (data: { name: string }) => api.post<ListItem>('/api/lists', data),
  update: (id: number, data: { name?: string }) => api.patch<ListItem>(`/api/lists/${id}`, data),
  delete: (id: number) => api.delete(`/api/lists/${id}`),
  addContacts: (listId: number, contact_ids: number[]) =>
    api.post<{ added: number; list_id: number }>(`/api/lists/${listId}/contacts`, { contact_ids }),
  removeContacts: (listId: number, contact_ids: number[]) =>
    api.delete<{ removed: number; list_id: number }>(`/api/lists/${listId}/contacts`, { data: { contact_ids } }),
}

// --- Tags
export type TagItem = {
  id: number
  tenant_id: number
  name: string
  created_at: string | null
}

export const tagsApi = {
  list: () => api.get<TagItem[]>('/api/tags'),
  create: (data: { name: string }) => api.post<TagItem>('/api/tags', data),
  update: (id: number, data: { name: string }) => api.patch<TagItem>(`/api/tags/${id}`, data),
  delete: (id: number) => api.delete(`/api/tags/${id}`),
  apply: (tagId: number, contact_ids: number[]) =>
    api.post<{ applied: number; tag_id: number }>(`/api/tags/${tagId}/apply`, { contact_ids }),
}

// --- Campaigns
export type CampaignItem = {
  id: number
  tenant_id: number
  name: string
  type: string
  list_id: number
  tag_filter_include: string[] | null
  tag_filter_exclude: string[] | null
  content: Record<string, unknown>
  use_global_shielding: boolean
  shielding_override: Record<string, unknown> | null
  instance_ids: number[] | null
  status: string
  scheduled_at: string | null
  started_at: string | null
  completed_at: string | null
  created_at: string | null
  updated_at: string | null
}

export const campaignsApi = {
  list: (params?: { status?: string }) => api.get<CampaignItem[]>('/api/campaigns', { params }),
  get: (id: number) => api.get<CampaignItem>(`/api/campaigns/${id}`),
  create: (data: {
    name: string
    type?: string
    list_id: number
    tag_filter_include?: string[] | null
    tag_filter_exclude?: string[] | null
    content?: Record<string, unknown>
    use_global_shielding?: boolean
    shielding_override?: Record<string, unknown> | null
    instance_ids?: number[] | null
    scheduled_at?: string | null
  }) => api.post<CampaignItem>('/api/campaigns', data),
  update: (id: number, data: Partial<CampaignItem>) => api.patch<CampaignItem>(`/api/campaigns/${id}`, data),
  delete: (id: number) => api.delete(`/api/campaigns/${id}`),
}
