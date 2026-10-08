import { llmHeaders, looksLikeMissingKey, notifyMissingKey } from './llm'

const BASE_URL = '/api'

/** 默认请求超时：后端卡住时页面不应该无限转圈 */
const DEFAULT_TIMEOUT = 60_000
/** 慢接口（AI 生成、文档更新、问答）用的放宽值 */
export const LONG_TIMEOUT = 30 * 60_000

type Options = RequestInit & { timeout?: number }

/**
 * 收到 401 时的回调。会话令牌存在 httponly Cookie 里，前端读不到、也无法预判过期，
 * 所以只能由接口回 401 来触发"回到未登录态"（由 AuthProvider 注册）。
 */
let unauthorizedHandler: (() => void) | null = null
export function setUnauthorizedHandler(fn: (() => void) | null) {
  unauthorizedHandler = fn
}

/**
 * 从错误响应里取出可读信息。
 * 后端出错时返回的可能是 FastAPI 的 {detail}、我们自己的 {error}/{message}，
 * 也可能是代理层的 HTML —— 逐个尝试，取不到就退回纯文本片段。
 */
export async function readErrorText(response: Response): Promise<string> {
  const text = await response.text().catch(() => '')
  try {
    const data = JSON.parse(text)
    const detail = data?.detail ?? data?.message ?? data?.error
    if (typeof detail === 'string') return detail
    if (detail) return JSON.stringify(detail)
  } catch {
    /* 不是 JSON，按纯文本处理 */
  }
  const trimmed = text.replace(/<[^>]+>/g, ' ').trim()
  return trimmed.slice(0, 300) || `HTTP ${response.status}`
}

async function request<T = any>(url: string, options?: Options): Promise<T> {
  const { timeout = DEFAULT_TIMEOUT, ...rest } = options || {}
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), timeout)

  try {
    // ⚠️ FormData 千万不能带 Content-Type：multipart 的 boundary 是浏览器自己拼进那个头的，
    //    手写 'application/json' 会让后端解析不出任何字段 —— 附件上传就死在这儿（2026-10-08）。
    const isForm = typeof FormData !== 'undefined' && rest.body instanceof FormData

    const response = await fetch(`${BASE_URL}${url}`, {
      ...rest,
      // 会话靠 Cookie：同源请求本来就会带上，显式写出来是为了别处改成本地存储时也稳
      credentials: 'include',
      // 用户自带的大模型凭证随每个请求走（localStorage → header），后端不留存
      headers: {
        ...(isForm ? {} : { 'Content-Type': 'application/json' }),
        ...llmHeaders(),
        ...(rest.headers || {}),
      },
      signal: controller.signal,
    })

    if (!response.ok) {
      const detail = await readErrorText(response)
      if (response.status === 401) unauthorizedHandler?.()
      // 「没填 API Key」是个可自救的状态，不该只丢一句报错：直接把设置框弹出来
      if (response.status === 400 && looksLikeMissingKey(detail)) notifyMissingKey()
      throw new Error(detail)
    }

    // 204 / 空响应体不该让 response.json() 抛 SyntaxError
    if (response.status === 204) return undefined as T
    const text = await response.text()
    return (text ? JSON.parse(text) : undefined) as T
  } catch (e: any) {
    if (e?.name === 'AbortError') {
      throw new Error(`请求超时（${Math.round(timeout / 1000)} 秒），后端可能仍在处理`)
    }
    throw e
  } finally {
    window.clearTimeout(timer)
  }
}

export const api = {
  get: <T = any>(url: string, options?: Options) => request<T>(url, options),
  post: <T = any>(url: string, data?: unknown, options?: Options) =>
    request<T>(url, { method: 'POST', body: data !== undefined ? JSON.stringify(data) : undefined, ...options }),
  put: <T = any>(url: string, data?: unknown, options?: Options) =>
    request<T>(url, { method: 'PUT', body: data !== undefined ? JSON.stringify(data) : undefined, ...options }),
  delete: <T = any>(url: string, options?: Options) => request<T>(url, { method: 'DELETE', ...options }),
  /**
   * 表单上传（附件用）。走和别的请求完全同一套超时 / 401 / 错误解析，
   * 唯一区别就是**不带 JSON 头**（见 request 里那段关于 boundary 的说明）。
   */
  upload: <T = any>(url: string, form: FormData, options?: Options) =>
    request<T>(url, { method: 'POST', body: form, ...options }),
}
