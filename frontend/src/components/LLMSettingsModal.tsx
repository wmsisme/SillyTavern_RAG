import { useEffect, useState } from 'react'
import {
  Modal, Form, Input, Select, Alert, Button, Space, App, Typography,
  AutoComplete, Divider, Radio, Tag,
} from 'antd'
import { api } from '../services/api'
import { useAuth } from '../services/auth'
import {
  clearLLMSettings, getLLMSettings, saveLLMSettings,
  type LLMProvider, type LLMSettings,
} from '../services/llm'

const { Text, Paragraph } = Typography

interface AccountSettings {
  configured: boolean
  provider: string
  model: string
  base_url: string
  masked_key: string
  decryptable: boolean
  updated_at?: string
}

/**
 * 「API 设置」：用户填自己的大模型 API Key。
 *
 * 两种存法**明确分开**（界面上要一眼看出区别）：
 *   · 存进我的账号 —— 换设备登录也能用；Key 加密存在服务器（服务器能解开才能替你调用）
 *   · 只存这台浏览器 —— 服务器从不经手你的 Key；换设备要重填
 * 两者互斥：选哪个就清掉另一个，不会出现"以为没存其实还在服务器上"。
 */
export default function LLMSettingsModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { message } = App.useApp()
  const { user } = useAuth()
  const [form] = Form.useForm()
  const [providers, setProviders] = useState<LLMProvider[]>([])
  const [testing, setTesting] = useState(false)
  const [saving, setSaving] = useState(false)
  const [advanced, setAdvanced] = useState(false)
  const [mode, setMode] = useState<'account' | 'local'>('local')
  const [account, setAccount] = useState<AccountSettings | null>(null)

  const providerId = Form.useWatch('provider', form)
  const meta = providers.find(p => p.id === providerId)
  const accountHasKey = !!account?.configured && account?.decryptable

  useEffect(() => {
    if (!open) return
    api.get('/llm/providers').then(d => setProviders(d.providers || []))
      .catch(() => message.error('拿不到平台清单，请检查后端是否在跑'))

    const local = getLLMSettings()
    setAdvanced(!!local?.baseUrl)

    if (user) {
      api.get('/llm/settings')
        .then((d: AccountSettings) => {
          setAccount(d)
          if (d?.configured && d.decryptable) {
            // 账号里已存 → 默认这种模式，且**不回填 Key**（前端根本拿不到原文）
            setMode('account')
            form.setFieldsValue({ provider: d.provider, model: d.model, baseUrl: d.base_url, apiKey: '' })
            setAdvanced(!!d.base_url)
            return
          }
          if (local) {
            setMode('local')
            form.setFieldsValue(local)
          } else {
            setMode('local')
            form.setFieldsValue({ provider: 'deepseek', apiKey: '', model: '', baseUrl: '' })
          }
        })
        .catch(() => setAccount(null))
    } else if (local) {
      setMode('local')
      form.setFieldsValue(local)
    } else {
      form.setFieldsValue({ provider: 'deepseek', apiKey: '', model: '', baseUrl: '' })
    }
  }, [open, form, message, user])

  const handleProviderChange = (pid: string) => {
    const p = providers.find(x => x.id === pid)
    form.setFieldsValue({ provider: pid, model: p?.default_model || '' })
  }

  const headersFromForm = (): Record<string, string> => {
    const v = form.getFieldsValue()
    const h: Record<string, string> = {}
    if (v.apiKey?.trim()) {
      h['X-LLM-Provider'] = v.provider
      h['X-LLM-Key'] = v.apiKey.trim()
      if (v.model?.trim()) h['X-LLM-Model'] = v.model.trim()
      if (v.baseUrl?.trim()) h['X-LLM-Base-Url'] = v.baseUrl.trim()
    }
    return h
  }

  const handleTest = async () => {
    const v = form.getFieldsValue()
    const h = headersFromForm()
    // 账号模式且输入框为空 → 后端会自动用账号里存的那把，这里不用带任何头
    if (!h['X-LLM-Key'] && !accountHasKey) { message.warning('先填 API Key'); return }
    setTesting(true)
    try {
      const r = await api.post('/llm/test', undefined, { headers: h, timeout: 60_000 })
      if (r?.ok) message.success(`连接成功（${r.provider} / ${r.model}）：${r.reply || 'OK'}`)
      else message.error(`连不上：${r?.error || '未知错误'}`)
    } catch (e: any) {
      message.error('测试失败：' + (e?.message || '未知错误'))
    } finally {
      setTesting(false)
    }
  }

  const handleSave = async () => {
    const v = await form.validateFields()
    setSaving(true)
    try {
      if (mode === 'account') {
        if (!user) { message.warning('请先登录，才能存到账号里'); return }
        const d: AccountSettings = await api.put('/llm/settings', {
          provider: v.provider,
          api_key: (v.apiKey || '').trim(),      // 空 = 保留原来那把
          model: (v.model || '').trim(),
          base_url: (v.baseUrl || '').trim(),
        })
        setAccount(d)
        clearLLMSettings()      // 两种存法互斥：存了账号就把本机那份清掉
        form.setFieldValue('apiKey', '')
        // 通知右上角的红点重新判断（账号存法不走 localStorage，所以得手动广播）
        window.dispatchEvent(new Event('llm-settings-changed'))
        message.success(`已存进你的账号（${d.masked_key}），换设备登录也能用`)
      } else {
        saveLLMSettings({
          provider: v.provider,
          apiKey: (v.apiKey || '').trim(),
          model: (v.model || '').trim(),
          baseUrl: (v.baseUrl || '').trim(),
        })
        // 互斥：既然选择只存本机，就把服务器上那份删掉，避免"以为没存其实还在服务器"
        if (user && accountHasKey) {
          await api.delete('/llm/settings').catch(() => {})
          setAccount(null)
        }
        message.success('已保存到这台浏览器（不会上传到服务器）')
      }
      onClose()
    } catch (e: any) {
      message.error(e?.message || '保存失败')
    } finally {
      setSaving(false)
    }
  }

  const handleClear = async () => {
    clearLLMSettings()
    if (user && accountHasKey) {
      try {
        await api.delete('/llm/settings')
        setAccount(null)
      } catch { /* 忽略：至少本机那份清掉了 */ }
    }
    window.dispatchEvent(new Event('llm-settings-changed'))
    form.setFieldsValue({ provider: 'deepseek', apiKey: '', model: '', baseUrl: '' })
    message.success('两处保存的 Key 都已清除')
  }

  return (
    <Modal
      title="API 设置（自带 Key）"
      open={open}
      onCancel={onClose}
      width={640}
      footer={[
        <Button key="clear" onClick={handleClear}>清除</Button>,
        <Button key="test" loading={testing} onClick={handleTest}>测试连接</Button>,
        <Button key="save" type="primary" loading={saving} onClick={handleSave}>保存</Button>,
      ]}
    >
      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        message="AI 功能用你自己的 API Key（本站不提供免费额度）"
        description="下面两种存法选一个："
      />

      <Radio.Group
        value={mode}
        onChange={e => setMode(e.target.value)}
        style={{ marginBottom: 8, width: '100%' }}
      >
        <Space direction="vertical" size={10} style={{ width: '100%' }}>
          <Radio value="account" disabled={!user}>
            <b>存进我的账号</b>
            <div>
              <Text type="secondary" style={{ fontSize: 12 }}>
                跟着账号走：换台设备登录也在（Key 加密保存）
              </Text>
            </div>
            {!user && <Text type="warning" style={{ fontSize: 12 }}>（要先登录）</Text>}
          </Radio>
          <Radio value="local">
            <b>只存这台浏览器</b>
            <div>
              <Text type="secondary" style={{ fontSize: 12 }}>
                跟着浏览器走：刷新过后仍然保存，换设备要重填
              </Text>
            </div>
          </Radio>
        </Space>
      </Radio.Group>
      <Paragraph type="secondary" style={{ fontSize: 12, marginBottom: 16 }}>
        两种只能选一个，换的时候会自动清掉另一种。
      </Paragraph>

      {accountHasKey && (
        <Alert
          type="success"
          showIcon
          style={{ marginBottom: 16 }}
          message={`账号里已存着：${account?.provider}${account?.model ? ' / ' + account.model : ''}（${account?.masked_key}）`}
          description={<Text type="secondary" style={{ fontSize: 12 }}>
            Key 输入框留空即可保留这一把（只改平台/模型时不用重填）。
          </Text>}
        />
      )}
      {account?.configured && account?.decryptable === false && (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
          message="账号里存的那把 Key 解不开了"
          description="多半是服务器的加密密钥换过。重新填一次就好。"
        />
      )}

      <Form form={form} layout="vertical">
        <Form.Item label="平台" name="provider" rules={[{ required: true }]}>
          <Select onChange={handleProviderChange}
                  options={providers.map(p => ({ label: p.label, value: p.id }))} />
        </Form.Item>

        {meta && (
          <Text type="secondary" style={{ display: 'block', marginTop: -12, marginBottom: 12, fontSize: 12 }}>
            {meta.key_hint}（内置地址：{meta.builtin_base_url}）
          </Text>
        )}

        <Form.Item
          label="API Key"
          name="apiKey"
          rules={mode === 'local' ? [{ required: true, message: '请填 API Key' }] : []}
        >
          <Input.Password
            placeholder={accountHasKey ? '留空 = 保留账号里已存的那把' : '粘贴你的 API Key'}
            autoComplete="off"
          />
        </Form.Item>

        <Form.Item label="模型" name="model" tooltip="留空则用该平台的默认模型">
          <AutoComplete options={(meta?.models || []).map(m => ({ value: m }))}
                        placeholder={meta?.default_model || '默认模型'} />
        </Form.Item>

        {!advanced && (
          <Button type="link" size="small" style={{ paddingLeft: 0 }} onClick={() => setAdvanced(true)}>
            接中转站 / 自建网关（自定义地址）
          </Button>
        )}
        {advanced && (
          <>
            <Divider style={{ margin: '8px 0 12px' }} />
            <Form.Item label="自定义接口地址（可选）" name="baseUrl"
                       tooltip="填了就覆盖内置地址；可用于中转站或自建网关">
              <Input placeholder="https://例如中转站地址/v1" allowClear />
            </Form.Item>
          </>
        )}
      </Form>

      <Paragraph type="secondary" style={{ fontSize: 12, marginBottom: 0 }}>
        国内服务器直连 OpenAI / Anthropic 通常不通 —— 那两家"能用但多半连不上"，不是这里填错了；
        用中转站时把地址填到上面的「自定义接口地址」即可。
      </Paragraph>
    </Modal>
  )
}
