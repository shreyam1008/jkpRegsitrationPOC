import { createContext, useContext, useState, useCallback, type ReactNode } from 'react'

interface User {
  username: string
  role: 'admin'
}

interface AuthContext {
  user: User | null
  login: (username: string, password: string) => boolean
  logout: () => void
}

const AuthCtx = createContext<AuthContext | null>(null)

const STORAGE_KEY = 'jkp_auth'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(() => {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (!stored) return null
    try { return JSON.parse(stored) as User } catch { return null }
  })

  const login = useCallback((username: string, password: string): boolean => {
    if (username === 'admin' && password === 'admin123') {
      const u: User = { username: 'admin', role: 'admin' }
      setUser(u)
      localStorage.setItem(STORAGE_KEY, JSON.stringify(u))
      return true
    }
    return false
  }, [])

  const logout = useCallback(() => {
    setUser(null)
    localStorage.removeItem(STORAGE_KEY)
  }, [])

  return <AuthCtx value={{ user, login, logout }}>{children}</AuthCtx>
}

export function useAuth(): AuthContext {
  const ctx = useContext(AuthCtx)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
