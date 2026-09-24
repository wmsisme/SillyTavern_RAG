import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Typography, Form, Input, Button, Select, Card, Space,
  Tabs, message, Spin, Row, Col, Divider, InputNumber,
  List, Popconfirm, Tag,
} from 'antd'
import {
  SaveOutlined, RobotOutlined, ArrowLeftOutlined,
  BookOutlined, PlusOutlined, DeleteOutlined,
} from '@ant-design/icons'
import { api } from '../services/api'

const { Title } = Typography
const { TextArea } = Input

const TAG_OPTIONS = ["奇幻", "科幻", "现代", "古代", "末日", "仙侠", "武侠", "魔法", "赛博朋克", "蒸汽朋克", "异世界", "校园", "恐怖"]

interface WorldBookEntry {
  key: string
  content: string
  comment: string
  depth: number
  trigger_words: string[]
}

export default function WorldBookEditPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [form] = Form.useForm()
  const isNew = !id || id === 'new'
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [aiInput, setAiInput] = useState('')
  const [generating, setGenerating] = useState(false)
  const [entries, setEntries] = useState<WorldBookEntry[]>([])

  useEffect(() => {
    if (!isNew) {
      setLoading(true)
      api.get(`/worldbooks/${id}`)
        .then((data: any) => {
          form.setFieldsValue(data)
          setEntries(data.entries || [])
        })
        .catch(() => message.error('加载世界书失败'))
        .finally(() => setLoading(false))
    }
  }, [id, form, isNew])

  const handleGenerate = async () => {
    if (!aiInput.trim()) { message.warning('请先输入世界观描述'); return }
    setGenerating(true)
    try {
      const data = await api.post('/worldbooks/generate/preview', { description: aiInput.trim() })
      if (data.error) {
        message.error(data.error)
      } else {
        form.setFieldsValue({ name: data.name, description: data.description, tags: data.tags })
        setEntries(data.entries || [])
        message.success('世界书生成成功，请检查并修改后保存')
      }
    } catch (e: any) { message.error('生成失败: ' + (e.message || '未知错误')) }
    finally { setGenerating(false) }
  }

  const handleAddEntry = () => {
    setEntries([...entries, { key: '', content: '', comment: '', depth: 1, trigger_words: [] }])
  }

  const handleDeleteEntry = (index: number) => {
    setEntries(entries.filter((_, i) => i !== index))
  }

  const handleUpdateEntry = (index: number, field: string, value: any) => {
    const newEntries: WorldBookEntry[] = entries.map((e, i) => i === index ? { ...e, [field]: value } : e)
    setEntries(newEntries)
  }

  const handleSave = async (values: any) => {
    setSaving(true)
    try {
      const payload = { ...values, entries }
      if (isNew) {
        await api.post('/worldbooks', payload)
        message.success('世界书创建成功')
        navigate('/worldbooks')
      } else {
        await api.put(`/worldbooks/${id}`, payload)
        message.success('世界书更新成功')
      }
    } catch (e: any) { message.error('保存失败: ' + (e.message || '未知错误')) }
    finally { setSaving(false) }
  }

  const handleDelete = async () => {
    if (!isNew && window.confirm('确定删除此世界书吗？')) {
      try {
        await api.delete(`/worldbooks/${id}`)
        message.success('世界书已删除')
        navigate('/worldbooks')
      } catch (e: any) { message.error('删除失败') }
    }
  }

  if (loading) {
    return <div style={{ textAlign: 'center', padding: 48 }}><Spin size="large" /></div>
  }

  return (
    <div style={{ maxWidth: 1000, margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/worldbooks')}>返回</Button>
          <Title level={3} style={{ margin: 0 }}>
            <BookOutlined style={{ marginRight: 8 }} />
            {isNew ? '创建世界书' : '编辑世界书'}
          </Title>
        </Space>
        <Space>
          {!isNew && <Button danger onClick={handleDelete}>删除世界书</Button>}
          <Button type="primary" icon={<SaveOutlined />} loading={saving} onClick={() => form.submit()}>保存</Button>
        </Space>
      </div>

      <Card title={<><RobotOutlined /> AI 世界观生成</>} size="small" style={{ marginBottom: 24 }}>
        <Row gutter={16}>
          <Col span={16}>
            <TextArea rows={5} value={aiInput} onChange={e => setAiInput(e.target.value)}
              placeholder="描述你的世界观，AI 将自动生成世界书条目。例如：
这是一个剑与魔法的奇幻世界，有三大王国互相争斗，远古龙族即将苏醒..." />
          </Col>
          <Col span={8}>
            <Card size="small" title="操作指南" style={{ height: '100%' }}>
              <ol style={{ paddingLeft: 16, fontSize: 13, lineHeight: 2.2 }}>
                <li>描述世界观</li>
                <li>点击 AI 生成</li>
                <li>检查并编辑条目</li>
                <li>手动增删条目</li>
                <li>点击保存</li>
              </ol>
              <Button type="primary" icon={<RobotOutlined />} loading={generating} onClick={handleGenerate} block>
                AI 生成世界书
              </Button>
            </Card>
          </Col>
        </Row>
      </Card>

      <Card>
        <Form form={form} layout="vertical" onFinish={handleSave}
          initialValues={{ name: '', description: '', tags: [] }}>
          <Tabs items={[{
            key: 'basic', label: '基本信息', children: (
              <>
                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item label="世界书名称" name="name" rules={[{ required: true }]}>
                      <Input placeholder="给你的世界观命名" />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item label="标签" name="tags">
                      <Select mode="multiple" placeholder="选择标签" options={TAG_OPTIONS.map(t => ({ label: t, value: t }))} />
                    </Form.Item>
                  </Col>
                </Row>
                <Form.Item label="世界观简述" name="description">
                  <TextArea rows={2} placeholder="30-100字简述" maxLength={200} showCount />
                </Form.Item>
              </>
            ),
          }, {
            key: 'entries', label: `条目管理 (${entries.length})`, children: (
              <div>
                <Button type="dashed" icon={<PlusOutlined />} onClick={handleAddEntry} block style={{ marginBottom: 16 }}>
                  添加条目
                </Button>
                <List
                  dataSource={entries}
                  renderItem={(entry: WorldBookEntry, index: number) => (
                    <List.Item>
                      <div style={{ width: '100%' }}>
                        <Row gutter={[12, 8]}>
                          <Col span={6}>
                            <Input placeholder="条目 Key" value={entry.key}
                              onChange={e => handleUpdateEntry(index, 'key', e.target.value)}
                              addonBefore="Key" />
                          </Col>
                          <Col span={3}>
                            <InputNumber style={{ width: '100%' }} placeholder="深度" value={entry.depth}
                              onChange={v => handleUpdateEntry(index, 'depth', v || 1)} min={1} max={10} addonBefore="深度" />
                          </Col>
                          <Col span={10}>
                            <Select mode="tags" placeholder="触发词（回车添加）" value={entry.trigger_words}
                              onChange={v => handleUpdateEntry(index, 'trigger_words', v)}
                              style={{ width: '100%' }} />
                          </Col>
                          <Col span={3}>
                            <Popconfirm title="删除此条目？" onConfirm={() => handleDeleteEntry(index)}>
                              <Button danger icon={<DeleteOutlined />} block>删除</Button>
                            </Popconfirm>
                          </Col>
                        </Row>
                        <Row gutter={12} style={{ marginTop: 8 }}>
                          <Col span={16}>
                            <TextArea rows={2} placeholder="条目内容" value={entry.content}
                              onChange={e => handleUpdateEntry(index, 'content', e.target.value)} />
                          </Col>
                          <Col span={8}>
                            <Input placeholder="备注说明" value={entry.comment}
                              onChange={e => handleUpdateEntry(index, 'comment', e.target.value)} />
                          </Col>
                        </Row>
                      </div>
                    </List.Item>
                  )}
                  locale={{ emptyText: '暂无条目，点击上方添加' }}
                />
              </div>
            ),
          }]} />
        </Form>
      </Card>
    </div>
  )
}
