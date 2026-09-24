import { useCallback, useEffect, useRef, useState } from 'react'
import { App, Badge, Button, List, Modal, Progress, Space, Tag, Typography } from 'antd'
import { CloudDownloadOutlined, SyncOutlined, ReloadOutlined } from '@ant-design/icons'
import { api } from '../services/api'

const { Text, Paragraph } = Typography

interface UpdateInfo {
  has_update: boolean
  changed_files: string[]
  current_commit: string
  upstream_commit: string
  message?: string
}

/**
 * 文档更新检测（需求 1）。
 * - 应用启动时自动检查一次（走后端 10 分钟缓存，不阻塞页面）
 * - 发现更新：弹窗让用户选择「立即更新」或「暂不更新」
 * - 更新中：轮询 /api/update/status 显示进度
 * - 更新后：后端已 reload_index()，提示用户刷新页面即可用新知识库
 */
export default function UpdateNotice() {
  const { message, modal } = App.useApp()
  const [checking, setChecking] = useState(false)
  const [updating, setUpdating] = useState(false)
  const [progress, setProgress] = useState('')
  const [info, setInfo] = useState<UpdateInfo | null>(null)
  const pollRef = useRef<number | null>(null)
  const notifiedRef = useRef(false)

  const stopPolling = useCallback(() => {
    if (pollRef.current !== null) {
      window.clearInterval(pollRef.current)
      pollRef.current = null
    }
  }, [])

  useEffect(() => stopPolling, [stopPolling])

  const check = useCallback(async (force: boolean) => {
    setChecking(true)
    try {
      const data: UpdateInfo = await api.get(`/update/check${force ? '?force=true' : ''}`)
      setInfo(data)
      return data
    } catch (e: any) {
      if (force) message.error('检查更新失败：' + (e?.message || '未知错误'))
      return null
    } finally {
      setChecking(false)
    }
  }, [message])

  const runUpdate = useCallback(async () => {
    setUpdating(true)
    setProgress('正在启动更新...')
    stopPolling()
    pollRef.current = window.setInterval(async () => {
      try {
        const st = await api.get('/update/status')
        if (st?.progress) setProgress(st.progress)
      } catch {
        /* 轮询失败不打断更新 */
      }
    }, 1000)

    try {
      const res = await api.post('/update/run')
      stopPolling()
      setUpdating(false)
      setProgress('')

      if (res.status === 'ok') {
        message.success(res.message || '更新完成')
        setInfo(prev => (prev ? { ...prev, has_update: false, changed_files: [] } : prev))
        modal.success({
          title: '文档更新完成',
          content: (
            <div>
              <Paragraph style={{ marginBottom: 8 }}>{res.message}</Paragraph>
              <Text type="secondary">知识库已重新加载，刷新页面即可使用最新内容。</Text>
            </div>
          ),
          okText: '刷新页面',
          onOk: () => window.location.reload(),
        })
      } else if (res.status === 'busy') {
        message.warning(res.message || '更新正在执行中')
      } else {
        modal.error({ title: '更新失败', content: res.message || '未知错误' })
      }
    } catch (e: any) {
      stopPolling()
      setUpdating(false)
      setProgress('')
      modal.error({ title: '更新失败', content: e?.message || '未知错误' })
    }
  }, [message, modal, stopPolling])

  const promptUpdate = useCallback((data: UpdateInfo) => {
    const files = data.changed_files || []
    modal.confirm({
      title: '检测到 SillyTavern 文档有更新',
      width: 560,
      icon: <CloudDownloadOutlined style={{ color: '#1677ff' }} />,
      content: (
        <div>
          <Paragraph style={{ marginBottom: 8 }}>
            {data.message || `发现 ${files.length} 个文件变更`}
          </Paragraph>
          <Space size="small" style={{ marginBottom: 12 }}>
            <Tag>当前 {data.current_commit || '未知'}</Tag>
            <Tag color="blue">上游 {data.upstream_commit || '未知'}</Tag>
          </Space>
          {files.length > 0 && (
            <List
              size="small"
              bordered
              style={{ maxHeight: 180, overflow: 'auto' }}
              dataSource={files.slice(0, 30)}
              renderItem={(f: string) => <List.Item>{f}</List.Item>}
            />
          )}
          {files.length > 30 && (
            <Text type="secondary">…另有 {files.length - 30} 个文件</Text>
          )}
          <Paragraph type="secondary" style={{ marginTop: 12, marginBottom: 0 }}>
            更新会拉取上游文档并重新翻译、向量化，可能耗时较久并消耗 DeepSeek 额度。
          </Paragraph>
        </div>
      ),
      okText: '立即更新',
      cancelText: '暂不更新',
      onOk: () => runUpdate(),
    })
  }, [modal, runUpdate])

  // 启动时自动检查一次（StrictMode 下 effect 会跑两次，用 ref 去重）
  useEffect(() => {
    if (notifiedRef.current) return
    notifiedRef.current = true
    check(false).then(data => {
      if (data?.has_update) promptUpdate(data)
    })
  }, [check, promptUpdate])

  const handleManualCheck = async () => {
    const data = await check(true)
    if (!data) return
    if (data.has_update) {
      promptUpdate(data)
    } else {
      message.success(data.message || '已是最新版本')
    }
  }

  return (
    <>
      <Badge dot={!!info?.has_update} offset={[-2, 2]}>
        <Button
          type="text"
          icon={checking ? <SyncOutlined spin /> : <ReloadOutlined />}
          onClick={handleManualCheck}
          disabled={updating}
          title="检查文档更新"
        >
          文档更新
        </Button>
      </Badge>

      <Modal
        open={updating}
        title="正在更新文档与索引"
        footer={null}
        closable={false}
        maskClosable={false}
      >
        <Progress percent={99} status="active" showInfo={false} />
        <Paragraph style={{ marginTop: 12, marginBottom: 0 }}>{progress || '处理中...'}</Paragraph>
        <Text type="secondary">请勿关闭页面或停止后端服务。</Text>
      </Modal>
    </>
  )
}
