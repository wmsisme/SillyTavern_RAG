import { useCallback, useEffect, useRef, useState } from 'react'
import { App, Badge, Button, List, Modal, Progress, Space, Tag, Typography } from 'antd'
import { CloudDownloadOutlined, SyncOutlined, ReloadOutlined } from '@ant-design/icons'
import { api, LONG_TIMEOUT } from '../services/api'

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
  const [elapsed, setElapsed] = useState(0)
  const pollRef = useRef<number | null>(null)
  const tickRef = useRef<number | null>(null)
  /** 用户点了「不再等待」后置 true：请求还在跑，但不再弹窗打断他 */
  const detachedRef = useRef(false)
  const notifiedRef = useRef(false)

  const stopPolling = useCallback(() => {
    if (pollRef.current !== null) {
      window.clearInterval(pollRef.current)
      pollRef.current = null
    }
    if (tickRef.current !== null) {
      window.clearInterval(tickRef.current)
      tickRef.current = null
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
    setElapsed(0)
    detachedRef.current = false
    stopPolling()
    pollRef.current = window.setInterval(async () => {
      try {
        const st = await api.get('/update/status')
        if (st?.progress) setProgress(st.progress)
      } catch {
        /* 轮询失败不打断更新 */
      }
    }, 1000)
    tickRef.current = window.setInterval(() => setElapsed(s => s + 1), 1000)

    try {
      // 更新要拉文档 + 翻译 + 向量化，实测 80s 起步、文档多时更久，
      // 所以这里用放宽的超时（默认 60s 会被误判成失败）。
      const res = await api.post('/update/run', undefined, { timeout: LONG_TIMEOUT })
      stopPolling()
      setUpdating(false)
      setProgress('')
      setInfo(prev => (prev ? { ...prev, has_update: false, changed_files: [] } : prev))

      if (detachedRef.current) {
        // 用户已经「不再等待」，就别再弹框打断他
        message.success(res.message || '文档更新已完成')
        return
      }

      if (res.status === 'ok') {
        message.success(res.message || '更新完成')
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
      // 超时/断连不等于后端停了：先问一下状态，再决定怎么说
      let stillRunning = false
      try {
        const st = await api.get('/update/status')
        stillRunning = !!st?.running
      } catch { /* 问不到就按失败处理 */ }

      if (stillRunning) {
        modal.warning({
          title: '等待超时，但后端仍在继续更新',
          content: '更新还在后端执行，完成后刷新页面即可使用新知识库。',
        })
      } else if (!detachedRef.current) {
        modal.error({ title: '更新失败', content: e?.message || '未知错误' })
      }
    }
  }, [message, modal, stopPolling])

  /** 「不再等待」：只是停止等待与轮询，后端更新照常跑完 */
  const handleDetach = useCallback(() => {
    detachedRef.current = true
    stopPolling()
    setUpdating(false)
    setProgress('')
    message.info('已转为后台执行：更新会继续跑完，完成后刷新页面即可')
  }, [message, stopPolling])

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
        closable={false}
        maskClosable={false}
        footer={[
          <Button key="detach" onClick={handleDetach}>不再等待（后端继续执行）</Button>,
        ]}
      >
        <Progress percent={99} status="active" showInfo={false} />
        <Paragraph style={{ marginTop: 12, marginBottom: 4 }}>{progress || '处理中...'}</Paragraph>
        <Text type="secondary">已等待 {elapsed} 秒。请勿关闭后端服务（页面可以留着不管）。</Text>
      </Modal>
    </>
  )
}
