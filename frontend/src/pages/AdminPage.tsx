import { useCallback, useEffect, useState } from 'react'
import {
  App, Button, Card, Col, Form, Input, InputNumber, Modal, Popconfirm,
  Row, Space, Statistic, Table, Tabs, Tag, Typography,
} from 'antd'
import type { TableColumnsType } from 'antd'
import { ReloadOutlined, StopOutlined, CheckCircleOutlined, CrownOutlined } from '@ant-design/icons'
import { api } from '../services/api'
import { useAuth } from '../services/auth'

interface Overview {
  users_total: number
  users_banned: number
  cards_total: number
  worldbooks_total: number
  queries_today: number
  queries_total: number
  queries_unanswered: number
  ip_bans_active: number
  unanswered_threshold: number
}

interface AdminUser {
  id: number
  username: string
  is_admin: boolean
  is_active: boolean
  created_at?: string | null
  ban_reason: string
  banned_at?: string | null
  sessions: number
  queries: number
  last_query_at?: string | null
}

interface IpBanRow {
  id: number
  ip: string
  reason: string
  created_by: string
  created_at?: string | null
  expires_at?: string | null
  expired: boolean
}

interface ActiveIpRow {
  ip: string
  queries: number
  users: number
  usernames: string
  last_at?: string | null
  banned: boolean
}

interface QueryLogRow {
  id: number
  created_at?: string | null
  ip: string
  user_id?: number | null
  username: string
  kind: string
  query: string
  sources_count: number
  top_score: number
  answered: boolean
  feedback: string
}

/** 后端给的是 ISO 串，直接 toLocaleString 会带 T，统一成看得懂的样子 */
function fmtTime(v?: string | null): string {
  if (!v) return '—'
  const d = new Date(v)
  if (Number.isNaN(d.getTime())) return String(v).slice(0, 19).replace('T', ' ')
  return d.toLocaleString('zh-CN', { hour12: false })
}

const KIND_LABEL: Record<string, string> = {
  search: '检索', ask: '问答', ask_stream: '问答(流式)',
}

export default function AdminPage() {
  const { user, ready } = useAuth()
  const { message } = App.useApp()

  const [overview, setOverview] = useState<Overview | null>(null)
  const [users, setUsers] = useState<AdminUser[]>([])
  const [bans, setBans] = useState<IpBanRow[]>([])
  const [activeIps, setActiveIps] = useState<ActiveIpRow[]>([])
  const [queries, setQueries] = useState<QueryLogRow[]>([])
  const [qTotal, setQTotal] = useState(0)
  const [qPage, setQPage] = useState(1)
  const [onlyUnanswered, setOnlyUnanswered] = useState(false)
  const [loading, setLoading] = useState(false)

  // 封号弹窗 / 封 IP 弹窗
  const [banTarget, setBanTarget] = useState<AdminUser | null>(null)
  const [banForm] = Form.useForm()
  const [ipOpen, setIpOpen] = useState(false)
  const [ipForm] = Form.useForm()

  const loadBase = useCallback(async () => {
    const [ov, us, ipBans, actIp] = await Promise.all([
      api.get<Overview>('/admin/overview'),
      api.get<AdminUser[]>('/admin/users'),
      api.get<IpBanRow[]>('/admin/ip-bans'),
      api.get<ActiveIpRow[]>('/admin/active-ips?days=7'),
    ])
    setOverview(ov); setUsers(us); setBans(ipBans); setActiveIps(actIp)
  }, [])

  const loadQueries = useCallback(async () => {
    const r = await api.get<{ total: number; items: QueryLogRow[] }>(
      `/admin/queries?page=${qPage}&page_size=50&only_unanswered=${onlyUnanswered}`,
    )
    setQueries(r.items); setQTotal(r.total)
  }, [qPage, onlyUnanswered])

  const reload = useCallback(async () => {
    setLoading(true)
    try {
      await Promise.all([loadBase(), loadQueries()])
    } catch (e: any) {
      message.error(e?.message || '加载失败')
    } finally {
      setLoading(false)
    }
  }, [loadBase, loadQueries, message])

  useEffect(() => {
    if (ready && user?.is_admin) reload()
  }, [ready, user, reload])

  // 普通用户直接访问 /admin 时给一句人话，而不是让每个接口回 403
  if (ready && !user?.is_admin) {
    return (
      <Card>
        <Typography.Title level={4}>没有权限</Typography.Title>
        <Typography.Paragraph type="secondary">
          这个页面只有管理员能看。当前账号{user ? `（${user.username}）` : '还没登录'}。
        </Typography.Paragraph>
      </Card>
    )
  }

  // ---------------------------------------------------------------- 操作
  const doBan = async () => {
    const v = await banForm.validateFields()
    try {
      const r = await api.post(`/admin/users/${banTarget!.id}/ban`, { reason: v.reason || '' })
      message.success(r?.message || '已封禁')
      setBanTarget(null); banForm.resetFields()
      await reload()
    } catch (e: any) {
      message.error(e?.message || '操作失败')
    }
  }

  const doUnban = async (u: AdminUser) => {
    try {
      const r = await api.post(`/admin/users/${u.id}/unban`)
      message.success(r?.message || '已解封'); await reload()
    } catch (e: any) { message.error(e?.message || '操作失败') }
  }

  const doMakeAdmin = async (u: AdminUser) => {
    try {
      const r = await api.post(`/admin/users/${u.id}/make-admin`)
      message.success(r?.message || '已设为管理员'); await reload()
    } catch (e: any) { message.error(e?.message || '操作失败') }
  }

  const doBanIp = async () => {
    const v = await ipForm.validateFields()
    try {
      const r = await api.post('/admin/ip-bans', {
        ip: v.ip, reason: v.reason || '', days: v.days || 0,
      })
      message.success(r?.message || '已封禁')
      setIpOpen(false); ipForm.resetFields()
      await reload()
    } catch (e: any) { message.error(e?.message || '操作失败') }
  }

  const doUnbanIp = async (row: IpBanRow | ActiveIpRow) => {
    const id = (row as IpBanRow).id
    const key = id ?? (row as ActiveIpRow).ip
    try {
      if (id) {
        const r = await api.delete(`/admin/ip-bans/${id}`)
        message.success(r?.message || '已解封')
      } else {
        // 活跃 IP 表里还没进黑名单的，这里就不该出现解封按钮
        message.info(`${key} 不在黑名单里`)
      }
      await reload()
    } catch (e: any) { message.error(e?.message || '操作失败') }
  }

  // ---------------------------------------------------------------- 表格列
  const userCols: TableColumnsType<AdminUser> = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    {
      title: '用户名', dataIndex: 'username',
      render: (v: string, r) => (
        <Space size={4}>
          <span>{v}</span>
          {r.is_admin && <Tag color="gold" icon={<CrownOutlined />}>管理员</Tag>}
        </Space>
      ),
    },
    {
      title: '状态', dataIndex: 'is_active', width: 160,
      render: (v: boolean, r) => (v
        ? <Tag color="green">正常</Tag>
        : <Space size={4}><Tag color="red">已封禁</Tag>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              {r.ban_reason || '未填原因'}
            </Typography.Text>
          </Space>),
    },
    { title: '在线会话', dataIndex: 'sessions', width: 90 },
    { title: '提问数', dataIndex: 'queries', width: 80 },
    { title: '最后提问', dataIndex: 'last_query_at', width: 170, render: (v: string) => fmtTime(v) },
    { title: '注册时间', dataIndex: 'created_at', width: 170, render: (v: string) => fmtTime(v) },
    {
      title: '操作', key: 'ops', width: 200,
      render: (_: unknown, r) => (
        <Space size={4}>
          {r.is_active ? (
            <Button size="small" danger icon={<StopOutlined />}
                    disabled={r.id === user?.id}
                    title={r.id === user?.id ? '不能封自己' : undefined}
                    onClick={() => { setBanTarget(r); banForm.resetFields() }}>
              封禁
            </Button>
          ) : (
            <Popconfirm title={`解封 ${r.username}？`} onConfirm={() => doUnban(r)}>
              <Button size="small" type="primary" ghost icon={<CheckCircleOutlined />}>解封</Button>
            </Popconfirm>
          )}
          {!r.is_admin && (
            <Popconfirm title={`把 ${r.username} 设为管理员？`} onConfirm={() => doMakeAdmin(r)}>
              <Button size="small">提为管理员</Button>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ]

  const banCols: TableColumnsType<IpBanRow> = [
    { title: 'IP', dataIndex: 'ip', width: 180 },
    { title: '原因', dataIndex: 'reason', ellipsis: true, render: (v: string) => v || '—' },
    { title: '由谁封', dataIndex: 'created_by', width: 100 },
    { title: '封禁时间', dataIndex: 'created_at', width: 170, render: (v: string) => fmtTime(v) },
    {
      title: '到期', dataIndex: 'expires_at', width: 170,
      render: (v: string, r) => (r.expired ? <Tag>已过期</Tag> : (v ? fmtTime(v) : <Tag color="red">永久</Tag>)),
    },
    {
      title: '操作', key: 'ops', width: 100,
      render: (_: unknown, r) => (
        <Popconfirm title={`解封 ${r.ip}？`} onConfirm={() => doUnbanIp(r)}>
          <Button size="small">解封</Button>
        </Popconfirm>
      ),
    },
  ]

  const activeIpCols: TableColumnsType<ActiveIpRow> = [
    { title: 'IP', dataIndex: 'ip', width: 180,
      render: (v: string, r) => <Space size={4}><span>{v}</span>{r.banned && <Tag color="red">已封</Tag>}</Space> },
    { title: '提问数', dataIndex: 'queries', width: 90, sorter: (a, b) => a.queries - b.queries },
    {
      title: '该 IP 上的账号数', dataIndex: 'users', width: 180,
      render: (v: number, r) => (v > 1
        ? <Space size={4}><Tag color="orange">{v} 个</Tag>
            <Typography.Text type="secondary" style={{ fontSize: 12 }} ellipsis>{r.usernames}</Typography.Text>
          </Space>
        : <span>{v} 个</span>),
    },
    { title: '最近一次', dataIndex: 'last_at', width: 170, render: (v: string) => fmtTime(v) },
    {
      title: '操作', key: 'ops', width: 90,
      render: (_: unknown, r) => (r.banned
        ? <Typography.Text type="secondary">已在黑名单</Typography.Text>
        : <Button size="small" danger onClick={() => { setIpOpen(true); ipForm.setFieldsValue({ ip: r.ip }) }}>
            封这个 IP
          </Button>),
    },
  ]

  const queryCols: TableColumnsType<QueryLogRow> = [
    { title: '时间', dataIndex: 'created_at', width: 160, render: (v: string) => fmtTime(v) },
    { title: '提问人', dataIndex: 'username', width: 110,
      render: (v: string, r) => v || <Typography.Text type="secondary">未登录</Typography.Text> },
    { title: 'IP', dataIndex: 'ip', width: 140 },
    { title: '方式', dataIndex: 'kind', width: 90, render: (v: string) => KIND_LABEL[v] || v },
    { title: '问题', dataIndex: 'query', ellipsis: true },
    { title: '来源数', dataIndex: 'sources_count', width: 80 },
    { title: '最高相关度', dataIndex: 'top_score', width: 100,
      render: (v: number) => (v ? v.toFixed(3) : '—') },
    {
      title: '结果', dataIndex: 'answered', width: 120,
      render: (v: boolean, r) => (v
        ? <Tag color="green">已解答</Tag>
        : <Tag color="orange">{r.feedback === 'unsolved' ? '用户说没解决' : '疑似未解答'}</Tag>),
    },
  ]

  const tabs = [
    {
      key: 'users', label: `用户管理（${users.length}）`,
      children: (
        <Table<AdminUser> rowKey="id" size="small" loading={loading}
                          columns={userCols} dataSource={users} pagination={false} />
      ),
    },
    {
      key: 'ips', label: `IP 管理（黑名单 ${bans.length}）`,
      children: (
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <div>
            <Space style={{ marginBottom: 8 }}>
              <Typography.Text strong>最近 7 天活跃 IP</Typography.Text>
              <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                同一 IP 上出现多个账号 → 很可能是共享账号，点右侧按钮可直接封该 IP
              </Typography.Text>
            </Space>
            <Table<ActiveIpRow> rowKey="ip" size="small" loading={loading}
                               columns={activeIpCols} dataSource={activeIps} pagination={false} />
          </div>
          <div>
            <Space style={{ marginBottom: 8 }}>
              <Typography.Text strong>IP 黑名单</Typography.Text>
              <Button size="small" danger onClick={() => { setIpOpen(true); ipForm.resetFields() }}>
                手动加一个
              </Button>
            </Space>
            <Table<IpBanRow> rowKey="id" size="small" loading={loading}
                            columns={banCols} dataSource={bans} pagination={false} />
          </div>
        </Space>
      ),
    },
    {
      key: 'queries', label: `提问记录（未解答 ${overview?.queries_unanswered ?? 0}）`,
      children: (
        <Space direction="vertical" style={{ width: '100%' }}>
          <Space>
            <Button
              type={onlyUnanswered ? 'primary' : 'default'}
              onClick={() => { setOnlyUnanswered(!onlyUnanswered); setQPage(1) }}
            >
              只看没答上来的
            </Button>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              判定口径：一条来源都没召回，或最高相关度低于 {(overview?.unanswered_threshold ?? 0.45)}
              ；用户点过「没解决」的一律计入
            </Typography.Text>
          </Space>
          <Table<QueryLogRow> rowKey="id" size="small" loading={loading}
                             columns={queryCols} dataSource={queries}
                             pagination={{
                               current: qPage, pageSize: 50, total: qTotal,
                               onChange: (p) => setQPage(p), showSizeChanger: false,
                             }} />
        </Space>
      ),
    },
  ]

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Row gutter={16}>
        <Col span={4}><Card size="small"><Statistic title="用户" value={overview?.users_total ?? 0}
          suffix={overview?.users_banned ? <Typography.Text type="danger" style={{ fontSize: 12 }}>封 {overview.users_banned}</Typography.Text> : null} /></Card></Col>
        <Col span={4}><Card size="small"><Statistic title="今天提问" value={overview?.queries_today ?? 0} /></Card></Col>
        <Col span={4}><Card size="small"><Statistic title="累计提问" value={overview?.queries_total ?? 0} /></Card></Col>
        <Col span={4}><Card size="small"><Statistic title="没答上来" value={overview?.queries_unanswered ?? 0}
          valueStyle={{ color: (overview?.queries_unanswered ?? 0) > 0 ? '#fa8c16' : undefined }} /></Card></Col>
        <Col span={4}><Card size="small"><Statistic title="角色卡" value={overview?.cards_total ?? 0} /></Card></Col>
        <Col span={4}><Card size="small"><Statistic title="IP 黑名单" value={overview?.ip_bans_active ?? 0} /></Card></Col>
      </Row>

      <Space>
        <Button icon={<ReloadOutlined />} onClick={reload} loading={loading}>刷新</Button>
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          没答上来的问题攒在这里，就是「下次该往知识库补什么」的清单
        </Typography.Text>
      </Space>

      <Tabs items={tabs} />

      <Modal
        title={banTarget ? `封禁账号：${banTarget.username}` : '封禁账号'}
        open={!!banTarget}
        onCancel={() => { setBanTarget(null); banForm.resetFields() }}
        onOk={doBan}
        okText="确认封禁"
        okButtonProps={{ danger: true }}
      >
        <Typography.Paragraph type="secondary" style={{ fontSize: 12 }}>
          封禁后他会立刻被踢下线，且无法再用原密码登录。解封后可恢复。
        </Typography.Paragraph>
        <Form form={banForm} layout="vertical">
          <Form.Item name="reason" label="原因（会记在后台，方便日后回溯）">
            <Input.TextArea rows={3} placeholder="例：用共享账号发布违规内容"
                            maxLength={200} showCount />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="封禁 IP"
        open={ipOpen}
        onCancel={() => { setIpOpen(false); ipForm.resetFields() }}
        onOk={doBanIp}
        okText="确认封禁"
        okButtonProps={{ danger: true }}
      >
        <Typography.Paragraph type="secondary" style={{ fontSize: 12 }}>
          注意：本机地址（127.0.0.1 / ::1）封不掉，这是防止把自己锁在门外。
          如果你前面挂了反向代理且没设 TRUST_PROXY=1，所有请求看起来都来自 127.0.0.1 ——
          这种情况下封 IP 起不到作用，得先把真实 IP 传进来。
        </Typography.Paragraph>
        <Form form={ipForm} layout="vertical">
          <Form.Item name="ip" label="IP 地址"
                     rules={[{ required: true, message: '请输入要封的 IP' }]}>
            <Input placeholder="例如 203.0.113.66" />
          </Form.Item>
          <Form.Item name="reason" label="原因">
            <Input placeholder="例：批量刷检索" maxLength={200} />
          </Form.Item>
          <Form.Item name="days" label="封多少天（0 = 永久）" initialValue={0}>
            <InputNumber min={0} max={3650} style={{ width: 160 }} />
          </Form.Item>
        </Form>
      </Modal>
    </Space>
  )
}
