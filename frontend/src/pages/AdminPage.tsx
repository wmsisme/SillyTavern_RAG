import { useCallback, useEffect, useState } from 'react'
import {
  App, Button, Card, Col, Form, Input, InputNumber, Modal, Popconfirm,
  Row, Space, Statistic, Table, Tabs, Tag, Tooltip, Typography,
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
  feedback_total: number
  feedback_unhandled: number
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
  feedback: string            // "" / solved / unsolved / irrelevant
  feedback_reason: string
  feedback_at?: string | null
  sources_digest: string      // 当时的检索结果摘要（JSON：前 5 条的 source + score）
  marked: boolean             // 站长勾选「这条要拿去更新知识库」
  marked_at?: string | null
  repeat_count: number        // 同一 IP 重复问同一个问题的次数（>1 时界面上会标出来）
}

interface FeedbackRow {
  id: number
  created_at?: string | null
  user_id?: number | null
  username: string
  ip: string
  category: string
  content: string
  page: string
  handled: boolean
  handled_at?: string | null
  handled_by: string
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
  const [feedbacks, setFeedbacks] = useState<FeedbackRow[]>([])
  const [fbTotal, setFbTotal] = useState(0)
  const [fbUnhandled, setFbUnhandled] = useState(0)
  const [fbOnlyUnhandled, setFbOnlyUnhandled] = useState(false)
  const [fbPage, setFbPage] = useState(1)
  const [qPage, setQPage] = useState(1)
  const [filter, setFilter] = useState<'all' | 'unanswered' | 'irrelevant' | 'unsolved' | 'marked'>('all')
  const [picked, setPicked] = useState<number[]>([])   // 勾选的提问记录 id（待更新清单）
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
    const q = new URLSearchParams({ page: String(qPage), page_size: '50' })
    if (filter === 'unanswered') q.set('only_unanswered', 'true')
    if (filter === 'irrelevant') q.set('feedback', 'irrelevant')
    if (filter === 'unsolved') q.set('feedback', 'unsolved')
    if (filter === 'marked') q.set('marked_only', 'true')
    const r = await api.get<{ total: number; items: QueryLogRow[] }>(`/admin/queries?${q}`)
    setQueries(r.items); setQTotal(r.total)
  }, [qPage, filter])

  const loadFeedback = useCallback(async () => {
    const q = new URLSearchParams({ page: String(fbPage), page_size: '50' })
    if (fbOnlyUnhandled) q.set('only_unhandled', 'true')
    const r = await api.get<{ total: number; unhandled: number; items: FeedbackRow[] }>(
      `/admin/feedback?${q}`)
    setFeedbacks(r.items); setFbTotal(r.total); setFbUnhandled(r.unhandled)
  }, [fbPage, fbOnlyUnhandled])

  const reload = useCallback(async () => {
    setLoading(true)
    try {
      await Promise.all([loadBase(), loadQueries(), loadFeedback()])
    } catch (e: any) {
      message.error(e?.message || '加载失败')
    } finally {
      setLoading(false)
    }
  }, [loadBase, loadQueries, loadFeedback, message])

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

  const doHandleFeedback = async (row: FeedbackRow, handled: boolean) => {
    try {
      const r = await api.post(`/admin/feedback/${row.id}/handle?handled=${handled}`)
      message.success(r?.message || '已更新')
      await reload()
    } catch (e: any) { message.error(e?.message || '操作失败') }
  }

  const doDeleteFeedback = async (row: FeedbackRow) => {
    try {
      const r = await api.delete(`/admin/feedback/${row.id}`)
      message.success(r?.message || '已删除')
      await reload()
    } catch (e: any) { message.error(e?.message || '操作失败') }
  }

  // 待更新清单：**勾选权留在人手上** —— 用户随便问一句就自动灌进知识库会把它污染掉，
  // 所以后台只做标记，真正补什么内容等勾完再定（导出的清单可以直接拿来用）。
  const doMark = async (marked: boolean) => {
    if (picked.length === 0) { message.info('先勾选几条'); return }
    try {
      const r = await api.post('/admin/queries/mark', { ids: picked, marked })
      message.success(r?.message || '已更新')
      setPicked([])
      await reload()
    } catch (e: any) { message.error(e?.message || '操作失败') }
  }

  const exportQueue = () => {
    // 同源请求会带上会话 Cookie，直接开新页下载
    window.open('/api/admin/queries/export?marked_only=true', '_blank')
  }

  const doDeletePicked = async () => {
    try {
      const r = await api.post('/admin/queries/delete', { ids: picked })
      message.success(r?.message || '已删除')
      setPicked([])
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
    {
      title: '问题', dataIndex: 'query', ellipsis: true,
      render: (v: string, r) => (
        <Space size={4}>
          <span>{v}</span>
          {(r.repeat_count ?? 1) > 1 && (
            <Typography.Text type="secondary" style={{ fontSize: 12 }} title="同一 IP 在短时间内重复问了这个">
              （重复 {r.repeat_count} 次）
            </Typography.Text>
          )}
        </Space>
      ),
    },
    { title: '来源数', dataIndex: 'sources_count', width: 80 },
    { title: '最高相关度', dataIndex: 'top_score', width: 100,
      render: (v: number) => (v ? v.toFixed(3) : '—') },
    {
      title: '结果', dataIndex: 'answered', width: 110,
      render: (v: boolean, r) => (v
        ? <Tag color="green">已解答</Tag>
        : <Tag color="orange">{r.feedback === 'solved' ? '?' : '疑似未解答'}</Tag>),
    },
    {
      // 注意与左边复选框的区别：复选框是「本次要操作哪些」，这一列是「已经加入待更新清单」
      title: '待更新', dataIndex: 'marked', width: 90,
      render: (v: boolean) => (v ? <Tag color="blue">已加入</Tag> : '—'),
    },
    {
      title: '用户反馈', key: 'fb', width: 220,
      render: (_: unknown, r) => {
        if (!r.feedback) return <Typography.Text type="secondary">—</Typography.Text>
        const meta: Record<string, { color: string; text: string }> = {
          solved: { color: 'green', text: '👍 有帮助' },
          unsolved: { color: 'orange', text: '👎 没解决' },
          irrelevant: { color: 'red', text: '🚫 内容不相关' },
        }
        const m = meta[r.feedback] || { color: 'default', text: r.feedback }
        let digest: { source?: string; score?: number }[] = []
        try { digest = JSON.parse(r.sources_digest || '[]') } catch { digest = [] }
        return (
          <Space direction="vertical" size={2}>
            <Tag color={m.color}>{m.text}</Tag>
            {r.feedback_reason && (
              <Typography.Text style={{ fontSize: 12 }}>{r.feedback_reason}</Typography.Text>
            )}
            {digest.length > 0 && (
              <Tooltip title={
                <div>
                  <div style={{ marginBottom: 4 }}>用户点反馈时，系统给出的是：</div>
                  {digest.map((d, i) => (
                    <div key={i}>{i + 1}. {d.source}（{Number(d.score || 0).toFixed(3)}）</div>
                  ))}
                </div>
              }>
                <Typography.Text type="secondary" style={{ fontSize: 12, cursor: 'help' }}>
                  当时给了 {digest.length} 条来源 ▸
                </Typography.Text>
              </Tooltip>
            )}
          </Space>
        )
      },
    },
  ]

  const feedbackCols: TableColumnsType<FeedbackRow> = [
    { title: '时间', dataIndex: 'created_at', width: 160, render: (v: string) => fmtTime(v) },
    {
      title: '用户', dataIndex: 'username', width: 110,
      render: (v: string) => v || <Typography.Text type="secondary">—</Typography.Text>,
    },
    { title: '分类', dataIndex: 'category', width: 80, render: (v: string) => <Tag>{v}</Tag> },
    { title: '内容', dataIndex: 'content', ellipsis: true },
    {
      title: '来自页面', dataIndex: 'page', width: 140,
      render: (v: string) => (v ? <Typography.Text code>{v}</Typography.Text> : '—'),
    },
    {
      title: '状态', dataIndex: 'handled', width: 110,
      render: (v: boolean) => (v ? <Tag color="green">已处理</Tag> : <Tag color="orange">待处理</Tag>),
    },
    {
      title: '操作', key: 'ops', width: 180,
      render: (_: unknown, r) => (
        <Space size={4}>
          <Button size="small" onClick={() => doHandleFeedback(r, !r.handled)}>
            {r.handled ? '改回待处理' : '标记已处理'}
          </Button>
          <Popconfirm title="删掉这条反馈？" onConfirm={() => doDeleteFeedback(r)}>
            <Button size="small" danger>删除</Button>
          </Popconfirm>
        </Space>
      ),
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
      key: 'feedback', label: `用户反馈（待处理 ${fbUnhandled}）`,
      children: (
        <Space direction="vertical" style={{ width: '100%' }}>
          <Space wrap>
            <Button
              type={fbOnlyUnhandled ? 'primary' : 'default'}
              onClick={() => { setFbOnlyUnhandled(!fbOnlyUnhandled); setFbPage(1) }}
            >
              只看待处理的
            </Button>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              用户从顶部栏「反馈」按钮主动提交的意见（建议 / 体验 / 故障）——
              这类信息日志里不会有，是他们开口才拿得到的
            </Typography.Text>
          </Space>
          <Table<FeedbackRow> rowKey="id" size="small" loading={loading}
                             columns={feedbackCols} dataSource={feedbacks}
                             pagination={{
                               current: fbPage, pageSize: 50, total: fbTotal,
                               onChange: (p) => setFbPage(p), showSizeChanger: false,
                             }} />
        </Space>
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
          <Space wrap>
            {([
              ['all', '全部'],
              ['unanswered', '只看没答上来的'],
              ['irrelevant', '只看「内容不相关」'],
              ['unsolved', '只看「没解决」'],
              ['marked', '只看待更新'],
            ] as const).map(([k, label]) => (
              <Button key={k} type={filter === k ? 'primary' : 'default'}
                      onClick={() => { setFilter(k); setQPage(1) }}>
                {label}
              </Button>
            ))}
            <Button type="primary" ghost disabled={picked.length === 0}
                    onClick={() => doMark(true)}>
              加入待更新{picked.length ? `（${picked.length}）` : ''}
            </Button>
            <Button disabled={picked.length === 0} onClick={() => doMark(false)}>移出</Button>
            <Button onClick={exportQueue}>导出清单</Button>
            <Popconfirm
              title={`删掉选中的 ${picked.length} 条记录？删了就没了`}
              disabled={picked.length === 0}
              onConfirm={doDeletePicked}
            >
              <Button danger disabled={picked.length === 0}>删除选中</Button>
            </Popconfirm>
          </Space>
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            自动判定：一条来源都没召回、或最高相关度低于 {overview?.unanswered_threshold ?? 0.45}；
            用户点过「没解决 / 内容不相关」的一律计入。
            <br />
            <b>待更新清单由你勾选</b>：勾中的条目点「导出清单」拿到 Markdown，
            补进知识库后再重建索引即可 —— **刻意不做自动灌库**，用户随口一问就写进知识库会污染它。
            表格里「待更新」列显示的是已加入的，「复选框」是本次要操作的，两者不一样。
          </Typography.Text>
          <Table<QueryLogRow> rowKey="id" size="small" loading={loading}
                             columns={queryCols} dataSource={queries}
                             rowSelection={{
                               selectedRowKeys: picked,
                               onChange: (keys) => setPicked(keys as number[]),
                             }}
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
        <Col span={4}>
          <Card size="small">
            <Statistic title="待处理反馈" value={overview?.feedback_unhandled ?? 0}
                       valueStyle={{ color: (overview?.feedback_unhandled ?? 0) > 0 ? '#fa8c16' : undefined }} />
          </Card>
        </Col>
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
