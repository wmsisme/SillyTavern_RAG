import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Typography, Card, Upload, Button, Select, Space, message,
  Row, Col, Divider, Input, Alert, Result,
} from 'antd'
import {
  UploadOutlined, DownloadOutlined, ArrowLeftOutlined,
  FileTextOutlined, SwapOutlined, TranslationOutlined,
  CodeOutlined, ReadOutlined, CopyOutlined, ClearOutlined,
} from '@ant-design/icons'

const { Title, Paragraph, Text } = Typography
const { TextArea } = Input

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
  const { toolId } = useParams<{ toolId: string }>()
  const navigate = useNavigate()
  const config = toolId ? TOOL_CONFIGS[toolId] : null
  const [file, setFile] = useState<File | null>(null)
  const [direction, setDirection] = useState(config?.operations?.[0]?.value || '')
  const [operation, setOperation] = useState(config?.operations?.[0]?.value || '')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [charMapping, setCharMapping] = useState('{}')
  const [previewText, setPreviewText] = useState('')
  const [imageUrl, setImageUrl] = useState('')

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
    if (toolId === 'jsonl-novel-converter') formData.append('character_mapping', charMapping)

    try {
      const resp = await fetch(apiPath, { method: 'POST', body: formData })
      const data = await resp.json()
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

      if (!data.error) {
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
              beforeUpload={(f) => { setFile(f); return false }}
              maxCount={1}
              accept={config.acceptedFiles}
              onRemove={() => { setFile(null); setResult(null); setPreviewText(''); setImageUrl('') }}
            >
              <Button icon={<UploadOutlined />} block>选择文件</Button>
            </Upload>
            {file && <Text type="secondary" style={{ display: 'block', marginTop: 8 }}>{file.name}</Text>}
          </Col>

          {toolId === 'jsonl-novel-converter' && (
            <Col xs={24}>
              <TextArea rows={2} value={charMapping} onChange={e => setCharMapping(e.target.value)}
                placeholder='角色名映射，如：{"user":"我","assistant":"助手角色名"}' />
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
