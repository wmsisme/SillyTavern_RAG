import { useEffect, useState } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Layout, Menu, Button, Dropdown, App, theme, Modal, Form, Input, Badge } from 'antd'
import {
  HomeOutlined,
  UserOutlined,
  BookOutlined,
  ToolOutlined,
  SearchOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  LogoutOutlined,
  KeyOutlined,
  ApiOutlined,
  SafetyOutlined,
} from '@ant-design/icons'
import UpdateNotice from '../components/UpdateNotice'
import LLMSettingsModal from '../components/LLMSettingsModal'
import { api } from '../services/api'
import { useAuth } from '../services/auth'
import { isLLMConfigured, setMissingKeyHandler } from '../services/llm'

const { Header, Sider, Content } = Layout

const baseMenuItems = [
  { key: '/', icon: <HomeOutlined />, label: '首页搜索' },
  { key: '/cards', icon: <UserOutlined />, label: '角色卡管理' },
  { key: '/worldbooks', icon: <BookOutlined />, label: '世界书管理' },
  { key: '/toolbox', icon: <ToolOutlined />, label: '工具箱' },
]

// 后台管理只在「已登录 + 是管理员」时出现 —— 普通用户看不见这个入口，
// 也就不会点进去撞一屏 403（后端那几个接口本来也只放给管理员）。
const adminMenuItem = { key: '/admin', icon: <SafetyOutlined />, label: '后台管理' }

export default function MainLayout() {
  const [collapsed, setCollapsed] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const { message } = App.useApp()
  const { user, setUser } = useAuth()
  const { token } = theme.useToken()

  const menuItems = user?.is_admin ? [...baseMenuItems, adminMenuItem] : baseMenuItems
  const selectedKey = '/' + location.pathname.split('/')[1]

  const handleLogout = async () => {
    try {
      await api.post('/auth/logout')
    } catch {
      /* 就算接口失败也要把前端状态清掉，否则页面会卡在"看着已登录"的假象里 */
    }
    setUser(null)
    message.success('已退出登录')
    navigate('/')
  }

  // 改密码：后端会顺手踢掉所有旧会话，所以改完必须重新登录（这里也照做，别留假登录态）
  const [pwdOpen, setPwdOpen] = useState(false)
  const [pwdSaving, setPwdSaving] = useState(false)
  const [pwdForm] = Form.useForm()

  // API 设置（BYOK）：没配 key 时右上角亮个红点；任何地方撞到"没 key"都直接弹这个框
  const [llmOpen, setLlmOpen] = useState(false)
  const [llmReady, setLlmReady] = useState(isLLMConfigured())

  useEffect(() => {
    let alive = true
    // 红点判断要看**两处**：本机 localStorage、以及登录用户存在账号里的配置
    const refresh = () => {
      if (isLLMConfigured()) { setLlmReady(true); return }
      if (!user) { setLlmReady(false); return }
      api.get('/llm/settings')
        .then(d => { if (alive) setLlmReady(!!d?.configured && d?.decryptable !== false) })
        .catch(() => { if (alive) setLlmReady(false) })
    }
    refresh()
    window.addEventListener('llm-settings-changed', refresh)
    setMissingKeyHandler(() => setLlmOpen(true))
    return () => {
      alive = false
      window.removeEventListener('llm-settings-changed', refresh)
      setMissingKeyHandler(null)
    }
  }, [user])

  const handleChangePassword = async (values: any) => {
    setPwdSaving(true)
    try {
      await api.post('/auth/password', {
        old_password: values.old_password,
        new_password: values.new_password,
      })
      setPwdOpen(false)
      pwdForm.resetFields()
      setUser(null)
      message.success('密码已修改，请用新密码重新登录')
      navigate('/login')
    } catch (e: any) {
      message.error(e?.message || '修改失败')
    } finally {
      setPwdSaving(false)
    }
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        trigger={null}
        collapsible
        collapsed={collapsed}
        style={{ background: token.colorBgContainer }}
      >
        <div style={{
          height: 64,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          borderBottom: `1px solid ${token.colorBorderSecondary}`,
        }}>
          <SearchOutlined style={{ fontSize: 24, color: token.colorPrimary }} />
          {!collapsed && (
            <span style={{ marginLeft: 12, fontSize: 16, fontWeight: 600, whiteSpace: 'nowrap' }}>
              ST 知识库
            </span>
          )}
        </div>
        <Menu
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          style={{ borderInlineEnd: 'none' }}
        />
      </Sider>
      <Layout>
        <Header style={{
          padding: '0 24px',
          background: token.colorBgContainer,
          display: 'flex',
          alignItems: 'center',
          borderBottom: `1px solid ${token.colorBorderSecondary}`,
        }}>
          <Button
            type="text"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setCollapsed(!collapsed)}
          />
          <span style={{ marginLeft: 16, fontSize: 18, fontWeight: 500 }}>
            {menuItems.find(item => item.key === selectedKey)?.label || 'SillyTavern RAG 知识库'}
          </span>
          <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 12 }}>
            {/* 文档更新是管理动作（/api/update/run 只放给管理员）：普通用户不该看见这个入口，
                否则点了「立即更新」只会拿到 403 */}
            {user?.is_admin && <UpdateNotice />}
            {/* BYOK 入口：没配 key 时亮红点 —— AI 功能全靠它，别让用户自己找 */}
            <Badge dot={!llmReady} offset={[-2, 4]}>
              <Button
                type="text"
                icon={<ApiOutlined />}
                onClick={() => setLlmOpen(true)}
                title={llmReady ? '已配置你自己的 API Key' : '还没配置 API Key：AI 问答与生成需要它'}
              >
                API 设置
              </Button>
            </Badge>
            {user ? (
              <Dropdown
                menu={{
                  items: [
                    { key: 'password', icon: <KeyOutlined />, label: '修改密码' },
                    { key: 'logout', icon: <LogoutOutlined />, label: '退出登录' },
                  ],
                  onClick: ({ key }) => {
                    if (key === 'logout') handleLogout()
                    if (key === 'password') setPwdOpen(true)
                  },
                }}
              >
                <Button type="text">
                  <UserOutlined style={{ marginRight: 6 }} />
                  {user.username}{user.is_admin ? '（管理员）' : ''}
                </Button>
              </Dropdown>
            ) : (
              <Button type="primary" size="small" onClick={() => navigate('/login')}>
                登录 / 注册
              </Button>
            )}
          </div>
        </Header>
        <Content style={{
          margin: 24,
          padding: 24,
          background: token.colorBgContainer,
          borderRadius: token.borderRadiusLG,
          overflow: 'auto',
        }}>
          <Outlet />
        </Content>
      </Layout>

      <Modal
        title="修改密码"
        open={pwdOpen}
        onCancel={() => { setPwdOpen(false); pwdForm.resetFields() }}
        onOk={() => pwdForm.submit()}
        confirmLoading={pwdSaving}
        okText="确认修改"
      >
        <Form form={pwdForm} layout="vertical" onFinish={handleChangePassword}>
          <Form.Item name="old_password" label="当前密码"
                     rules={[{ required: true, message: '请输入当前密码' }]}>
            <Input.Password autoComplete="current-password" />
          </Form.Item>
          <Form.Item name="new_password" label="新密码（至少 6 位）"
                     rules={[{ required: true, min: 6, message: '新密码至少 6 位' }]}>
            <Input.Password autoComplete="new-password" />
          </Form.Item>
          <Form.Item name="confirm" label="再输一次新密码" dependencies={['new_password']}
                     rules={[
                       { required: true, message: '请再输一次' },
                       ({ getFieldValue }) => ({
                         validator: (_rule, value) => (value === getFieldValue('new_password')
                           ? Promise.resolve()
                           : Promise.reject(new Error('两次输入不一致'))),
                       }),
                     ]}>
            <Input.Password autoComplete="new-password" />
          </Form.Item>
        </Form>
      </Modal>
      <LLMSettingsModal open={llmOpen} onClose={() => setLlmOpen(false)} />
    </Layout>
  )
}
