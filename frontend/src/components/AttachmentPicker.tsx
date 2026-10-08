import { useRef, useState, type ChangeEvent } from 'react'
import { App, Button, Space, Typography } from 'antd'
import { api } from '../services/api'

const { Text } = Typography

/** 与后端 attachment_service.ALLOWED_EXT 对齐 —— 这里只是提前把关，真正说了算的是服务端。 */
const ACCEPT = '.md,.txt,.pdf,.docx,.json,.csv'
const MAX_FILES = 3
const MAX_MB = 20

export interface PickedFile {
  id: number
  orig_name: string
  size: number
}

/**
 * 附件选择器 —— 两个反馈入口（顶部「反馈」与提问后的评价）**共用**这一个。
 *
 * 两段式上传的**第一段**：选好就立刻传，拿到 id；提交反馈时再把 id 带上去绑定
 * （见 后端 api/attachments.py 的说明）。为什么要分两段：
 *   ① 反馈接口是 JSON 的，为它单独改成 multipart 会牵动前后端好几处；
 *   ② 「文件已经传完了」本身就是在给用户反馈 —— 比一个转圈的大按钮诚实。
 *
 * 五道闸门（大小 / 每次个数 / 每 IP 每天 / 每用户 / 全局总量）都在**服务端**。
 * 这里只做「别让用户白等」的预检（明显超限就别开始传了）；
 * 服务端拒绝时把它给的原因**原样**显示 —— 那边写的是人话，别翻译、别吞掉。
 */
export default function AttachmentPicker({ value, onChange, hint }: {
  value: PickedFile[]
  onChange: (v: PickedFile[]) => void
  hint?: string
}) {
  const { message } = App.useApp()
  const inputRef = useRef<HTMLInputElement>(null)
  const [busy, setBusy] = useState(false)

  const pick = async (e: ChangeEvent<HTMLInputElement>) => {
    const picked = Array.from(e.target.files || [])
    e.target.value = ''                    // 清掉：同一个文件连选两次也要能触发
    if (!picked.length) return

    const room = MAX_FILES - value.length
    if (room <= 0) {
      message.warning(`最多 ${MAX_FILES} 个文件`)
      return
    }
    const files = picked.slice(0, room)
    if (picked.length > room) message.warning(`最多 ${MAX_FILES} 个，先传前 ${room} 个`)

    const tooBig = files.find(f => f.size > MAX_MB * 1024 * 1024)
    if (tooBig) {
      message.error(`「${tooBig.name}」超过 ${MAX_MB}MB —— 换个小的，或者只传其中的关键部分`)
      return
    }

    const form = new FormData()
    files.forEach(f => form.append('files', f))
    setBusy(true)
    try {
      const r = await api.upload<{ items: PickedFile[] }>('/attachments', form)
      onChange([...value, ...(r?.items || [])])
      message.success(`传好了 ${r?.items?.length || 0} 个文件`)
    } catch (err: any) {
      message.error(err?.message || '上传失败，稍后再试')
    } finally {
      setBusy(false)
    }
  }

  const remove = async (id: number) => {
    try {
      await api.delete(`/attachments/${id}`)
      onChange(value.filter(v => v.id !== id))
    } catch (err: any) {
      message.error(err?.message || '删不掉这个文件')
    }
  }

  return (
    <div>
      <Space size={8} wrap>
        <Button size="small" loading={busy} onClick={() => inputRef.current?.click()}>
          选择文件
        </Button>
        <Text type="secondary" style={{ fontSize: 12 }}>
          {hint || `支持 md / txt / pdf / docx / json / csv，最多 ${MAX_FILES} 个、单个 ${MAX_MB}MB`}
        </Text>
      </Space>
      <input ref={inputRef} type="file" multiple accept={ACCEPT}
             onChange={pick} style={{ display: 'none' }} />

      {value.length > 0 && (
        <ul style={{ margin: '8px 0 0', paddingLeft: 18 }}>
          {value.map(f => (
            <li key={f.id} style={{ fontSize: 12 }}>
              <Text>{f.orig_name}</Text>
              <Text type="secondary">（{f.size < 1024 * 1024
                ? `${Math.ceil(f.size / 1024)} KB`
                : `${(f.size / 1048576).toFixed(1)} MB`}）</Text>
              <Button type="link" size="small" onClick={() => remove(f.id)}>去掉</Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
