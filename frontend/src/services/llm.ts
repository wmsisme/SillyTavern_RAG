/**
 * 大模型凭证（BYOK）在前端的存放处。
 *
 * 只存**这台浏览器**的 localStorage，请求时随 header 发给后端，后端用完即弃。
 * 不做任何"上传到服务器保存"的事 —— 产品定调是不给免费额度，
 * 那用户的 key 就没有理由离开他自己的机器。
 */
const STORAGE_KEY = 'strag_llm_settings'

export interface LLMSettings {
  provider: string
  apiKey: string
  /** 留空就用该平台的默认模型 */
  model?: string
  /** 留空就用内置地址；填了可接中转站 / 自建网关 */
  baseUrl?: string
}

export interface LLMProvider {
  id: string
  label: string
  protocol: string
  default_model: string
  models: string[]
  key_hint: string
  builtin_base_url: string
}

let cached: LLMSettings | null | undefined

export function getLLMSettings(): LLMSettings | null {
  if (cached !== undefined) return cached
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) {
      cached = null
    } else {
      const s = JSON.parse(raw)
      cached = s && s.provider && s.apiKey ? (s as LLMSettings) : null
    }
  } catch {
    cached = null
  }
  return cached
}

export function saveLLMSettings(s: LLMSettings) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(s))
  cached = s
  window.dispatchEvent(new Event('llm-settings-changed'))
}

export function clearLLMSettings() {
  localStorage.removeItem(STORAGE_KEY)
  cached = null
  window.dispatchEvent(new Event('llm-settings-changed'))
}

export function isLLMConfigured(): boolean {
  return getLLMSettings() !== null
}

/** 给请求加凭证头。没配置就返回空对象，让后端去回那句"请填 key"。 */
export function llmHeaders(): Record<string, string> {
  const s = getLLMSettings()
  if (!s) return {}
  const h: Record<string, string> = {
    'X-LLM-Provider': s.provider,
    'X-LLM-Key': s.apiKey,
  }
  if (s.model) h['X-LLM-Model'] = s.model
  if (s.baseUrl) h['X-LLM-Base-Url'] = s.baseUrl
  return h
}

/** 后端那句"要用你自己的 API Key"的识别嘴 */
export function looksLikeMissingKey(text: string): boolean {
  return !!text && (text.includes('API Key') || text.includes('api key'))
}

/**
 * 「没配 key」的统一出口。
 *
 * 以前各页面各写各的（首页甚至只显示 "HTTP 400"），用户根本不知道该干什么。
 * 现在由界面注册一次：任何地方撞到"没 key"，直接弹设置框。
 */
let missingKeyHandler: (() => void) | null = null

export function setMissingKeyHandler(fn: (() => void) | null) {
  missingKeyHandler = fn
}

export function notifyMissingKey() {
  missingKeyHandler?.()
}
