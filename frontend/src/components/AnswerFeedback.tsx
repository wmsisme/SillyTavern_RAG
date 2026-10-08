import { useEffect, useState } from 'react'
import { App, Button, Card, Input, Space, Typography } from 'antd'
import { api } from '../services/api'
import AttachmentPicker, { type PickedFile } from './AttachmentPicker'

const { Text } = Typography

/**
 * 一次提问的结果反馈。
 *
 * 为什么必须有「检索到的内容不相关」这一档：**检索回了内容 ≠ 内容是对的**。
 * 光看相关度分数（我们自己的阈值判据）分不出"系统给错了"和"文档本身没写清楚"，
 * 而用户一眼就知道 —— 所以三档里最有用的是第三档。
 *
 * 用户选完档位再填原因（选填，但界面会鼓励写）：
 * 原因就是我们下次该补什么、或该修哪条召回的依据。
 *
 * 附件（2026-10-08 加）：用户可以**直接把自己手上的资料传上来**。
 * 这一档尤其有用 —— 他说"不相关"的时候，如果顺手传了正确的资料，
 * 站长在后台勾「这条要补进知识库」时就能直接拿它去改，不用再来回问。
 */
const OPTIONS = [
  { kind: 'solved', label: '👍 有帮助', tip: '这次回答解决了我的问题' },
  { kind: 'unsolved', label: '👎 没解决', tip: '没回答上我的问题' },
  {
    kind: 'irrelevant',
    label: '🚫 检索到的内容不相关',
    tip: '系统给了内容，但和我的问题没关系 —— 哪怕它显示的相关度很高',
  },
] as const

const PLACEHOLDER: Record<string, string> = {
  solved: '（选填）哪一点帮到了你？',
  unsolved: '（选填）你原本想解决什么？',
  irrelevant:
    '（选填，但写了我们才知道怎么改）哪一条不相关、为什么？例如「三条都是正则表达式的内容，和世界书无关」',
}

export default function AnswerFeedback({ queryLogId }: { queryLogId: number }) {
  const { message } = App.useApp()
  const [kind, setKind] = useState<string>('')
  const [reason, setReason] = useState('')
  const [files, setFiles] = useState<PickedFile[]>([])
  const [sending, setSending] = useState(false)
  const [sent, setSent] = useState(false)
  const [sentCount, setSentCount] = useState(0)

  // 换了一次提问（id 变了）→ 反馈状态清零，别把上一条的评价和附件带到这一条上
  useEffect(() => {
    setKind(''); setReason(''); setSent(false); setFiles([]); setSentCount(0)
  }, [queryLogId])

  const submit = async () => {
    if (!kind) {
      message.info('先选一个「有帮助 / 没解决 / 不相关」')
      return
    }
    setSending(true)
    try {
      const r = await api.post<{ message?: string }>('/rag/feedback', {
        query_log_id: queryLogId,
        kind,
        reason: reason.trim(),
        attachment_ids: files.map(f => f.id),
      })
      setSentCount(files.length)
      setSent(true)
      message.success(r?.message || '已记录，谢谢反馈')
    } catch (e: any) {
      message.error(e?.message || '提交失败，稍后再试')
    } finally {
      setSending(false)
    }
  }

  if (sent) {
    return (
      <Card size="small">
        <Text type="success">
          ✅ 已记录，谢谢你的反馈 —— 站长能看到它，并据此改进知识库。
          {sentCount > 0 && `连同 ${sentCount} 个文件一起收到了。`}
        </Text>
      </Card>
    )
  }

  return (
    <Card size="small" title="这次的结果对你有帮助吗？">
      <Space wrap>
        {OPTIONS.map(o => (
          <Button
            key={o.kind}
            size="small"
            title={o.tip}
            type={kind === o.kind ? 'primary' : 'default'}
            danger={kind === o.kind && (o.kind === 'irrelevant' || o.kind === 'unsolved')}
            onClick={() => setKind(o.kind)}
          >
            {o.label}
          </Button>
        ))}
      </Space>

      {kind && (
        <div style={{ marginTop: 12 }}>
          <Input.TextArea
            rows={2}
            value={reason}
            maxLength={500}
            showCount
            placeholder={PLACEHOLDER[kind]}
            onChange={e => setReason(e.target.value)}
          />

          {/* 手上有能纠正它的资料？传上来 —— 对「不相关」这一档尤其有价值 */}
          <div style={{ marginTop: 8 }}>
            <AttachmentPicker
              value={files}
              onChange={setFiles}
              hint="（可选）有能纠正它的资料就传上来，站长会拿它去改 —— 最多 3 个、单个 20MB"
            />
          </div>

          <div style={{ marginTop: 8 }}>
            <Button type="primary" size="small" loading={sending} onClick={submit}>
              提交反馈
            </Button>
            <Text type="secondary" style={{ marginLeft: 12, fontSize: 12 }}>
              原因可以留空，但写清楚能让我们更快改对
            </Text>
          </div>
        </div>
      )}
    </Card>
  )
}
