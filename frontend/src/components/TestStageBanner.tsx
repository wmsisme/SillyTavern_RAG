import { useState } from 'react'
import { Alert } from 'antd'
import { ExperimentOutlined } from '@ant-design/icons'

/**
 * 测试阶段提示条（2026-10-08 达铭要求）。
 *
 * **它解决的是什么问题**：用户一进来就会撞见各种限制 —— 注册要邀请码、
 * 附件最多 3 个 / 单个 20MB、同一个网络每天只能传 5 个、检索还有频率上限。
 * 不说理由的话，这些只会被读成「站长抠门」；先说清「这站跑在站长自己的电脑上、
 * 还在测试期」，它们才变成「能理解」。
 *
 * **文案守则**（达铭纠正过我一次：原文「你直接说：一个跟着账号走，一个跟着浏览器走，
 * 刷新过后仍然保存。你说的有点看不懂」）：讲**行为**，别讲**机制** ——
 * 说「哪些事现在有上限、什么时候会放开」，而不是「服务器磁盘配额与限流算法」。
 * 「跑在自己电脑上」这句要留着：它不是机制，是**用户能听懂也能共情的那一句**。
 *
 * 可关闭且**记住**（localStorage）：提示该给第一次来的人看到；
 * 已经看过、正在用的人不该每次都被它挡掉一行 —— 关了就长期不再出现。
 */
const DISMISS_KEY = 'strag-stage-banner-dismissed'

export default function TestStageBanner() {
  const [closed, setClosed] = useState(() => {
    try {
      return localStorage.getItem(DISMISS_KEY) === '1'
    } catch {
      return false                 // 隐私模式下读不了 localStorage，当没关过
    }
  })

  if (closed) return null

  return (
    <Alert
      banner
      type="info"
      showIcon
      icon={<ExperimentOutlined />}
      closable
      onClose={() => {
        try { localStorage.setItem(DISMISS_KEY, '1') } catch { /* 写不了就算了 */ }
        setClosed(true)
      }}
      message={
        <span style={{ fontSize: 13 }}>
          <strong>这个站点还在测试阶段</strong> —— 它跑在站长自己的电脑上（不是云服务器），
          所以注册要邀请码，上传文件和检索都有上限。
          <strong>测试通过后会换到正式服务器，这些限制都会放开。</strong>
          遇到问题、或者想要什么功能，点「反馈」告诉我 —— 现在提的每一条都会直接影响后面怎么做。
        </span>
      }
    />
  )
}
