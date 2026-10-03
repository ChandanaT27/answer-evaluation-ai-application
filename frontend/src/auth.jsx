import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import api from './api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(!!localStorage.getItem('token'))

  useEffect(() => {
    if (!localStorage.getItem('token')) return
    api.get('/auth/me').then((r) => setUser(r.data)).catch(() => localStorage.removeItem('token')).finally(() => setLoading(false))
  }, [])

  const login = useCallback(async (username, password) => {
    const r = await api.post('/auth/login', { username, password })
    localStorage.setItem('token', r.data.token)
    setUser(r.data.user)
    return r.data.user
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('token')
    setUser(null)
  }, [])

  const can = useCallback((p) => !!user?.permissions?.includes(p), [user])

  return <AuthContext.Provider value={{ user, loading, login, logout, can }}>{children}</AuthContext.Provider>
}

export const useAuth = () => useContext(AuthContext)
