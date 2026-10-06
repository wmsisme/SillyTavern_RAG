import { createContext, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { api, setUnauthorizedHandler } from './api'

/** 当前登录用户。形态与后端 schemas/user.py 的 UserResponse 对齐 */
export interface AuthUser {
  id: number
  username: string
  is_admin: boolean
  created_at: string
}

interface AuthCtxValue {
  user: AuthUser | null
  /** 首次 /auth/me 是否已经问过（没问完之前不要渲染"需要登录"的空态，会闪） */
  ready: boolean
  refresh: () => Promise<void>
  setUser: (u: AuthUser | null) => void
}

const AuthCtx = createContext<AuthCtxValue>({
  user: null, ready: false, refresh: async () => {}, setUser: () => {},
})

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [ready, setReady] = useState(false)

  const refresh = async () => {
    try {
      setUser(await api.get<AuthUser>('/auth/me'))
    } catch {
      setUser(null)   // 401 = 没登录，属正常情况，不当错误弹
    }
  }

  useEffect(() => {
    // 任何接口回 401（比如令牌过期/被踢），前端立刻回到未登录态
    setUnauthorizedHandler(() => setUser(null))
    refresh().finally(() => setReady(true))
  }, [])

  return (
    <AuthCtx.Provider value={{ user, ready, refresh, setUser }}>
      {children}
    </AuthCtx.Provider>
  )
}

export const useAuth = () => useContext(AuthCtx)
