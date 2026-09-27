const BASE_URL = '/api'

/** 默认请求超时：后端卡住时页面不应该无限转圈 */
const DEFAULT_TIMEOUT = 60_000
/** 慢接口（AI 生成、文档更新、问答）用的放宽值 */
export const LONG_TIMEOUT = 30 * 60_000

type Options = RequestInit & { timeout?: number }

/**
 * 从错误响应里取出可读信息。
 * 后端出错时返回的可能是 FastAPI 的 {detail}、我们自己的 {error}/{message}，
 * 也可能是代理层的 HTML —— 逐个尝试，取不到就退回纯文本片段。
 */
async function readErrorText(response: Response): Promise<string> {
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
    const response = await fetch(`${BASE_URL}${url}`, {
      ...rest,
      headers: { 'Content-Type': 'application/json', ...(rest.headers || {}) },
      signal: controller.signal,
    })

    if (!response.ok) {
      throw new Error(await readErrorText(response))
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
}
