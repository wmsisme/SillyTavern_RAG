import { useState, useRef, useEffect } from 'react'
import { Typography, Input, Button, Card, Spin, Divider, Space, Tag, List } from 'antd'
import { SearchOutlined, SendOutlined, FileTextOutlined, LoadingOutlined } from '@ant-design/icons'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { api, readErrorText } from '../services/api'
import { llmHeaders, looksLikeMissingKey, notifyMissingKey } from '../services/llm'
import AnswerFeedback from '../components/AnswerFeedback'

const { Title, Paragraph, Text } = Typography

interface SearchResult {
  content: string
  source: string
  score: number
}

export default function HomePage() {
  const [query, setQuery] = useState('')
  const [answer, setAnswer] = useState('')
  const [sources, setSources] = useState<SearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [streaming, setStreaming] = useState(false)
  const [hasSearched, setHasSearched] = useState(false)
  // 本次提问在服务端的记录 id —— 反馈按钮要拿它回传（由流式 done 事件带回来）
  const [queryLogId, setQueryLogId] = useState<number | null>(null)
  const answerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (answerRef.current) {
      answerRef.current.scrollTop = answerRef.current.scrollHeight
    }
  }, [answer])

  const handleSearch = async () => {
    if (!query.trim() || loading) return
    setLoading(true)
    setStreaming(true)
    setAnswer('')
    setSources([])
    setQueryLogId(null)      // 新的一次提问：反馈区要重新开始（组件按 id 变化自己重置）
    setHasSearched(true)

    try {
      const response = await fetch('/api/rag/ask/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...llmHeaders() },
        body: JSON.stringify({ query: query.trim() }),
      })

      if (!response.ok) {
        // 不能只报 "HTTP 400" —— 这一条多半是「还没填你自己的 API Key」，
        // 要把它变成人话，并把设置框直接弹出来（用户不用自己找入口）
        const detail = await readErrorText(response)
        if (looksLikeMissingKey(detail)) notifyMissingKey()
        throw new Error(detail)
      }

      const reader = response.body?.getReader()
      if (!reader) throw new Error('No reader')

      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.trim()) continue
          try {
            const data = JSON.parse(line)
            if (data.type === 'token') {
              setAnswer(prev => prev + data.data)
            } else if (data.type === 'sources') {
              setSources(data.data || [])
            } else if (data.type === 'error') {
              // 后端生成失败时会发 error 事件；原先这里不认，界面只剩一片空白
              setAnswer(prev => prev + `\n\n**生成失败**：${data.data}`)
              setStreaming(false)
            } else if (data.type === 'done') {
              // 后端把本次提问的记录 id 放在 done 里 —— 反馈按钮靠它定位
              setQueryLogId(data.query_log_id ?? null)
              setStreaming(false)
            }
          } catch {}
        }
      }
    } catch (e) {
      setAnswer(`搜索失败: ${e instanceof Error ? e.message : '未知错误'}`)
      setStreaming(false)
    } finally {
      setLoading(false)
      setStreaming(false)
    }
  }

  return (
    <div style={{ maxWidth: 900, margin: '0 auto' }}>
      <div style={{ textAlign: 'center', marginBottom: 32 }}>
        <Title level={2} style={{ marginBottom: 8 }}>
          <SearchOutlined style={{ marginRight: 12 }} />
          SillyTavern 知识库
        </Title>
        <Paragraph type="secondary">
          搜索 SillyTavern 相关文档：预设设置、CSS 样式、正则表达式、API 导入、角色卡、世界书等
        </Paragraph>
      </div>

      <div style={{ display: 'flex', gap: 12, marginBottom: 32 }}>
        <Input
          size="large"
          placeholder="输入你的问题，例如：如何用正则替换AI回复中的特定文字？"
          value={query}
          onChange={e => setQuery(e.target.value)}
          onPressEnter={handleSearch}
          prefix={<SearchOutlined />}
          disabled={loading}
        />
        <Button
          size="large"
          type="primary"
          icon={loading ? <LoadingOutlined /> : <SendOutlined />}
          onClick={handleSearch}
          loading={loading}
        >
          搜索
        </Button>
      </div>

      {loading && !answer && (
        <div style={{ textAlign: 'center', padding: 48 }}>
          <Spin size="large" tip="正在检索知识库..." />
        </div>
      )}

      {answer && (
        <Card
          title={
            <Space>
              <FileTextOutlined />
              <span>回答</span>
              {streaming && <Tag color="processing">生成中...</Tag>}
            </Space>
          }
          style={{ marginBottom: 24 }}
        >
          <div
            ref={answerRef}
            style={{
              maxHeight: 500,
              overflow: 'auto',
              lineHeight: 1.8,
            }}
          >
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {answer}
            </ReactMarkdown>
          </div>
        </Card>
      )}

      {queryLogId !== null && (
        <div style={{ marginBottom: 24 }}>
          <AnswerFeedback queryLogId={queryLogId} />
        </div>
      )}

      {sources.length > 0 && (
        <Card title="参考来源" size="small">
          <List
            dataSource={sources}
            renderItem={(item: SearchResult, index: number) => (
              <List.Item>
                <List.Item.Meta
                  title={
                    <Space>
                      <Tag color="blue">来源 {index + 1}</Tag>
                      <Text code>{item.source}</Text>
                      <Tag color={item.score > 0.5 ? 'green' : 'orange'}>
                        相关度: {(item.score * 100).toFixed(0)}%
                      </Tag>
                    </Space>
                  }
                  description={item.content.slice(0, 200) + (item.content.length > 200 ? '...' : '')}
                />
              </List.Item>
            )}
          />
        </Card>
      )}

      {!hasSearched && (
        <Card style={{ marginTop: 32 }}>
          <Title level={5}>使用示例</Title>
          <Divider />
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {[
              '如何用正则给 AI 回复中的魔法咒语自动添加斜体？',
              'SillyTavern 的预设文件存放在哪里？',
              '如何配置 OpenRouter API 连接？',
              '世界书的递归扫描是什么？',
              'CSS 自定义主题怎么设置？',
            ].map(example => (
              <Tag
                key={example}
                color="blue"
                style={{ cursor: 'pointer', padding: '4px 12px', fontSize: 14 }}
                onClick={() => {
                  setQuery(example)
                }}
              >
                {example}
              </Tag>
            ))}
          </div>
        </Card>
      )}
    </div>
  )
}
