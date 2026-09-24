import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Typography, Table, Button, Input, Select, Switch, Space, Tag,
  Card, message, Row, Col, Image, Tooltip, Popconfirm,
} from 'antd'
import {
  PlusOutlined, UserOutlined, SearchOutlined,
  ReloadOutlined, EditOutlined, DeleteOutlined,
} from '@ant-design/icons'
import { api } from '../services/api'

const { Title } = Typography

const TAG_OPTIONS = [
  "RPG", "日常聊天", "科幻", "奇幻", "现代", "古代", "中世纪", "未来",
  "校园", "职场", "冒险", "恐怖", "悬疑", "恋爱", "喜剧", "悲剧",
  "战争", "武侠", "仙侠", "末日", "赛博朋克", "蒸汽朋克", "魔法",
  "超能力", "吸血鬼", "狼人", "天使", "恶魔", "神明", "机器人",
  "异世界", "穿越", "游戏", "运动", "音乐", "美食", "推理",
]

interface CardItem {
  id: number
  name: string
  description: string
  tags: string[]
  is_r18: boolean
  image_path: string
  created_at: string
  updated_at: string
}

export default function CardsPage() {
  const navigate = useNavigate()
  const [data, setData] = useState<CardItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [filterTags, setFilterTags] = useState<string[]>([])
  const [filterR18, setFilterR18] = useState<boolean | undefined>(undefined)
  const pageSize = 20

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      params.set('page', String(page))
      params.set('page_size', String(pageSize))
      if (search) params.set('search', search)
      if (filterTags.length > 0) params.set('tags', filterTags.join(','))
      if (filterR18 !== undefined) params.set('is_r18', String(filterR18))

      const res = await api.get(`/cards?${params.toString()}`)
      setData(res.items || [])
      setTotal(res.total || 0)
    } catch (e: any) {
      message.error('加载失败: ' + (e.message || '未知错误'))
    } finally {
      setLoading(false)
    }
  }, [page, search, filterTags, filterR18])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const handleDelete = async (id: number) => {
    try {
      await api.delete(`/cards/${id}`)
      message.success('角色卡已删除')
      fetchData()
    } catch (e: any) {
      message.error('删除失败: ' + (e.message || '未知错误'))
    }
  }

  const columns = [
    {
      title: '图片',
      dataIndex: 'image_path',
      key: 'image',
      width: 80,
      render: (path: string) => {
        if (path) {
          return <Image src={path} width={60} height={60} style={{ borderRadius: 8, objectFit: 'cover' }} fallback="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHRleHQgeD0iMzAiIHk9IjMwIiBmb250LXNpemU9IjI4IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBkeT0iLjNlbSI+8J+RpDwvdGV4dD48L3N2Zz4=" />
        }
        return (
          <div style={{
            width: 60, height: 60, borderRadius: 8,
            background: '#f0f0f0', display: 'flex',
            alignItems: 'center', justifyContent: 'center',
          }}>
            <UserOutlined style={{ fontSize: 28, color: '#bbb' }} />
          </div>
        )
      },
    },
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: CardItem) => (
        <Space>
          <span style={{ fontWeight: 500, fontSize: 15 }}>{text}</span>
          {record.is_r18 && <Tag color="red">R18</Tag>}
        </Space>
      ),
    },
    {
      title: '标签',
      dataIndex: 'tags',
      key: 'tags',
      width: 280,
      render: (tags: string[]) => (
        <Space size={[0, 4]} wrap>
          {(tags || []).slice(0, 4).map((tag: string) => (
            <Tag key={tag} color="blue">{tag}</Tag>
          ))}
          {(tags || []).length > 4 && <Tag>+{tags.length - 4}</Tag>}
        </Space>
      ),
    },
    {
      title: '简介',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      render: (text: string) => (
        <Tooltip title={text}>
          <span style={{ color: '#666' }}>{text || '-'}</span>
        </Tooltip>
      ),
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      key: 'updated_at',
      width: 170,
      render: (text: string) => text ? new Date(text).toLocaleString('zh-CN') : '-',
    },
    {
      title: '操作',
      key: 'actions',
      width: 100,
      render: (_: any, record: CardItem) => (
        <Space>
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => navigate(`/cards/${record.id}`)} />
          <Popconfirm title="确定删除此角色卡吗？" onConfirm={() => handleDelete(record.id)}>
            <Button type="link" size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Title level={3} style={{ margin: 0 }}>
          <UserOutlined style={{ marginRight: 8 }} />
          角色卡管理
          <Tag style={{ marginLeft: 12 }}>{total} 张</Tag>
        </Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchData}>刷新</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/cards/new')}>
            创建角色卡
          </Button>
        </Space>
      </div>

      <Card>
        <Row gutter={[16, 12]} style={{ marginBottom: 16 }}>
          <Col xs={24} sm={8}>
            <Input
              prefix={<SearchOutlined />}
              placeholder="搜索名称或简介"
              value={search}
              onChange={e => { setSearch(e.target.value); setPage(1) }}
              allowClear
            />
          </Col>
          <Col xs={24} sm={10}>
            <Select
              mode="multiple"
              placeholder="按标签筛选"
              style={{ width: '100%' }}
              options={TAG_OPTIONS.map(t => ({ label: t, value: t }))}
              value={filterTags}
              onChange={tags => { setFilterTags(tags); setPage(1) }}
              allowClear
            />
          </Col>
          <Col xs={24} sm={6}>
            <Space>
              <span>R18:</span>
              <Select
                style={{ width: 100 }}
                value={filterR18}
                onChange={v => { setFilterR18(v); setPage(1) }}
                allowClear
                placeholder="全部"
                options={[
                  { label: '是', value: true },
                  { label: '否', value: false },
                ]}
              />
            </Space>
          </Col>
        </Row>

        <Table
          dataSource={data}
          columns={columns}
          rowKey="id"
          loading={loading}
          pagination={{
            current: page,
            pageSize,
            total,
            showTotal: t => `共 ${t} 张角色卡`,
            showSizeChanger: false,
            onChange: setPage,
          }}
          onRow={(record) => ({
            onDoubleClick: () => navigate(`/cards/${record.id}`),
            style: { cursor: 'pointer' },
          })}
        />
      </Card>
    </div>
  )
}
