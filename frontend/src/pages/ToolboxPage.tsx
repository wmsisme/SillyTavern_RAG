import { Typography, Card, Row, Col } from 'antd'
import { useNavigate } from 'react-router-dom'
import {
  FileTextOutlined,
  SwapOutlined,
  TranslationOutlined,
  CodeOutlined,
  ReadOutlined,
  ToolOutlined,
} from '@ant-design/icons'

const { Title } = Typography

const tools = [
  { key: 'separator', label: '元数据分离器', desc: '分离角色卡的 JSON 和图片', icon: <FileTextOutlined /> },
  { key: 'worldbook-converter', label: '世界书转换器', desc: 'CharacterBook ↔ WorldBook 双向转换', icon: <SwapOutlined /> },
  { key: 'chinese-converter', label: '简繁转换器', desc: '批量转换角色卡简繁体', icon: <TranslationOutlined /> },
  { key: 'width-converter', label: '文本格式化', desc: '全角半角、清除空行、JSON 压缩', icon: <CodeOutlined /> },
  { key: 'jsonl-novel-converter', label: 'JSONL 小说转换器', desc: 'JSONL 聊天记录转 Markdown 小说', icon: <ReadOutlined /> },
]

export default function ToolboxPage() {
  const navigate = useNavigate()

  return (
    <div>
      <Title level={3}>
        <ToolOutlined style={{ marginRight: 8 }} />
        工具箱
      </Title>
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        {tools.map(tool => (
          <Col xs={24} sm={12} md={8} key={tool.key}>
            <Card
              hoverable
              onClick={() => navigate(`/toolbox/${tool.key}`)}
              style={{ height: '100%' }}
            >
              <Card.Meta
                avatar={tool.icon}
                title={tool.label}
                description={tool.desc}
              />
            </Card>
          </Col>
        ))}
      </Row>
    </div>
  )
}
