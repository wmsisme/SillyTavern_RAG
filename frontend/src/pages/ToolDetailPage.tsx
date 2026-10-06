import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Typography, Card, Upload, Button, Select, Space, App,
  Row, Col, Divider, Input, Alert, Result, Checkbox,
} from 'antd'
import {
  UploadOutlined, DownloadOutlined, ArrowLeftOutlined,
  FileTextOutlined, SwapOutlined, TranslationOutlined,
  CodeOutlined, ReadOutlined, CopyOutlined, ClearOutlined,
} from '@ant-design/icons'

const { Title, Paragraph, Text } = Typography
const { TextArea } = Input

/** 上传大小上限：后端会把整个文件读进内存再处理，超大文件会直接把服务打满 */
const MAX_UPLOAD_MB = 32
const MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024

/** 前端侧类型校验：Upload 的 accept 只在文件选择框里生效，拖拽/改后缀都能绕过 */
function fileAcceptOk(f: File, accept: string): boolean {
  if (!accept) return true
  const name = (f.name || '').toLowerCase()
  const type = (f.type || '').toLowerCase()
  return accept.split(',').map(s => s.trim().toLowerCase()).filter(Boolean).some(p => {
    if (p.startsWith('.')) return name.endsWith(p)
    if (p.endsWith('/*')) return type.startsWith(p.slice(0, -1))
    return type === p
  })
}

const TOOL_CONFIGS: Record<string, {
  title: string; icon: React.ReactNode; desc: string;
  acceptedFiles: string; operations?: { label: string; value: string }[];
}> = {
  'separator': {
    title: '元数据分离器', icon: <FileTextOutlined />,
    desc: '上传角色卡文件（PNG 图片或 JSON 文件），分离其中的 JSON 元数据和图片。',
    acceptedFiles: '.png,.json',
  },
  'worldbook-converter': {
    title: '世界书转换器', icon: <SwapOutlined />,
    desc: '在 CharacterBook 和 WorldBook 格式之间进行双向转换。',
    acceptedFiles: '.json',
    operations: [
      { label: 'CharacterBook → WorldBook', value: 'characterbook_to_worldbook' },
      { label: 'WorldBook → CharacterBook', value: 'worldbook_to_characterbook' },
    ],
  },
  'chinese-converter': {
    title: '简繁转换器', icon: <TranslationOutlined />,
    desc: '上传文本或 JSON 文件，批量转换简繁体。',
    acceptedFiles: '.txt,.json,.md',
    operations: [
      { label: '简体→繁体', value: 's2t' },
      { label: '繁体→简体', value: 't2s' },
      { label: '简体→台湾繁体', value: 's2tw' },
      { label: '台湾繁体→简体', value: 'tw2s' },
      { label: '简体→香港繁体', value: 's2hk' },
      { label: '香港繁体→简体', value: 'hk2s' },
    ],
  },
  'width-converter': {
    title: '文本格式化', icon: <CodeOutlined />,
    desc: '全角半角转换、清除独立空行、JSON 压缩/格式化。',
    acceptedFiles: '.txt,.json,.md',
    operations: [
      { label: '全角→半角', value: 'fullwidth_to_halfwidth' },
      { label: '半角→全角', value: 'halfwidth_to_fullwidth' },
      { label: '清除独立空行', value: 'remove_empty_lines' },
      { label: 'JSON 压缩', value: 'compress_json' },
      { label: 'JSON 格式化', value: 'format_json' },
    ],
  },
  'jsonl-novel-converter': {
    title: 'JSONL 小说转换器', icon: <ReadOutlined />,
    desc: '将 JSONL 聊天记录整理为可阅读的 Markdown 小说格式。',
    acceptedFiles: '.jsonl,.txt',
  },
}

export default function ToolDetailPage() {
  const { message } = App.useApp()
  const { toolId } = useParams<{ toolId: string }>()
  const navigate = useNavigate()
  const config = toolId ? TOOL_CONFIGS[toolId] : null
  const [file, setFile] = useState<File | null>(null)
  const [direction, setDirection] = useState(config?.operations?.[0]?.value || '')
  const [operation, setOperation] = useState(config?.operations?.[0]?.value || '')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [charMapping, setCharMapping] = useState('{}')
  /** 是否把 AI 的思考过程（reasoning）也写进小说里，默认不要 */
  const [includeReasoning, setIncludeReasoning] = useState(false)
  const [previewText, setPreviewText] = useState('')
  const [imageUrl, setImageUrl] = useState('')

  // 切换工具时必须重置这些状态：路由参数变了但组件实例是复用的，
  // 否则会把上一个工具的 direction/operation 带到新工具上
  // （实测 /toolbox/worldbook-converter → /toolbox/chinese-converter 会发出
  //  对方不支持的参数值，后端直接回「不支持的转换方向」）。
  useEffect(() => {
    const first = TOOL_CONFIGS[toolId || '']?.operations?.[0]?.value || ''
    setDirection(first)
    setOperation(first)
    setFile(null)
    setResult(null)
    setPreviewText('')
    setImageUrl('')
  }, [toolId])

  if (!config) {
    return (
      <Result status="404" title="工具未找到" extra={
        <Button onClick={() => navigate('/toolbox')} icon={<ArrowLeftOutlined />}>返回工具箱</Button>
      } />
    )
  }

  const apiPath = `/api/tools/${toolId}`

  const handleProcess = async () => {
    if (!file) { message.warning('请先选择文件'); return }
    setLoading(true)
    setResult(null)
    setPreviewText('')
    setImageUrl('')

    const formData = new FormData()
    formData.append('file', file)
    if (config.operations) {
      if (toolId === 'chinese-converter') formData.append('direction', direction)
      else if (toolId === 'width-converter') formData.append('operation', operation)
      else formData.append('direction', direction)
    }
    if (toolId === 'jsonl-novel-converter') {
      formData.append('character_mapping', charMapping)
      formData.append('include_reasoning', String(includeReasoning))
    }

    try {
      const resp = await fetch(apiPath, { method: 'POST', body: formData })
      const data: any = await resp.json().catch(() => ({}))

      // 后端出错时返回的是 HTTP 4xx/5xx + {detail}，原来既不检查 resp.ok 也不认 detail，
      // 于是「处理失败」会被显示成「处理完成」。这里统一处理。
      if (!resp.ok) {
        const msg = data?.detail || data?.error || `HTTP ${resp.status}`
        setResult({ error: msg })
        message.error('处理失败: ' + msg)
        return
      }

      setResult(data)

      if (data.converted_text) {
        setPreviewText(data.converted_text)
      }
      if (data.converted_data) {
        setPreviewText(JSON.stringify(data.converted_data, null, 2))
      }
      if (data.json_data) {
        setPreviewText(JSON.stringify(data.json_data, null, 2))
      }

      // 元数据分离器返回的图片是 base64，转成 blob URL 供预览/下载
      if (data.image_base64) {
        setImageUrl(`data:${data.image_mime || 'image/png'};base64,${data.image_base64}`)
      }

      if (data.error) {
        message.error(data.error)
      } else {
        message.success(data.message || '处理完成')
      }
    } catch (e: any) {
      message.error('处理失败: ' + (e.message || '未知错误'))
    } finally {
      setLoading(false)
    }
  }

  const handleDownload = () => {
    if (!previewText) return
    const blob = new Blob([previewText], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    const ext = toolId === 'jsonl-novel-converter' ? '.md' : toolId === 'worldbook-converter' ? '.json' : '.txt'
    a.download = (file?.name?.replace(/\.[^.]+$/, '') || 'output') + '_converted' + ext
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleDownloadImage = () => {
    if (!imageUrl) return
    const a = document.createElement('a')
    a.href = imageUrl
    a.download = result?.image_filename || ((file?.name?.replace(/\.[^.]+$/, '') || 'card') + '.png')
    a.click()
  }

  return (
    <div style={{ maxWidth: 900, margin: '0 auto' }}>
      <div style={{ marginBottom: 24 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/toolbox')} style={{ marginBottom: 8 }}>返回工具箱</Button>
        <Title level={3}>{config.icon} {config.title}</Title>
        <Paragraph type="secondary">{config.desc}</Paragraph>
      </div>

      <Card style={{ marginBottom: 16 }}>
        <Row gutter={[16, 16]}>
          <Col xs={24} md={8}>
            <Upload
              beforeUpload={(f) => {
                const file = f as File
                if (!fileAcceptOk(file, config.acceptedFiles)) {
                  message.error(`文件类型不支持，该工具只接受：${config.acceptedFiles}`)
                  return Upload.LIST_IGNORE
                }
                if (file.size > MAX_UPLOAD_BYTES) {
                  message.error(`文件太大（${(file.size / 1024 / 1024).toFixed(1)} MB），上限 ${MAX_UPLOAD_MB} MB`)
                  return Upload.LIST_IGNORE
                }
                setFile(file)
                return false
              }}
              maxCount={1}
              accept={config.acceptedFiles}
              onRemove={() => { setFile(null); setResult(null); setPreviewText(''); setImageUrl('') }}
            >
              <Button icon={<UploadOutlined />} block>选择文件</Button>
            </Upload>
            {file && (
              <Text type="secondary" style={{ display: 'block', marginTop: 8 }}>
                {file.name}（{(file.size / 1024).toFixed(0)} KB）
              </Text>
            )}
          </Col>

          {toolId === 'jsonl-novel-converter' && (
            <Col xs={24}>
              <Space direction="vertical" style={{ width: '100%' }} size={8}>
                <TextArea rows={2} value={charMapping} onChange={e => setCharMapping(e.target.value)}
                  placeholder='角色名映射（可选），如：{"user":"我","心理医生":"陈医生"}' />
                <Space size={16} wrap>
                  <Checkbox checked={includeReasoning} onChange={e => setIncludeReasoning(e.target.checked)}>
                    把 AI 的思考过程也写进去
                  </Checkbox>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    支持 SillyTavern 导出的聊天记录（.jsonl）与 OpenAI 的 role/content 格式
                  </Text>
                </Space>
              </Space>
            </Col>
          )}

          {config.operations && toolId !== 'width-converter' && (
            <Col xs={24} md={8}>
              <Select style={{ width: '100%' }} value={direction} onChange={setDirection} options={config.operations} />
            </Col>
          )}

          {config.operations && toolId === 'width-converter' && (
            <Col xs={24} md={8}>
              <Select style={{ width: '100%' }} value={operation} onChange={setOperation} options={config.operations} />
            </Col>
          )}

          <Col xs={24} md={toolId === 'separator' ? 16 : 8}>
            <Space>
              <Button type="primary" loading={loading} onClick={handleProcess} disabled={!file}>开始处理</Button>
              {previewText && <Button icon={<DownloadOutlined />} onClick={handleDownload}>下载结果</Button>}
              {imageUrl && <Button icon={<DownloadOutlined />} onClick={handleDownloadImage}>下载图片</Button>}
              {(previewText || imageUrl) && <Button icon={<ClearOutlined />} onClick={() => { setResult(null); setPreviewText(''); setImageUrl(''); setFile(null) }}>清空</Button>}
            </Space>
          </Col>
        </Row>
      </Card>

      {result?.error && (
        <Alert type="error" message="处理失败" description={result.error} style={{ marginBottom: 16 }} />
      )}

      {result?.message && !result?.error && (
        <Alert type="success" message={result.message} style={{ marginBottom: 16 }} />
      )}

      {imageUrl && (
        <Card title="分离出的图片" style={{ marginBottom: 16 }} extra={
          <Button icon={<DownloadOutlined />} size="small" onClick={handleDownloadImage}>下载图片</Button>
        }>
          <img src={imageUrl} alt="分离出的角色卡图片"
            style={{ maxWidth: '100%', maxHeight: 400, borderRadius: 8, display: 'block' }} />
        </Card>
      )}

      {previewText && (
        <Card title="结果预览" extra={
          <Button icon={<CopyOutlined />} size="small" onClick={() => {
            navigator.clipboard.writeText(previewText)
            message.success('已复制到剪贴板')
          }}>复制</Button>
        }>
          <pre style={{
            maxHeight: 500, overflow: 'auto', whiteSpace: 'pre-wrap',
            wordBreak: 'break-word', background: '#f5f5f5', padding: 16,
            borderRadius: 8, fontSize: 13, lineHeight: 1.7,
          }}>
            {previewText.slice(0, 50000)}
            {previewText.length > 50000 && '\n\n... (内容过长，已截断)'}
          </pre>
        </Card>
      )}
    </div>
  )
}
