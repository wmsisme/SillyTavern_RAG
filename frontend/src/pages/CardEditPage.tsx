import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Typography, Form, Input, Button, Select, Switch, Card, Space,
  App, Tabs, Spin, Row, Col, Divider, Tag, InputNumber, Upload,
} from 'antd'
import {
  SaveOutlined, RobotOutlined, ArrowLeftOutlined,
  UserOutlined, PlusOutlined, UploadOutlined, PictureOutlined,
} from '@ant-design/icons'
import { api } from '../services/api'

const { Title, Text } = Typography
const { TextArea } = Input

const TAG_OPTIONS = [
  "RPG", "日常聊天", "科幻", "奇幻", "现代", "古代", "中世纪", "未来",
  "校园", "职场", "冒险", "恐怖", "悬疑", "恋爱", "喜剧", "悲剧",
  "战争", "武侠", "仙侠", "末日", "赛博朋克", "蒸汽朋克", "魔法",
  "超能力", "吸血鬼", "狼人", "天使", "恶魔", "神明", "机器人",
  "异世界", "穿越", "游戏", "运动", "音乐", "美食", "推理",
]

export default function CardEditPage() {
  const { message } = App.useApp()
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [form] = Form.useForm()
  const isNew = !id || id === 'new'
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [aiInput, setAiInput] = useState('')
  const [generating, setGenerating] = useState(false)
  const [imagePath, setImagePath] = useState('')
  const [uploading, setUploading] = useState(false)
  const [suggesting, setSuggesting] = useState(false)
  const [generatingBar, setGeneratingBar] = useState(false)

  useEffect(() => {
    if (!isNew) {
      setLoading(true)
      api.get(`/cards/${id}`)
        .then((data: any) => {
          form.setFieldsValue(data)
          setImagePath(data.image_path || '')
        })
        .catch(() => message.error('加载角色卡失败'))
        .finally(() => setLoading(false))
    }
  }, [id, form, isNew])

  // 图片上传：新卡还没 id，先保存再传
  const handleUploadImage = async (f: File) => {
    if (isNew) {
      message.warning('请先保存角色卡，再上传图片')
      return
    }
    setUploading(true)
    try {
      const fd = new FormData()
      fd.append('file', f)
      // 这里必须用原生 fetch：FormData 要让浏览器自己加 multipart boundary，
      // 走 api.post 会被固定成 Content-Type: application/json 而失败。
      const resp = await fetch(`/api/cards/${id}/image`, { method: 'POST', body: fd })
      const data: any = await resp.json().catch(() => ({}))
      if (!resp.ok) throw new Error(data?.detail || `HTTP ${resp.status}`)
      setImagePath(data.image_path || '')
      message.success('图片已上传')
    } catch (e: any) {
      message.error('上传失败: ' + (e.message || '未知错误'))
    } finally {
      setUploading(false)
    }
  }

  const handleRemoveImage = async () => {
    if (isNew) return
    try {
      const resp = await fetch(`/api/cards/${id}/image`, { method: 'DELETE' })
      const data: any = await resp.json().catch(() => ({}))
      if (!resp.ok) throw new Error(data?.detail || `HTTP ${resp.status}`)
      setImagePath('')
      message.success('已移除图片，列表里会显示默认图标')
    } catch (e: any) {
      message.error('移除失败: ' + (e.message || '未知错误'))
    }
  }

  const characterInfo = () => {
    const v = form.getFieldsValue()
    return [v.name, v.gender, v.age, v.species, v.occupation, v.personality, v.description]
      .filter(Boolean).join('，')
  }

  // 状态栏 AI 生成：按当前 is_r18 开关走对应字段（需求要求两种内容不一样）
  const handleGenerateStatusBar = async () => {
    const info = characterInfo()
    if (!info) { message.warning('请先填写角色名称、性格等基本信息'); return }
    setGeneratingBar(true)
    try {
      const r18 = !!form.getFieldValue('is_r18')
      const data: any = await api.post('/cards/generate/status-bar', { character_info: info, is_r18: r18 })
      if (data.error) throw new Error(data.error)
      const field = r18 ? 'status_bar_content_r18' : 'status_bar_content'
      form.setFieldValue(field, data.status_bar || '')
      form.setFieldValue('has_status_bar', true)
      message.success(r18 ? '已生成 R18 状态栏内容' : '已生成全年龄状态栏内容')
    } catch (e: any) {
      message.error('生成状态栏失败: ' + (e.message || '未知错误'))
    } finally {
      setGeneratingBar(false)
    }
  }

  const handleSuggestTags = async () => {
    const info = characterInfo()
    if (!info) { message.warning('请先填写角色描述'); return }
    setSuggesting(true)
    try {
      const data: any = await api.post('/cards/suggest-tags', { character_info: info })
      const tags: string[] = data.tags || []
      if (!tags.length) { message.warning('没有拿到推荐标签，再补充点角色信息试试'); return }
      const cur: string[] = form.getFieldValue('tags') || []
      form.setFieldValue('tags', Array.from(new Set([...cur, ...tags])))
      message.success(`推荐 ${tags.length} 个标签，已并入当前选择`)
    } catch (e: any) {
      message.error('推荐标签失败: ' + (e.message || '未知错误'))
    } finally {
      setSuggesting(false)
    }
  }

  const handleGenerate = async () => {
    if (!aiInput.trim()) {
      message.warning('请先输入角色描述')
      return
    }
    setGenerating(true)
    try {
      const data: any = await api.post('/cards/generate/preview', { description: aiInput.trim() })
      if (data.error) {
        message.error(data.error)
      } else {
        form.setFieldsValue(data)
        message.success('角色卡生成成功，请检查并修改后保存')
      }
    } catch (e: any) {
      message.error('生成失败: ' + (e.message || '未知错误'))
    } finally {
      setGenerating(false)
    }
  }

  const handleSave = async (values: any) => {
    setSaving(true)
    try {
      if (isNew) {
        const created: any = await api.post('/cards', values)
        message.success('角色卡创建成功，接下来可以上传图片')
        // 跳到带上 id 的编辑页：图片上传需要 card_id
        navigate(`/cards/${created.id}`)
      } else {
        await api.put(`/cards/${id}`, values)
        message.success('角色卡更新成功')
      }
    } catch (e: any) {
      message.error('保存失败: ' + (e.message || '未知错误'))
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!isNew && window.confirm('确定删除此角色卡吗？')) {
      try {
        await api.delete(`/cards/${id}`)
        message.success('角色卡已删除')
        navigate('/cards')
      } catch (e: any) {
        message.error('删除失败: ' + (e.message || '未知错误'))
      }
    }
  }

  if (loading) {
    return <div style={{ textAlign: 'center', padding: 48 }}><Spin size="large" /></div>
  }

  return (
    <div style={{ maxWidth: 1000, margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/cards')}>返回</Button>
          <Title level={3} style={{ margin: 0 }}>
            <UserOutlined style={{ marginRight: 8 }} />
            {isNew ? '创建角色卡' : '编辑角色卡'}
          </Title>
        </Space>
        <Space>
          {!isNew && (
            <Button danger onClick={handleDelete}>删除角色卡</Button>
          )}
          <Button type="primary" icon={<SaveOutlined />} loading={saving} onClick={() => form.submit()}>
            保存
          </Button>
        </Space>
      </div>

      <Row gutter={24}>
        <Col span={12}>
          <Card title={<><RobotOutlined /> AI 生成助手</>} size="small" style={{ marginBottom: 24 }}>
            <TextArea
              rows={6}
              value={aiInput}
              onChange={e => setAiInput(e.target.value)}
              placeholder="描述你想要的角色，AI 将自动生成角色卡。例如：
一个年轻的精灵弓箭手，性格内向但战斗勇敢，生活在古老的森林中..."
            />
            <Button
              type="primary"
              icon={<RobotOutlined />}
              loading={generating}
              onClick={handleGenerate}
              style={{ marginTop: 12 }}
              block
            >
              AI 生成角色卡
            </Button>
          </Card>
        </Col>

        <Col span={12}>
          <Card title="创建步骤" size="small" style={{ marginBottom: 24 }}>
            <ol style={{ paddingLeft: 20, lineHeight: 2 }}>
              <li>在左侧输入角色的自然语言描述</li>
              <li>点击 AI 生成，自动填充表单</li>
              <li>检查并修改各字段内容</li>
              <li>选择合适的标签</li>
              <li>根据需要开启 R18 和状态栏</li>
              <li>添加自定义 CSS（可选）</li>
              <li>点击保存完成</li>
            </ol>
          </Card>
        </Col>
      </Row>

      <Card>
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSave}
          initialValues={{
            name: '', age: '', gender: '', species: '', occupation: '',
            tags: [], is_r18: false, has_status_bar: false,
            status_bar_content: '', status_bar_content_r18: '',
            custom_css: '', first_message: '', description: '',
            appearance: '', personality: '', background: '',
          }}
        >
          <Tabs
            items={[
              {
                key: 'basic',
                label: '基本信息',
                children: (
                  <>
                    <Form.Item label="角色卡图片">
                      <Space align="start" size={16}>
                        {imagePath
                          ? <img src={imagePath} alt="角色卡图片"
                              style={{ width: 96, height: 96, objectFit: 'cover', borderRadius: 8, border: '1px solid #f0f0f0' }} />
                          : <div style={{
                              width: 96, height: 96, borderRadius: 8, border: '1px dashed #d9d9d9',
                              display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#bbb',
                            }}>
                              <PictureOutlined style={{ fontSize: 28 }} />
                            </div>}
                        <Space direction="vertical">
                          <Upload
                            accept="image/png,image/jpeg,image/webp,image/gif"
                            showUploadList={false}
                            beforeUpload={(f) => { handleUploadImage(f as File); return false }}
                          >
                            <Button icon={<UploadOutlined />} loading={uploading}>
                              {imagePath ? '更换图片' : '上传图片'}
                            </Button>
                          </Upload>
                          {imagePath && <Button size="small" danger onClick={handleRemoveImage}>移除图片</Button>}
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            {isNew ? '保存后才能上传' : 'png / jpg / webp / gif，≤8MB；不上传则列表显示默认图标'}
                          </Text>
                        </Space>
                      </Space>
                    </Form.Item>
                    <Row gutter={16}>
                      <Col span={12}>
                        <Form.Item label="角色名称" name="name" rules={[{ required: true }]}>
                          <Input placeholder="给角色起个名字" />
                        </Form.Item>
                      </Col>
                      <Col span={6}>
                        <Form.Item label="年龄" name="age">
                          <Input placeholder="年龄" />
                        </Form.Item>
                      </Col>
                      <Col span={6}>
                        <Form.Item label="性别" name="gender">
                          <Select
                            options={[
                              { label: '男', value: '男' },
                              { label: '女', value: '女' },
                              { label: '其他', value: '其他' },
                            ]}
                          />
                        </Form.Item>
                      </Col>
                    </Row>
                    <Row gutter={16}>
                      <Col span={12}>
                        <Form.Item label="种族" name="species">
                          <Input placeholder="人类、精灵、机器人等" />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item label="职业" name="occupation">
                          <Input placeholder="战士、法师、学生等" />
                        </Form.Item>
                      </Col>
                    </Row>
                    <Form.Item label="一句话简介" name="description">
                      <TextArea rows={2} placeholder="20-50字简短介绍" maxLength={100} showCount />
                    </Form.Item>
                  </>
                ),
              },
              {
                key: 'details',
                label: '详细设定',
                children: (
                  <>
                    <Form.Item label="外貌描述" name="appearance">
                      <TextArea rows={4} placeholder="描述角色的外貌特征：发型、眼睛、身高、体型、服装风格等" />
                    </Form.Item>
                    <Form.Item label="性格描述" name="personality">
                      <TextArea rows={4} placeholder="描述角色的性格特点、喜好、习惯、说话风格等" />
                    </Form.Item>
                    <Form.Item label="背景故事" name="background">
                      <TextArea rows={5} placeholder="描述角色的过往经历、家族背景、重要事件等" />
                    </Form.Item>
                  </>
                ),
              },
              {
                key: 'tags',
                label: '标签与分类',
                children: (
                  <>
                    <Form.Item label="角色标签" name="tags">
                      <Select mode="multiple" placeholder="选择标签，可多选" options={TAG_OPTIONS.map(t => ({ label: t, value: t }))} />
                    </Form.Item>
                    <Form.Item>
                      <Button icon={<RobotOutlined />} loading={suggesting} onClick={handleSuggestTags}>
                        AI 推荐标签
                      </Button>
                    </Form.Item>
                    <Divider />
                    <Row gutter={16}>
                      <Col span={8}>
                        <Form.Item label="R18 内容" name="is_r18" valuePropName="checked">
                          <Switch checkedChildren="开启" unCheckedChildren="关闭" />
                        </Form.Item>
                      </Col>
                      <Col span={8}>
                        <Form.Item label="状态栏" name="has_status_bar" valuePropName="checked">
                          <Switch checkedChildren="开启" unCheckedChildren="关闭" />
                        </Form.Item>
                      </Col>
                    </Row>
                  </>
                ),
              },
              {
                key: 'advanced',
                label: '高级设置',
                children: (
                  <>
                    <Form.Item label="开场白" name="first_message">
                      <TextArea rows={3} placeholder="角色第一次对用户说的话" />
                    </Form.Item>
                    <Form.Item>
                      <Space>
                        <Button icon={<RobotOutlined />} loading={generatingBar} onClick={handleGenerateStatusBar}>
                          AI 生成状态栏内容
                        </Button>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          按当前「R18 内容」开关写入对应字段，并自动开启状态栏
                        </Text>
                      </Space>
                    </Form.Item>
                    <Form.Item label="状态栏内容（全年龄）" name="status_bar_content">
                      <TextArea rows={3} placeholder='[{"label":"心情","value":"愉悦"},{"label":"好感度","value":"50"}]' />
                    </Form.Item>
                    <Form.Item label="状态栏内容（R18）" name="status_bar_content_r18">
                      <TextArea rows={3} placeholder='[{"label":"兴奋度","value":"30"},{"label":"服从度","value":"20"}]' />
                    </Form.Item>
                    <Form.Item label="自定义 CSS" name="custom_css">
                      <TextArea rows={6} placeholder="自定义 CSS 样式代码" style={{ fontFamily: 'monospace' }} />
                    </Form.Item>
                  </>
                ),
              },
            ]}
          />
        </Form>
      </Card>
    </div>
  )
}
