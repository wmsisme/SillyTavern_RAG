import { useNavigate } from 'react-router-dom'
import { Button, Result, Spin } from 'antd'
import type { ReactNode } from 'react'
import { useAuth } from '../services/auth'

/**
 * 私有页面的守卫：角色卡 / 世界书是「自己的资料」，没登录就明说，
 * 而不是让接口回 401 之后在页面上弹一堆红字。
 */
export default function RequireLogin({ children }: { children: ReactNode }) {
  const { user, ready } = useAuth()
  const navigate = useNavigate()

  if (!ready) {
    return <div style={{ textAlign: 'center', padding: 48 }}><Spin size="large" /></div>
  }
  if (!user) {
    return (
      <Result
        status="403"
        title="需要登录"
        subTitle="角色卡与世界书是你自己的私人资料，登录后才能查看和管理。"
        extra={<Button type="primary" onClick={() => navigate('/login')}>去登录 / 注册</Button>}
      />
    )
  }
  return <>{children}</>
}
