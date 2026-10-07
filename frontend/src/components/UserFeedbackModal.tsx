import { useState } from 'react'
import { App, Form, Input, Modal, Space, Tag, Typography } from 'antd'
import { api } from '../services/api'

/** 反馈分类：给几个快捷标签，用户不用自己想怎么归类 */
const CATEGORIES = ['建议', '体验', '故障', '其他'] as const

const PLACEHOLDER = [
  '例如：搜索结果经常给出不相关的内容',
  '例如：手机上打开排版乱了；工具箱上传大文件没提示',
  '例如：点「立即更新」转很久最后报错',
  '想说什么都行 ——',
].join('\n')

export default function UserFeedbackModal({ open, onClose }:
  { open: boolean; onClose: () => void }) {
  const { message } = App.useApp()
  const [form] = Form.useForm()
  const [category, setCategory] = useState<string>('建议')
  const [sending, setSending] = useState(false)

  const submit = async () => {
    let values: { content: string }
    try {
      values = await form.validateFields()
    } catch {
      return                       // 校验没过，antd 已经在字段上标红了
    }
    setSending(true)
    try {
      const r = await api.post<{ message?: string }>('/feedback', {
        content: values.content,
        category,
        // 带上当前页面：站长看到「工具箱页说的」就知道去查哪儿
        page: window.location.pathname,
      })
      message.success(r?.message || '收到，谢谢！')
      form.resetFields()
      setCategory('建议')
      onClose()
    } catch (e: any) {
      message.error(e?.message || '提交失败，稍后再试')
    } finally {
      setSending(false)
    }
  }

  return (
    <Modal
      title="给站长提个反馈"
      open={open}
      onCancel={() => { onClose() }}
      onOk={submit}
      okText="提交"
      confirmLoading={sending}
      width={560}
      destroyOnClose
    >
      <Typography.Paragraph type="secondary" style={{ fontSize: 12 }}>
        哪里不好用、哪里缺东西、哪里出错了，都可以直接说。每一条站长都能看到，
        也会记下你现在所在的页面，方便定位。
      </Typography.Paragraph>

      <Space size={4} wrap style={{ marginBottom: 12 }}>
        {CATEGORIES.map(c => (
          <Tag.CheckableTag key={c} checked={category === c} onChange={() => setCategory(c)}>
            {c}
          </Tag.CheckableTag>
        ))}
      </Space>

      <Form form={form} layout="vertical">
        <Form.Item
          name="content"
          rules={[
            { required: true, message: '写点内容吧' },
            { min: 2, message: '至少写两个字' },
          ]}
        >
          <Input.TextArea rows={5} maxLength={4000} showCount placeholder={PLACEHOLDER} />
        </Form.Item>
      </Form>
    </Modal>
  )
}
