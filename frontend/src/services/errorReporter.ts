/**
 * 前端错误上报：把浏览器里的错误送回服务端 —— 「让线上不再瞎」的前端那一半。
 *
 * **只发技术信息**：错误消息、堆栈、当前页面路径、脚本 URL、行列号。
 * 不发用户输入、不发 localStorage、不发 cookie —— 服务端那边也**没有**接收这些的字段
 * （见 backend/api/errors.py 的 schema），两边都堵上。
 *
 * 这个文件本身跑在**崩溃路径**上，所以它自己有三条纪律：
 *   ① 上报失败一律吞掉，绝不抛错 —— 否则会触发新的 error 事件，变成自激循环
 *   ② 同一条错误（kind + message + page）只报一次
 *   ③ 每个页面会话最多报 MAX_PER_SESSION 条，防「某个组件在渲染里崩 → 无限重渲 → 刷爆库」
 *
 * 三条都需要：错误上报这东西一旦反过来放大问题，比不做还糟。
 */

const MAX_PER_SESSION = 20
const MESSAGE_MAX = 1000
const STACK_MAX = 4000

let sent = 0
const seen = new Set<string>()

interface ErrorPayload {
  kind: string
  message: string
  stack: string
  page: string
  source: string
  line: number
  col: number
}

function send(payload: ErrorPayload): void {
  try {
    if (sent >= MAX_PER_SESSION) return
    const key = `${payload.kind}|${payload.message}|${payload.page}`
    if (seen.has(key)) return
    seen.add(key)
    sent += 1

    // sendBeacon：页面正在崩 / 正在卸载时也发得出去，且不阻塞主线程。
    // 它接受 Blob，用 Blob 才能带上 application/json（否则会被当成 text/plain）。
    if (typeof navigator.sendBeacon === 'function') {
      const blob = new Blob([JSON.stringify(payload)], { type: 'application/json' })
      if (navigator.sendBeacon('/api/errors', blob)) return
    }
    // 退回 fetch：keepalive 让它在页面已经开始卸载时仍能完成
    void fetch('/api/errors', {
      method: 'POST',
      body: JSON.stringify(payload),
      headers: { 'Content-Type': 'application/json' },
      keepalive: true,
    }).catch(() => {
      /* 上报失败就算了 —— 这里绝不能抛，否则又是一次错误 */
    })
  } catch {
    /* 同上 */
  }
}

export function installErrorReporting(): void {
  window.addEventListener('error', (event) => {
    // 资源加载失败（img / script 404）也会冒到这个事件上：那时 error 为 null、filename 为空。
    // 那不是代码错误，混进来只会把真错误淹掉 —— 只收「脚本异常」这一类。
    if (!event.error && !event.filename) return
    const err = event.error as Error | undefined
    send({
      kind: 'error',
      message: (err?.message || event.message || 'unknown error').slice(0, MESSAGE_MAX),
      stack: (err?.stack || '').slice(0, STACK_MAX),
      page: location.pathname + location.hash,
      source: (event.filename || '').slice(0, 250),
      line: event.lineno || 0,
      col: event.colno || 0,
    })
  })

  window.addEventListener('unhandledrejection', (event) => {
    // reason 可能是 Error，也可能是任何被 reject 的值（字符串、对象、undefined）
    const reason = event.reason as unknown
    const err = reason instanceof Error ? reason : undefined
    send({
      kind: 'unhandledrejection',
      message: (err?.message || String(reason ?? 'unknown rejection')).slice(0, MESSAGE_MAX),
      stack: (err?.stack || '').slice(0, STACK_MAX),
      page: location.pathname + location.hash,
      source: '',
      line: 0,
      col: 0,
    })
  })
}
