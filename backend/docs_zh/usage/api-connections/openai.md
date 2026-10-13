
# Chat Completions

## 各来源的具体说明

> **⚠️ **重要！****
>
> 大多数 API 平台只允许你在创建 API 密钥时查看一次生成的密钥。如果你丢失了它，就需要生成一个新的密钥。请务必妥善保管！


### OpenAI

使用 OpenAI 的开发者平台访问各种 OpenAI 模型，包括 gpt-4o、gpt-4.1、o3 等。

**如何获取 API 密钥：**

1. 前往 [OpenAI](https://platform.openai.com/) 并登录。
2. 使用“[查看 API 密钥](https://platform.openai.com/account/api-keys)”选项创建一个新的 API 密钥。

### Claude

Claude 是由 Anthropic 开发的一系列 AI 模型。你可以通过 Anthropic 控制台访问 Claude 模型。

**如何获取 API 密钥：**

1. 前往 [Anthropic Console](https://console.anthropic.com/) 并登录。
2. 使用“[获取 API 密钥](https://console.anthropic.com/settings/keys)”部分创建一个新的 API 密钥。

### Mistral AI

Mistral AI 是一个同时开发开源和专有模型的团队，秉持高科学标准并注重开放性。你可以在本地运行他们的模型，或通过他们的 API 服务 La Plateforme 使用。

**如何获取 API 密钥：**

1. 第一步是在 [La Plateforme](https://console.mistral.ai/) 上创建一个账户。
2. 完成后，你可以选择[套餐](https://console.mistral.ai/billing/plans)并设置支付信息，或选择免费套餐。
3. 接下来，你可以创建你的 [API 密钥](https://console.mistral.ai/api-keys/)。你可能需要等待几分钟，密钥才会生效！

### DeepSeek

DeepSeek Platform 通过 API 提供对最新 DeepSeek 模型的访问。他们提供一系列模型，包括 DeepSeek V3 和 DeepSeek R1。

**如何获取 API 密钥：**

1. 在 [DeepSeek Platform](https://platform.deepseek.com/) 上注册。
2. 注册并充值账户后，你可以在“[API 密钥](https://platform.deepseek.com/api_keys)”部分创建一个 API 密钥。

### AI21

AI21 Labs 提供一系列 AI 模型，包括其旗舰 Jamba 系列。你可以通过 AI21 Studio API 访问他们的模型。

**如何获取 API 密钥：**

1. 前往 [AI21 Studio](https://studio.ai21.com/) 并登录。
2. 导航到“Settings => API Keys”部分创建一个新的 API 密钥。

### Cohere

Cohere 提供一套用于各种任务的 AI 模型，包括文本生成和嵌入。你可以通过 Cohere API 访问他们的模型。

**如何获取 API 密钥：**

1. 前往 [Cohere](https://cohere.com/) 并登录。
2. 在账户设置中导航到“[API 密钥](https://dashboard.cohere.com/api-keys)”部分创建一个新的 API 密钥。

### Perplexity

Perplexity AI 通过其 API 提供对支持联网的 Sonar 模型的访问，用于实时研究和信息检索。

官方入门指南：[Perplexity 快速开始](https://docs.perplexity.ai/getting-started/quickstart)

**如何获取 API 密钥：**

1. 前往 [Perplexity](https://perplexity.ai/) 并登录。
2. 前往“[API 计费](https://www.perplexity.ai/account/api/billing)”部分购买 API 使用额度。
3. 在设置中导航到“[API 密钥](https://www.perplexity.ai/account/api/keys)”部分创建一个新的 API 密钥。

### Fireworks AI

Fireworks AI 是一个高性能平台，提供快速、经济高效的方式来访问最先进的开源语言模型。该平台提供无服务器部署，兼容 OpenAI API，并支持高达 256,000 个 token 的上下文窗口。

**如何获取 API 密钥：**

1. 前往 [Fireworks AI](https://fireworks.ai/) 创建账户或登录。
2. 在账户设置中导航到 [API 密钥页面](https://app.fireworks.ai/settings/users/api-keys)。
3. 点击“Create API key”并提供一个描述性名称（例如“SillyTavern”）。

## Electron Hub

Electron Hub 是一个统一的 OpenAI 兼容平台，通过单个 API 密钥提供对多个供应商模型的访问。

**如何获取 API 密钥：**

1. 在 [Electron Hub](https://playground.electronhub.ai/console) 创建一个账户。
2. 从 **Console → API Keys** 页面生成一个 API 密钥。

## 自定义 OpenAI 兼容端点

> **⚠️ Warning**
>
> 需要注意的是，对于你可能遇到的任何问题，我们不提供支持！
> 我们不保证与所有可能的 API 端点兼容！


> **📝 提示**
如果你打算使用此功能来连接本地端点，例如 TabbyAPI、Oobabooga、Aphrodite 或类似的服务，你可能想查看[这些服务的内置兼容性](/usage/api-connections/)。自定义端点功能主要用于其他暴露 OpenAI 兼容 API Chat Completion 端点的服务和程序。

大多数 Text Completion API 支持比 OpenAI 标准允许的更多的自定义选项。这些更丰富的自定义选项，例如 Min-P 采样器，可能值得 SillyTavern 用户尝试，它可以大大提高生成质量。
> **📝 提示**

你可以为 Chat Completions 后端配置一个替代端点。这个自定义端点可以连接到任何支持通用 OpenAI API schema 的服务器。

兼容后端的示例包括：

* [LM Studio](https://lmstudio.ai/)
* [LiteLLM](https://www.litellm.ai/)
* [LocalAI](https://localai.io/)

### 连接

要访问此功能：

1. 切换到“Chat Completion”API 类型
2. 为“Chat Completion Source”选择“Custom (OpenAI-compatible)”

输入自定义端点 URL 和 API 密钥（如需要）。例如，TabbyAPI 需要 API 密钥进行身份验证。

> **💡 Tip**
>
> **提示：** 如果你遇到连接问题，请尝试在端点 URL 末尾添加 `/v1`。不要添加 `/chat/completions` 后缀。


### 选择模型

如果自定义 API 实现了 `/v1/models` 端点以提供可用模型列表，你可以从下拉列表中选择。否则，使用文本字段手动输入模型 ID。

勾选“Bypass API status check”以防止 SillyTavern 就 API 端点无法正常工作向你发出警告。如果你的 API 端点工作正常但 SillyTavern 持续显示警告，请启用此选项。

点击“Test Message”通过向模型发送一个简单提示来验证连接性。

> **ℹ️ 要记录外部供应商？**
>
> 供应商开发者应阅读[集成外部供应商](/for-contributors/provider-integrations/)，了解供应商自有的设置指南模板以及 UI 扩展、服务器插件和官方集成路线。


## 提示词后处理

> **⚠️ Warning**
>
> **注意：** 当使用带有“no tools”的后处理选项时，不支持工具调用！


某些端点可能对传入提示词的格式施加特定限制，例如仅要求一条系统消息或严格交替角色。

SillyTavern 提供内置的提示词转换器来帮助满足这些要求（从限制最少到最多）：

1. None - 除非 API 严格要求，否则不应用显式处理
2. Merge consecutive messages from the same role（合并来自同一角色的连续消息）
3. Semi-strict - 合并角色，仅允许一条可选的系统消息
4. Strict - 合并角色，仅允许一条可选的系统消息，并要求用户消息排在第一位
5. Single user message - 将所有角色的所有消息合并为一条用户消息

Merge、semi-strict 和 strict 还会从提示词中移除任何工具调用，除非选择了“with tools”变体。这对于不支持工具调用且你现有提示词包含工具调用的 API 很有用。

在 SillyTavern 中实现的限制较少的选项对限制较多的端点没有影响，除了“Custom OpenAI-compatible”；Custom 在请求无效时可能会报错。

在严格模式下，如果在第一条助手消息之前不存在用户消息，则会插入 `config.yaml` 中的 `promptPlaceholder`，默认值为“\[Start a new chat]”。