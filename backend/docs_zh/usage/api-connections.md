
# API 连接

SillyTavern 可以连接多种 LLM API。  
下面将描述它们各自的优势、劣势和使用场景。

## 通俗解释：聊天补全 vs 文本补全

当您首次进入 ST 的“API 连接”页面时，会看到一个下拉选项，用于选择“聊天补全”（Chat Completion）或“文本补全”（Text Completion）等术语。理解这些含义很有帮助。

**它不是什么：** 人们很容易把“文本补全”理解为本地模型，把“聊天补全”理解为云端 LLM，但实际上并非如此。例如，“NovelAI”或“Kobold”也并非完全独立的模型类型，尽管它们在 ST 的 API 下拉菜单中是单独的选项。您可以通过合适的后端将模型强制适配到不同的 API 结构，但这并非本节的重点。

当您使用 ST 发送消息时，您的聊天记录、角色描述以及诸如知识书或作者注释等其他提示会被构造成一个单独的“提示”（prompt）发送给模型。您所使用模型的 API“类型”决定了这个提示的具体构造方式（ST 会在后台自动处理这些——您可以打开 ST 终端，查看发送给 AI 的提示具体是什么样子）。

### 聊天补全

顾名思义，聊天补全模型会将您的提示结构化为用户（您）、助手（AI）或系统（中立）之间的一系列消息。经过聊天补全训练的模型有助于营造“聊天”的感觉，即 AI“回复”最后一条消息。当您使用 ChatGPT 网站时，后台处理的就是聊天补全 API。

### 文本补全（也称“补全”）

另一方面，文本补全（同样顾名思义）会将您的提示转换为一个长字符串，模型会简单地尝试继续这个字符串（想象一下，您所有的文本、数百条消息、所有格式、换行符等都被压缩成一个非常长的句子）。

如果 ST 中的消息恰好被格式化为 `您的角色名: ` 和 `角色名: ` 之间的一系列消息，那么文本补全模型会尝试延续这种模式，ST 会将其渲染为新的聊天消息，但实际上模型只是在尝试延续文本。如果您输入了“太阳从”，文本补全模型很可能会帮您补全为“东方升起”。

大多数文本补全模型都有一个推荐的“指令模板”（Instruct Template，通常在模型文档或下载页面中提到），该模板帮助它们像聊天补全模型一样“回复”消息和指令。ST 通常会在“高级格式化”页面中提供大多数（如果不是全部）指令模板供您选择。

## 本地 API

- 这些 LLM API 可以在您的 PC 上运行。
- 免费使用，没有内容过滤器。
- 安装过程可能较复杂（**SillyTavern 开发团队不为此提供支持**）。
- 需要从 [HuggingFace](https://huggingface.co/models?other=LLM) 单独下载 LLM 模型，每个模型 5-50GB。
- 大多数模型不如云端 LLM API 强大。

### KoboldCpp

- 易于使用的 API，支持 CPU 卸载（对低显存用户有帮助）和流式输出。
- 在 Windows、Mac 和 Linux 上由单个二进制文件运行。
- 支持 GGUF 模型。
- 比仅使用 GPU 的加载器（如 AutoGPTQ 和 Exllama/v2）慢。
- [GitHub](https://github.com/LostRuins/koboldcpp)，[安装说明](/usage/api-connections/koboldcpp/)

### llama.cpp

- KoboldCpp 和 Ollama 所派生的原始源代码。
- 提供预编译二进制文件，也可以选择从源代码编译。
- 支持 GGUF 模型。
- 轻量级 CLI 接口，用于 llama-server。
- [GitHub](https://github.com/ggml-org/llama.cpp)

### Ollama

- 在所有基于 llama.cpp 的 API 中，设置和使用最简单。
- 有一个便捷的 [模型目录](https://ollama.com/library)，支持一键下载。
- 支持包裹在 Ollama 自有格式中的 GGUF 模型。
- [GitHub](https://github.com/ollama/ollama)，[网站](https://ollama.com/)

### Oobabooga TextGeneration WebUI

- 一体化 Gradio 界面，支持流式输出。
- 对量化模型（AWQ、Exl2、GGML、GGUF、GPTQ）和 FP16 模型提供最广泛的支持。
- 提供一键安装程序。
- 定期更新，有时可能破坏与 SillyTavern 的兼容性。
- [GitHub](https://github.com/oobabooga/text-generation-webui#one-click-installers)

**将 SillyTavern 正确连接到 Ooba 的新 OpenAI API 的方法：**

1. 确保您已更新到 Oobabooga 的 TextGen 的最新版本（截至 2023 年 11 月 14 日）。
2. 编辑 CMD_FLAGS.txt 文件，在其中添加 `--api` 标志。然后重新启动 Ooba 服务器。
3. 将 ST 连接到 `http://localhost:5000/`（默认），不要勾选“Legacy API”复选框。您可以从 Ooba 控制台提供的 URL 中移除 `/v1` 后缀。

*您可以使用 `--api-port 5001` 标志更改 API 托管端口，其中 5001 是您的自定义端口。*

### TabbyAPI

- 基于 [Exllamav2](https://github.com/turboderp/exllamav2) 的轻量级 API，支持流式输出。
- 支持 Exl2、GPTQ 和 FP16 模型。
- [官方扩展](https://github.com/theroyallab/ST-tabbyAPI-loader)允许直接从 SillyTavern 加载/卸载模型。
- 不建议低显存用户使用（不支持 CPU 卸载）。
- [GitHub](https://github.com/theroyallab/tabbyAPI)，[安装说明](/usage/api-connections/tabbyapi/)

### KoboldAI Classic（已弃用，已停止维护）

- 在您的 PC 上运行，100% 私有，提供多种模型。
- 对 AI 生成设置提供最直接的控制。
- 需要 GPU 拥有大量显存（6-24GB，取决于 LLM 模型）。
- 模型仅限于 2k 上下文。
- 不支持流式输出。
- 流行的 KoboldAI 版本：
  - [Henky's United](https://github.com/henk717/KoboldAI)
  - [0cc4m 的 4-bit 支持版 United](https://github.com/0cc4m/KoboldAI)

## 云端 LLM API

- 这些 LLM API 作为云服务运行，不需要占用您的 PC 资源。
- 它们比大多数本地 LLM 更强大/更智能。
- 然而，它们都有不同程度的内容过滤，并且大多数需要付费。

### AI Horde

- SillyTavern 可以开箱即用地访问此 API，无需额外设置。
- 利用个别志愿者（Horde Workers）的 GPU 处理您聊天输入的生成立即响应。
- 生成等待时间、AI 设置和可用模型完全取决于 Workers 的情况。
- [网站](https://aihorde.net/)，[安装说明](/usage/api-connections/horde/)

### OpenAI（ChatGPT）

- 易于设置和获取 API 密钥。
- 需要预付积分，按提示计费。
- 非常符合逻辑。创意风格可能重复且可预测。
- 大多数新模型（gpt-4-turbo、gpt-4o）支持多模态。
- [网站](https://platform.openai.com/)，[安装说明](/usage/api-connections/openai/#openai)

### Claude（由 Anthropic 提供）

- 推荐给希望 AI 聊天具有创意且独特写作风格的用户。
- 需要预付积分，按提示计费。
- 最新模型（Claude 3）支持多模态。
- 需要特定的提示风格，并利用 [预填充](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/prefill-claudes-response) 来控制回复方向。
- [网站](https://console.anthropic.com/)，[安装说明](/usage/api-connections/openai/#claude)

### Google AI Studio 和 Vertex AI

- 有免费层，存在速率限制（Gemini Flash），可能需要提供账单信息。
- [AI Studio](https://aistudio.google.com/) 通常拥有最新的模型和功能。
- [Vertex AI](https://console.cloud.google.com/vertex-ai/studio) 设置更复杂，但更稳定。
- [安装说明](/usage/api-connections/google/)

### Mistral（由 Mistral AI 提供）

- 多种大小和用途的高效模型。您可以在 [他们的平台](https://console.mistral.ai/api-keys/) 上创建账户和 API 密钥。
- 通用用途的上下文大小从 32k 到 128k，编程用途的上下文大小从 32k 到 256k。
- 免费层，存在速率限制。
- 合理的审核，Mistral 的主要原则是中立和赋能用户，更多信息请查看 [这里](https://mistral.ai/terms/)。
- [网站](https://console.mistral.ai/)，[安装说明](/usage/api-connections/openai/#mistral-ai)

### OpenRouter

- 提供统一 API，可访问市场上所有主流 LLM。
- 按 token 付费的积分系统，以及每日请求量有限的免费模型。
- 除非 LLM 供应商要求，否则不强制执行审核。
- [网站](https://openrouter.ai)，[安装说明](/usage/api-connections/openrouter/)

### DeepSeek

- 提供对非常流行的 DeepSeek V3（`deepseek-chat`）和 DeepSeek R1（`deepseek-reasoner`）最新版本的访问。
- 需要付费购买积分（最低 $2），但相对于其质量而言，模型非常便宜。
- API 端没有审核，但模型可能拒绝某些提示。
- [网站](https://platform.deepseek.com/)，[安装说明](/usage/api-connections/openai/#deepseek)

### AI21

- 提供对 Jamba 系列开放模型的访问。
- 有免费试用（三个月 $10），之后按 token 每月付费。
- [网站](https://ai21.com/)，[安装说明](/usage/api-connections/openai/#ai21)

### Cohere

- 提供对 Cohere 最新模型的访问（command-r、command-a、c4ai-aya 等）。
- 有免费层（试用密钥），提供足够的速率限制供日常使用。
- [网站](https://cohere.com/)，[安装说明](/usage/api-connections/openai/#cohere)

### Perplexity

- 通过其 API 提供独特的 Perplexity Sonar 在线模型访问。
- 需要配置计费并购买积分。
- [网站](https://perplexity.ai/)，[安装说明](/usage/api-connections/openai/#perplexity)

### Mancer AI

- 托管多种系列无限制模型的服务。
- 使用“积分”支付各种模型的 token。
- 默认不记录提示，但您可以启用记录以获得 token 积分折扣。
- 使用类似于 `Oobabooga TextGeneration WebUI` 的 API，详情请参阅 [Mancer 文档](https://mancer.tech/docs/clients/#sampling-parameters)。
- [网站](https://mancer.tech/)，[安装说明](/usage/api-connections/mancer/)

### DreamGen

- 专为可操控创意写作调整的无审查模型。
- 每月免费积分，以及付费订阅。
- 模型范围从 7B 到 70B。
- [安装说明](/usage/api-connections/dreamgen/)

### Pollinations

- 无需设置，开箱即用。
- 免费提供多种模型。
- 输出内容有时可能包含指向第三方服务的广告链接。

### NovelAI

- 无内容过滤器，最新模型基于 Llama 3。
- 需要付费订阅，套餐级别决定最大上下文长度。
- [网站](https://novelai.net/)，[安装说明](/usage/api-connections/novelai/)

### Electron Hub

- 一个 API 密钥即可解锁来自多个供应商（OpenAI、Anthropic、DeepSeek 等）的模型，用于文本和图像生成。
- 每天 $0.25 免费积分，提供付费套餐。
- [网站](https://www.electronhub.ai/)，[安装说明](/usage/api-connections/openai/#electron-hub)

### AI/ML API

- 统一 API，支持 300 多个模型，包括 Claude、GPT-4o、Gemini、LLaMA 3、Mistral 等。
- 提供免费层（速率限制）、订阅套餐和按量付费选项。
- [网站](https://aimlapi.com)，[文档](https://docs.aimlapi.com)，[模型列表](https://aimlapi.com/models)