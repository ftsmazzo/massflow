/**
 * Cliente HTTP para a MassFlow API.
 * Em dev: proxy /api -> localhost:8000. Em produção: mesma origem ou VITE_API_URL.
 */
import axios, { type AxiosError } from 'axios'

/** Extrai mensagem de erro da resposta da API (FastAPI: detail string ou array de validação). */
export function getApiErrorMessage(err: unknown, fallback = 'Ocorreu um erro.'): string {
  if (!err || typeof err !== 'object' || !('response' in err)) {
    return 'Não foi possível conectar ao servidor. Em produção, verifique se a URL da API (VITE_API_URL) está correta.'
  }
  const response = (err as AxiosError<{ detail?: string | Array<{ msg?: string; loc?: unknown }> }>).response
  const detail = response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const messages = detail.map((d) => (typeof d === 'object' && d && 'msg' in d ? d.msg : String(d)))
    return messages.filter(Boolean).join(' ') || fallback
  }
  if (response?.status) return `Erro ${response.status}. ${fallback}`
  return fallback
}

const baseURL = (import.meta.env.VITE_API_URL ?? '').replace(/\/+$/, '')

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
  status: (id: number) => api.get<{ instance: string; connection_state: unknown }>(`/api/instances/${id}/status`),
}
