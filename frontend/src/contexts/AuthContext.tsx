import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { authApi, type User, type Tenant } from '../services/api'

type AuthState = {
  token: string | null
  user: User | null
  tenant: Tenant | null
  loading: boolean
}

type AuthContextValue = AuthState & {
  login: (email: string, password: string) => Promise<void>
  register: (data: { email: string; password: string; name?: string; tenant_name: string }) => Promise<void>
  logout: () => void
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

const TOKEN_KEY = 'massflow_token'
const USER_KEY = 'massflow_user'

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY))
  const [user, setUser] = useState<User | null>(() => {
    try {
      const s = localStorage.getItem(USER_KEY)
      return s ? JSON.parse(s) : null
    } catch {
      return null
    }
  })
  const [tenant, setTenant] = useState<Tenant | null>(null)
  const [loading, setLoading] = useState(true)

  const refreshUser = useCallback(async () => {
    if (!token) return
    try {
      const [meRes, tenantRes] = await Promise.all([authApi.me(), authApi.tenant()])
      setUser(meRes.data)
      setTenant(tenantRes.data)
      localStorage.setItem(USER_KEY, JSON.stringify(meRes.data))
    } catch {
      setToken(null)
      setUser(null)
      setTenant(null)
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(USER_KEY)
    }
  }, [token])

  useEffect(() => {
    if (!token) {
      setUser(null)
      setTenant(null)
      setLoading(false)
      return
    }
    refreshUser().finally(() => setLoading(false))
  }, [token, refreshUser])

  useEffect(() => {
    const onStorage = () => {
      const t = localStorage.getItem(TOKEN_KEY)
      if (!t) setToken(null)
    }
    window.addEventListener('storage', onStorage)
    return () => window.removeEventListener('storage', onStorage)
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const { data } = await authApi.login(email, password)
    localStorage.setItem(TOKEN_KEY, data.access_token)
    setToken(data.access_token)
  }, [])

  const register = useCallback(
    async (data: { email: string; password: string; name?: string; tenant_name: string }) => {
      const { data: tokenData } = await authApi.register(data)
      localStorage.setItem(TOKEN_KEY, tokenData.access_token)
      setToken(tokenData.access_token)
    },
    []
  )

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
    setToken(null)
    setUser(null)
    setTenant(null)
  }, [])

  const value: AuthContextValue = {
    token,
    user,
    tenant,
    loading,
    login,
    register,
    logout,
    refreshUser,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
