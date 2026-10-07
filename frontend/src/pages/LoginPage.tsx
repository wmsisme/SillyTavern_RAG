import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Typography, Form, Input, Button, Card, App, Tabs, Alert, Space } from 'antd'
import { UserOutlined, LockOutlined, SearchOutlined } from '@ant-design/icons'
import { api } from '../services/api'
import { useAuth } from '../services/auth'

const { Title, Text } = Typography

export default function LoginPage() {
  const { message } = App.useApp()
  const { refresh } = useAuth()
  const navigate = useNavigate()
  const [tab, setTab] = useState<'login' | 'register'>('login')
  const [loading, setLoading] = useState(false)
  const [needInvite, setNeedInvite] = useState(false)

  const submit = async (values: any) => {
    setLoading(true)
    try {
      if (tab === 'register') {
        await api.post('/auth/register', {
          username: values.username,
          password: values.password,
          invite_code: values.invite_code || '',
        })
        message.success('注册成功，已自动登录')
      } else {
        await api.post('/auth/login', { username: values.username, password: values.password })
        message.success('登录成功')
      }
      await refresh()
      navigate('/')
    } catch (e: any) {
      // 需要邀请码时后端会明确说；顺手把输入框亮出来
      if (String(e?.message || '').includes('邀请码')) setNeedInvite(true)
      message.error(e?.message || '操作失败')
    } finally {
      setLoading(false)
    }
  }

  const form = (
    <Form layout="vertical" onFinish={submit} size="large">
      <Form.Item name="username" rules={[{ required: true, message: '请输入用户名' }]}>
        <Input prefix={<UserOutlined />} placeholder="用户名" autoComplete="username" />
      </Form.Item>
      {/* 长度校验**只在注册页**加：登录页加会挡住老账号（密码是历史遗留的短密码就登不进来了） */}
      <Form.Item name="password" rules={[
        { required: true, message: '请输入密码' },
        ...(tab === 'register' ? [{ min: 8, message: '密码至少 8 位' }] : []),
      ]}>
        <Input.Password prefix={<LockOutlined />}
                        placeholder={tab === 'register' ? '密码（至少 8 位，别用纯数字）' : '密码'}
                        autoComplete={tab === 'login' ? 'current-password' : 'new-password'} />
      </Form.Item>
      {tab === 'register' && (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
          message="密码无法找回，请设一个自己能记住的"
          description="密码是加密保存的，连管理员也看不到原文，忘了只能重置。"
        />
      )}
      {tab === 'register' && needInvite && (
        <Form.Item name="invite_code">
          <Input placeholder="邀请码" />
        </Form.Item>
      )}
      <Form.Item style={{ marginBottom: 8 }}>
        <Button type="primary" htmlType="submit" loading={loading} block>
          {tab === 'login' ? '登录' : '注册并登录'}
        </Button>
      </Form.Item>
    </Form>
  )

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: '#f5f5f5', padding: 24,
    }}>
      <Card style={{ width: 420 }} variant="borderless">
        <Space direction="vertical" size={4} style={{ marginBottom: 20, width: '100%' }}>
          <Title level={4} style={{ margin: 0 }}>
            <SearchOutlined style={{ marginRight: 8, color: '#1677ff' }} />
            ST 知识库
          </Title>
          <Text type="secondary" style={{ fontSize: 13 }}>
            注册后即可拥有自己的角色卡与世界书库 —— 只有你自己能看到。
          </Text>
        </Space>

        <Tabs
          activeKey={tab}
          onChange={k => setTab(k as 'login' | 'register')}
          items={[
            { key: 'login', label: '登录', children: form },
            { key: 'register', label: '注册', children: form },
          ]}
        />

        <Alert
          type="info"
          showIcon
          style={{ marginTop: 8 }}
          message="知识库搜索与工具箱无需登录"
          description="没有账号也能直接搜索 SillyTavern 文档、使用工具箱；只有角色卡/世界书需要登录。"
        />
      </Card>
    </div>
  )
}
