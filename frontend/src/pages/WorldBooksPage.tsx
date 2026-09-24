import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Typography, Card, Button, Input, Select, Space, Tag,
  message, Row, Col, List, Tooltip, Popconfirm,
} from 'antd'
import {
  PlusOutlined, BookOutlined, SearchOutlined,
  ReloadOutlined, EditOutlined, DeleteOutlined,
} from '@ant-design/icons'
import { api } from '../services/api'

const { Title, Paragraph, Text } = Typography

const TAG_OPTIONS = ["奇幻", "科幻", "现代", "古代", "末日", "仙侠", "武侠", "魔法", "赛博朋克", "蒸汽朋克", "异世界", "校园", "恐怖"]

interface WorldBookItem {
  id: number
  name: string
  description: string
  tags: string[]
  entries: any[]
  updated_at: string
}

export default function WorldBooksPage() {
  const navigate = useNavigate()
  const [data, setData] = useState<WorldBookItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [filterTags, setFilterTags] = useState<string[]>([])
  const pageSize = 5

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      params.set('page', String(page))
      params.set('page_size', String(pageSize))
      if (search) params.set('search', search)
      if (filterTags.length > 0) params.set('tags', filterTags.join(','))

      const res = await api.get(`/worldbooks?${params.toString()}`)
      setData(res.items || [])
      setTotal(res.total || 0)
    } catch (e: any) {
      message.error('加载失败')
    } finally {
      setLoading(false)
    }
  }, [page, search, filterTags])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const handleDelete = async (id: number) => {
    try {
      await api.delete(`/worldbooks/${id}`)
      message.success('世界书已删除')
      fetchData()
    } catch (e: any) {
      message.error('删除失败')
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Title level={3} style={{ margin: 0 }}>
          <BookOutlined style={{ marginRight: 8 }} />
          世界书管理
          <Tag style={{ marginLeft: 12 }}>{total} 本</Tag>
        </Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchData}>刷新</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/worldbooks/new')}>
            创建世界书
          </Button>
        </Space>
      </div>

      <Card>
        <Row gutter={[16, 12]} style={{ marginBottom: 16 }}>
          <Col xs={24} sm={10}>
            <Input prefix={<SearchOutlined />} placeholder="搜索名称或描述" value={search}
              onChange={e => { setSearch(e.target.value); setPage(1) }} allowClear />
          </Col>
          <Col xs={24} sm={14}>
            <Select mode="multiple" placeholder="按标签筛选" style={{ width: '100%' }}
              options={TAG_OPTIONS.map(t => ({ label: t, value: t }))}
              value={filterTags} onChange={tags => { setFilterTags(tags); setPage(1) }} allowClear />
          </Col>
        </Row>

        <List
          loading={loading}
          dataSource={data}
          pagination={{
            current: page, pageSize, total,
            showTotal: t => `共 ${t} 本世界书`,
            showSizeChanger: false,
            onChange: setPage,
          }}
          renderItem={(item: WorldBookItem) => (
            <List.Item
              actions={[
                <Button type="link" icon={<EditOutlined />} onClick={() => navigate(`/worldbooks/${item.id}`)}>编辑</Button>,
                <Popconfirm title="确定删除此世界书吗？" onConfirm={() => handleDelete(item.id)}>
                  <Button type="link" danger icon={<DeleteOutlined />}>删除</Button>
                </Popconfirm>,
              ]}
              onDoubleClick={() => navigate(`/worldbooks/${item.id}`)}
              style={{ cursor: 'pointer' }}
            >
              <List.Item.Meta
                avatar={
                  <div style={{
                    width: 56, height: 56, borderRadius: 8, background: '#f0f0f0',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                  }}>
                    <BookOutlined style={{ fontSize: 26, color: '#1677ff' }} />
                  </div>
                }
                title={
                  <Space>
                    <Text strong style={{ fontSize: 15 }}>{item.name}</Text>
                    {(item.tags || []).map((tag: string) => (
                      <Tag key={tag} color="blue">{tag}</Tag>
                    ))}
                  </Space>
                }
                description={
                  <Tooltip title={item.description}>
                    <Paragraph ellipsis={{ rows: 2 }} style={{ margin: 0, color: '#666' }}>
                      {item.description || '暂无描述'}
                    </Paragraph>
                  </Tooltip>
                }
              />
              <Text type="secondary" style={{ fontSize: 12 }}>
                {item.entries?.length || 0} 个条目 · {item.updated_at ? new Date(item.updated_at).toLocaleString('zh-CN') : '-'}
              </Text>
            </List.Item>
          )}
        />
      </Card>
    </div>
  )
}
